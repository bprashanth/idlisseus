"""points — the ONE resolver that turns a species name into a cached points file.

Why this exists: tools that consume points (geo.cooccur, predict, invasive…) should NOT each know where
points come from — otherwise adding a source (iNaturalist, camera traps, a paper) means editing every tool.
`points` is the single place that knows the sources: it MERGES GBIF (`occurrence`) + iNaturalist, dedupes,
and caches to a DETERMINISTIC path. Tools just say "give me points for species X" and get a file path back.
This also stops the agent hallucinating temp filenames — the path is returned, never invented.

  get(species, bbox) -> {"path": ".../points/<slug>__<hash>.csv", "n":..., "by_source":{...}}
  CLI: python points.py get --species "Tectona grandis" --bbox 77.8,12.37,78.55,13.1
Cache dir: $POINTS_CACHE or /opt/data/work/points (container) or ../runs/points (host).
"""
import argparse
import hashlib
import json
import re
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _base import write_points, read_points  # noqa: E402

# EBTL dry-Deccan analog belt — a sensible default AOI for pulling a species' points for transfer/colocation.
DEFAULT_BBOX = [76.0, 11.0, 79.5, 13.6]


# ─────────────────────────────── name resolution (L1) ───────────────────────────────
# A species QUESTION arrives as a name the *user* speaks — often a COMMON name ("green cat snake").
# GBIF/iNat/paper all key on the SCIENTIFIC name, and a common name can map to the WRONG species
# (real failure: "green cat snake" = Boiga cyanea, but the agent used Boiga flaviviridis = Wall's cat
# snake). So resolve FIRST: iNaturalist for vernacular→taxon (best common-name coverage), GBIF for the
# scientific backbone + fuzzy/typo matches. Cache to a JSON dict for O(1) reuse. If we can't resolve
# confidently, SAY so (ambiguous/unmatched) rather than guess — that honesty is the whole point.

def _http_json(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "idlisseus-points/0.2"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def _resolve_cache_path():
    return os.path.join(_cache_dir(), "taxonomy_resolve.json")


def _load_resolve_cache():
    try:
        return json.load(open(_resolve_cache_path()))
    except Exception:
        return {}


def _gbif_match(name):
    """GBIF species/match — authoritative for SCIENTIFIC names (+ fuzzy typos). NONE for pure common names."""
    try:
        u = "https://api.gbif.org/v1/species/match?strict=false&name=" + urllib.parse.quote(name)
        d = _http_json(u)
        if d.get("matchType") in (None, "NONE"):
            return None
        return {"scientific": d.get("canonicalName") or d.get("scientificName"),
                "rank": (d.get("rank") or "").upper(), "match": d.get("matchType"),
                "confidence": d.get("confidence")}
    except Exception:
        return None


def _inat_taxa(name, per=6):
    """iNaturalist taxa search — best VERNACULAR (common-name) coverage. Returns candidates, ranked by use."""
    try:
        u = ("https://api.inaturalist.org/v1/taxa?per_page=%d&q=" % per) + urllib.parse.quote(name)
        d = _http_json(u)
        out = []
        for t in d.get("results", []):
            out.append({"scientific": t.get("name"),
                        "common": t.get("preferred_common_name"),
                        "rank": (t.get("rank") or "").upper(),
                        "obs": t.get("observations_count") or 0,
                        "matched": (t.get("matched_term") or "")})
        return out
    except Exception:
        return []


def resolve(name, refresh=False):
    """Resolve a spoken name (common OR scientific) → the accepted scientific name + accepted common name.
    Returns {input, scientific, common, rank, source, match, ambiguous, candidates, note}. On failure,
    scientific=None and note explains — callers should treat the name as UNVERIFIED, not guess."""
    key = name.strip().lower()
    cache = _load_resolve_cache()
    if key in cache and not refresh:
        return cache[key]
    out = {"input": name, "scientific": None, "common": None, "rank": None,
           "source": None, "match": None, "ambiguous": False, "candidates": [], "note": ""}
    looks_sci = len(name.split()) == 2 and name[:1].isupper() and name.split()[1].islower()
    gb = _gbif_match(name)
    inat = _inat_taxa(name)
    # exact-common-name hits in iNat (the vernacular the user likely spoke)
    cn = [t for t in inat if t.get("common") and t["common"].strip().lower() == key]
    if gb and (gb["match"] == "EXACT" or looks_sci) and gb["rank"] in ("SPECIES", "SUBSPECIES", "GENUS"):
        out.update(scientific=gb["scientific"], rank=gb["rank"], match=gb["match"], source="gbif")
        # borrow an accepted common name from iNat if the scientific matches
        for t in inat:
            if t["scientific"] and t["scientific"].lower() == gb["scientific"].lower():
                out["common"] = t.get("common"); break
    elif cn:
        best = max(cn, key=lambda t: (t["rank"] == "SPECIES", t["obs"]))
        out.update(scientific=best["scientific"], common=best["common"], rank=best["rank"], source="inat",
                   match="common-name")
        others = {t["scientific"] for t in cn if t["scientific"] != best["scientific"]}
        if others:
            out["ambiguous"] = True
            out["candidates"] = [{"scientific": t["scientific"], "common": t["common"], "obs": t["obs"]} for t in cn[:4]]
            out["note"] = ("common name '%s' maps to multiple taxa — picked the most-observed (%s); verify."
                           % (name, best["scientific"]))
    elif inat:
        # L1 relevance guard: a bare common word makes iNat autocomplete return typo-fuzzy GARBAGE from the
        # WRONG kingdom (gaur->fireweed, sambar->a dragonfly), and picking the most-observed hit asserts it
        # confidently. Only trust a fuzzy hit that RELATES to the query — its common/scientific shares a word
        # with what the user said. Otherwise resolve to NOTHING: an honest "unverified, ask" beats a
        # confident wrong-species (the #1 correctness failure, LIMITATIONS L1).
        toks = {w for w in key.replace("'", " ").replace("-", " ").split() if len(w) > 2}
        def _rel(t):   # WHOLE-WORD overlap (not substring — else 'gaur' matches the plant 'Gaura')
            words = set(re.findall(r"[a-z]+", ((t.get("common") or "") + " " + (t.get("scientific") or "")).lower()))
            return bool(toks & words)
        rel = [t for t in inat if _rel(t)]
        if rel:
            best = max(rel, key=lambda t: (t["rank"] == "SPECIES", t["obs"]))
            out.update(scientific=best["scientific"], common=best.get("common"), rank=best["rank"],
                       source="inat", match="fuzzy")
            out["note"] = "no exact name match; best RELATED iNaturalist guess '%s' — VERIFY before asserting." % best["scientific"]
            out["candidates"] = [{"scientific": t["scientific"], "common": t.get("common"), "obs": t["obs"]} for t in rel[:4]]
        else:
            out["note"] = ("'%s' matched no taxon by name (iNaturalist returned only unrelated species) — "
                           "UNVERIFIED; say you could not resolve it and ask which species is meant." % name)
            out["candidates"] = [{"scientific": t["scientific"], "common": t.get("common"), "obs": t["obs"]} for t in inat[:3]]
    elif gb:
        out.update(scientific=gb["scientific"], rank=gb["rank"], match=gb["match"], source="gbif")
        out["note"] = "GBIF %s match only — verify." % gb["match"]
    else:
        out["note"] = "could not resolve '%s' to a known taxon — treat as UNVERIFIED (say so; ask the user)." % name
    # cross-source disagreement flag (both resolved, different species)
    if gb and out["source"] == "inat" and out["scientific"] and gb["scientific"] \
            and out["scientific"].split()[0].lower() != gb["scientific"].split()[0].lower():
        out["ambiguous"] = True
        out["note"] = (out["note"] + " (iNat and GBIF disagree: iNat=%s vs GBIF=%s)"
                       % (out["scientific"], gb["scientific"])).strip()
    try:
        cache[key] = out
        json.dump(cache, open(_resolve_cache_path(), "w"))
    except Exception:
        pass
    return out


def _cache_dir():
    for d in (os.environ.get("POINTS_CACHE"), "/opt/data/work/points",
              os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "runs", "points"))):
        if not d:
            continue
        try:
            os.makedirs(d, exist_ok=True)
            if os.access(d, os.W_OK):
                return d
        except Exception:
            continue
    return os.getcwd()


def _path(species, bbox):
    slug = species.lower().replace(" ", "_").replace("/", "_")
    h = hashlib.sha1(",".join(f"{x:.3f}" for x in bbox).encode()).hexdigest()[:6]
    return os.path.join(_cache_dir(), f"{slug}__{h}.csv")


def get(species, bbox=None, sources=("gbif", "inat", "paper"), limit=500, refresh=False, resolve_name=True):
    """Resolve a species to a cached, source-merged points CSV. Idempotent (cache hit unless refresh).
    First normalises the NAME (common→scientific via `resolve`); the merged sources are pulled on the
    resolved scientific name, and the resolution (incl. any ambiguity) is returned so /why can show it."""
    res = resolve(species) if resolve_name else None
    query = (res or {}).get("scientific") or species          # pull on the accepted scientific name
    bbox = [float(x) for x in (bbox or DEFAULT_BBOX)]
    path = _path(query, bbox)
    if os.path.exists(path) and not refresh:
        rows = read_points(path)
        return {"species": species, "resolved": res, "path": path, "n": len(rows), "cached": True}
    species = query
    rows, by = [], {}
    if "gbif" in sources:
        try:
            import occurrence
            g = occurrence.search(species, bbox=bbox, limit=limit)
            rows += g; by["gbif"] = len(g)
        except Exception as e:
            by["gbif"] = f"err:{str(e)[:40]}"
    if "inat" in sources:
        try:
            import inaturalist
            i = inaturalist.search(species, bbox, limit=limit)
            rows += i; by["inat"] = len(i)
        except Exception as e:
            by["inat"] = f"err:{str(e)[:40]}"
    if "paper" in sources:                             # published-paper datasets = high-grade origin source
        try:
            import paper_data
            p = paper_data.search(species, bbox)
            if isinstance(p, dict):
                p = p.get("points") or p.get("results") or []
            good = [r for r in (p or []) if isinstance(r, dict) and r.get("lat") and r.get("lon")]
            for r in good:
                r.setdefault("dataset", r.get("paper") or r.get("source") or "paper_data")
            rows += good; by["paper"] = len(good)
        except Exception as e:
            by["paper"] = f"err:{str(e)[:40]}"
    # dedupe on rounded coords
    seen, uniq = set(), []
    for r in rows:
        if not (r.get("lat") and r.get("lon")):
            continue
        k = (round(float(r["lat"]), 5), round(float(r["lon"]), 5))
        if k not in seen:
            seen.add(k); uniq.append(r)
    write_points(uniq, path)
    return {"species": species, "resolved": res, "bbox": bbox, "path": path, "n": len(uniq),
            "by_source": by, "cached": False}


def describe():
    return {
        "connector": "points",
        "purpose": "Resolve a species name to a cached, source-merged points CSV (GBIF + iNaturalist).",
        "produces": "a deterministic CSV path other tools consume (geo.cooccur, predict, invasive).",
        "functions": ["get(species, bbox=[w,s,e,n], sources=('gbif','inat','paper'), ...) -> {path,n,by_source,resolved}",
                      "resolve(name) -> {scientific, common, ambiguous, candidates, note} — common↔scientific"],
        "use": "Call this FIRST when a tool needs a species' points — then pass the returned `path` to the "
               "tool. `get` auto-RESOLVES the name (common→scientific) and returns `resolved`; if the user "
               "gave a common name, check `resolved.ambiguous`/`resolved.note` and state the species you used. "
               "Use `resolve` alone to just verify a name. Never invent a points filename; use the returned path.",
        "gotcha": "Caches by species+bbox hash under /opt/data/work/points. Default bbox = the dry-Deccan "
                  "analog belt; pass --bbox for a specific AOI. `--refresh` to re-pull.",
        "example": "python /opt/data/connectors/points.py get --species \"Tectona grandis\" --bbox 77.8,12.37,78.55,13.1",
    }


def _main(argv=None):
    ap = argparse.ArgumentParser(prog="points")
    ap.add_argument("--describe", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    g = sub.add_parser("get"); g.add_argument("--species", required=True); g.add_argument("--bbox")
    g.add_argument("--limit", type=int, default=500); g.add_argument("--refresh", action="store_true")
    r = sub.add_parser("resolve"); r.add_argument("--species", required=True); r.add_argument("--refresh", action="store_true")
    args = ap.parse_args(argv)
    if args.describe or not args.cmd:
        print(json.dumps(describe(), indent=2)); return
    if args.cmd == "resolve":
        print(json.dumps(resolve(args.species, refresh=args.refresh), indent=2)); return
    print(json.dumps(get(args.species, args.bbox.split(",") if args.bbox else None,
                         limit=args.limit, refresh=args.refresh), indent=2))


if __name__ == "__main__":
    _main()
