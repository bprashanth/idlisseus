"""paper_crawl.py — AOI x author x subject crawl of ecological paper datasets.

Seeds with NCF's Zenodo community, ingests every dataset (via paper_data), harvests
the authors, then follows the authorship graph: for each author, pull their other
Zenodo datasets (which surfaces co-authors via shared datasets), ingest those too.
Everything lands in an index (points + value + provenance + which AOI it falls in),
so it becomes a queryable, GBIF-like store sourced from papers.

Bounded so it terminates: caps datasets, per-author fan-out, and file size.

  python3 research/paper_crawl.py --max-datasets 40 --max-authors 20
"""
import argparse
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "semantic_broker", "connectors"))
import paper_data as pdm  # noqa: E402

INDEX = os.path.join(HERE, "paper_data_index.jsonl")
CATALOG = os.path.join(HERE, "paper_catalog.jsonl")  # every inspected dataset -> card material
ZENODO = "https://zenodo.org/api/records"
# AOIs to tag points against (name -> bbox w,s,e,n)
AOIS = {"anamalai": [76.3, 10.2, 77.2, 11.7], "ebtl_corridor": [77.4, 11.9, 78.5, 12.9]}
# Free-text themes for Zenodo (hop 2) + Dryad (hop 3), RETARGETED to EBTL's ecoregion:
# South Deccan Plateau DRY-DECIDUOUS / thorn (Krishnagiri, TN), NOT the wet Western Ghats.
# The NCF wet-forest core still enters via hops 0-1 (community + author graph); these
# themes chase the six EBTL buckets: dry-deciduous analog places, invasives-in-dry,
# elephant/HEC/corridor, diet/forage, agroforestry/land-use. See MASTER_PLAN + the
# ecoregion audit. Bandipur/BRT/Mudumalai/Cauvery are the same dry ecoregion family as EBTL.
THEME_QUERIES = [
    # dry-deciduous ecoregion & analog places
    "dry deciduous forest India", "tropical dry forest India", "Eastern Ghats vegetation",
    "Deccan plateau forest", "Bandipur", "Biligiri Rangaswamy BRT", "Mudumalai forest",
    "Sathyamangalam", "Cauvery wildlife India", "Bannerghatta", "Nagarahole Kabini",
    # invasives in dry systems
    "Prosopis juliflora India", "Lantana camara dry forest India",
    "Senna spectabilis invasion", "invasive plant grassland India",
    # elephant / human-elephant conflict / corridor
    "Asian elephant corridor India", "human elephant conflict crop", "elephant movement India",
    # diet / forage / herbivore (to demonstrate shifts)
    "elephant diet foraging India", "ungulate diet dry forest India", "dhole diet India",
    "large herbivore browsing India",
    # agroforestry / land-use in the dry belt
    "agroforestry India biodiversity", "farmland biodiversity India", "silvopasture grazing India",
]


CACHE = os.path.join(HERE, "paper_cache")
_TAB = (".csv", ".tsv", ".txt", ".xlsx", ".xls")


import hashlib


def _dl(url):
    """Fetch bytes with an on-disk cache + polite backoff on 429 (Dryad rate-limits).
    Attaches the Dryad bearer token for datadryad.org byte downloads."""
    os.makedirs(CACHE, exist_ok=True)
    cp = os.path.join(CACHE, "dl_" + hashlib.md5(url.encode()).hexdigest())
    if os.path.exists(cp):
        return open(cp, "rb").read()
    headers = {"User-Agent": "idlisseus-crawl/0.1 (research)"}
    if "datadryad.org" in url:
        tok = pdm._dryad_token()
        if tok:
            headers["Authorization"] = f"Bearer {tok}"
    req = urllib.request.Request(url, headers=headers)
    for attempt in range(5):
        try:
            # pdm._OPENER strips our bearer on the 302 to Dryad's presigned S3 url
            raw = pdm._OPENER.open(req, timeout=90).read()
            open(cp, "wb").write(raw)
            time.sleep(0.4)  # be polite between hits
            return raw
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 4:
                time.sleep(2 ** attempt * 2)  # 2,4,8,16s
                continue
            raise


def _cache_path(name):
    return os.path.join(CACHE, re.sub(r"[^A-Za-z0-9._-]", "_", name)[-120:])


def _expand_files(files):
    """Normalize a file list to LOCAL ingestable tabular files: unzip any .zip, and
    prefetch remote csv/tsv/txt/xlsx through the cached+backoff _dl. Ingest then reads
    locally — no rate-limit hits mid-ingest, and everything is cached across runs."""
    os.makedirs(CACHE, exist_ok=True)
    out = []
    for f in files:
        nm = str(f.get("name", "")).lower()
        if nm.endswith(".zip"):
            try:
                z = zipfile.ZipFile(io.BytesIO(_dl(f["url"])))
            except Exception:
                continue
            for inner in z.namelist():
                if inner.lower().endswith(_TAB) and "__MACOSX" not in inner:
                    p = _cache_path(inner)
                    try:
                        open(p, "wb").write(z.read(inner))
                        out.append({"name": os.path.basename(inner), "url": p})
                    except Exception:
                        continue
        elif nm.endswith(_TAB):
            url = f["url"]
            if url.startswith("http"):
                p = _cache_path(f.get("name", url))
                try:
                    open(p, "wb").write(_dl(url))
                    out.append({"name": f.get("name"), "url": p})
                except Exception:
                    continue
            else:
                out.append(f)
    return out


def _records(params):
    url = f"{ZENODO}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "idlisseus-crawl/0.1"})
    d = json.loads(urllib.request.urlopen(req, timeout=45).read())
    out = []
    for h in d.get("hits", {}).get("hits", []):
        files = [{"name": f.get("key"), "size_mb": round(f.get("size", 0) / 1e6, 3),
                  "url": f.get("links", {}).get("self")}
                 for f in h.get("files", [])
                 if str(f.get("key", "")).lower().endswith(_TAB + (".zip",))
                 and f.get("size", 0) < 60e6]
        if files:
            out.append({"doi": h.get("doi"), "title": h.get("metadata", {}).get("title"),
                        "authors": [c.get("name") for c in h.get("metadata", {}).get("creators", [])],
                        "files": files})
    return out


def _tag_aoi(lat, lon):
    for name, (w, s, e, n) in AOIS.items():
        if w <= lon <= e and s <= lat <= n:
            return name
    return "elsewhere"


def crawl(max_datasets, max_authors, per_author, theme_per_query=15):
    seen, authors_seen = set(), set()
    idx = open(INDEX, "w")
    cat = open(CATALOG, "w")
    n_ds = n_pts = n_cat = 0
    by_type, by_aoi = {}, {}

    def ingest_rec(rec, hop):
        nonlocal n_ds, n_pts, n_cat
        if not rec.get("doi") or rec["doi"] in seen:
            return
        seen.add(rec["doi"])
        rec = dict(rec, files=_expand_files(rec.get("files", [])))
        if not rec["files"]:
            return
        # card material: columns per tabular file + any codebook/README text (files are
        # local/cached now, so this is cheap). This is what step (b) builds cards from —
        # captured for EVERY inspected dataset, even ones the point-extractor can't georef.
        cols, codebook = {}, ""
        for f in rec["files"]:
            nm = f.get("name", "").lower()
            if any(k in nm for k in ("readme", "codebook", "metadata")) or nm.endswith(".txt"):
                try:
                    raw = _dl(f["url"]) if f["url"].startswith("http") else open(f["url"], "rb").read()
                    codebook += f"\n[{f['name']}]\n" + raw.decode("utf-8", "ignore")[:3000]
                except Exception:
                    pass
                continue
            try:
                r0 = pdm._read_table(f["url"], max_rows=1)
                if r0:
                    cols[f["name"]] = list(r0[0].keys())
            except Exception:
                pass
        try:
            ing = pdm.ingest_dataset(rec, limit=20000)
        except Exception as ex:
            print(f"    ! ingest failed: {str(ex)[:60]}"); ing = {"strategy": "error", "points": []}
        pts = ing.get("points", [])
        vt = ing.get("value_type") or ing.get("detected", {}).get("value_type") or "unknown"
        n_cat += 1
        cat.write(json.dumps({"doi": rec["doi"], "title": rec["title"], "hop": hop,
                              "authors": rec.get("authors", []), "columns": cols,
                              "codebook": codebook[:6000], "n_points": len(pts),
                              "value_type": vt if pts else None,
                              "strategy": ing.get("strategy")}) + "\n")
        for a in rec.get("authors", []):
            authors_seen.add(a)
        if not pts:
            return
        n_ds += 1
        for p in pts:
            aoi = _tag_aoi(p["lat"], p["lon"])
            idx.write(json.dumps({"lat": p["lat"], "lon": p["lon"], "value": p.get("value"),
                                  "value_type": vt, "doi": rec["doi"], "dataset": rec["title"],
                                  "authors": rec.get("authors", []), "aoi": aoi, "hop": hop}) + "\n")
            by_type[vt] = by_type.get(vt, 0) + 1
            by_aoi[aoi] = by_aoi.get(aoi, 0) + 1
        n_pts += len(pts)
        print(f"  [hop{hop}] +{len(pts)} pts ({vt}) <- {rec['title'][:52]}")

    # hop 0: NCF community
    print("== hop 0: NCF Zenodo community ==")
    for rec in _records({"communities": pdm.COMMUNITIES["ncf"], "type": "dataset", "size": 25}):
        if n_ds >= max_datasets:
            break
        ingest_rec(rec, 0)

    # hop 1: authors of those datasets -> their other datasets (co-authors surface here)
    print("== hop 1: author graph (their other datasets) ==")
    for a in list(authors_seen)[:max_authors]:
        if n_ds >= max_datasets:
            break
        try:
            recs = _records({"q": f'creators.name:"{a}"', "type": "dataset", "size": per_author})
        except Exception:
            continue
        for rec in recs:
            if n_ds >= max_datasets:
                break
            ingest_rec(rec, 1)
        time.sleep(0.5)

    # hop 2: broad Zenodo keyword search across ALL of Zenodo (not just NCF community)
    print("== hop 2: Zenodo theme search (Western Ghats / dry-deciduous / restoration) ==")
    for q in THEME_QUERIES:
        if n_ds >= max_datasets:
            break
        try:
            recs = _records({"q": q, "type": "dataset", "size": theme_per_query})
        except Exception as ex:
            print(f"  ! theme query failed ({q}): {str(ex)[:50]}"); continue
        print(f"  query {q!r}: {len(recs)} datasets w/ tabular/zip files")
        for rec in recs:
            if n_ds >= max_datasets:
                break
            ingest_rec(rec, 2)
        time.sleep(0.5)

    # hop 3: Dryad (authenticated) — only if creds configured (~/.hermes/secrets/dryad.json)
    if pdm.dryad_configured():
        print("== hop 3: Dryad (authenticated download) ==")
        for q in THEME_QUERIES:
            if n_ds >= max_datasets:
                break
            try:
                recs = pdm.dryad_find(q, size=theme_per_query)
            except Exception as ex:
                print(f"  ! dryad query failed ({q}): {str(ex)[:50]}"); continue
            print(f"  query {q!r}: {len(recs)} Dryad datasets w/ tabular files")
            for rec in recs:
                if n_ds >= max_datasets:
                    break
                ingest_rec(rec, 3)
            time.sleep(0.5)
    else:
        print("== hop 3: Dryad SKIPPED (no creds — see research/DRYAD_SETUP.md) ==")

    idx.close(); cat.close()
    print(f"\n=== crawl done: {n_cat} datasets inspected (card corpus), "
          f"{n_ds} georeferenced, {n_pts} points, {len(authors_seen)} authors seen ===")
    print("by value_type:", by_type)
    print("by AOI:", by_aoi)
    print("index ->", INDEX)
    print("catalog ->", CATALOG)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-datasets", type=int, default=40)
    ap.add_argument("--max-authors", type=int, default=20)
    ap.add_argument("--per-author", type=int, default=4)
    ap.add_argument("--theme-per-query", type=int, default=15)
    a = ap.parse_args()
    crawl(a.max_datasets, a.max_authors, a.per_author, a.theme_per_query)
