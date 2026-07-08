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
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _base import write_points, read_points  # noqa: E402

# EBTL dry-Deccan analog belt — a sensible default AOI for pulling a species' points for transfer/colocation.
DEFAULT_BBOX = [76.0, 11.0, 79.5, 13.6]


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


def get(species, bbox=None, sources=("gbif", "inat", "paper"), limit=500, refresh=False):
    """Resolve a species to a cached, source-merged points CSV. Idempotent (cache hit unless refresh)."""
    bbox = [float(x) for x in (bbox or DEFAULT_BBOX)]
    path = _path(species, bbox)
    if os.path.exists(path) and not refresh:
        rows = read_points(path)
        return {"species": species, "path": path, "n": len(rows), "cached": True}
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
    return {"species": species, "bbox": bbox, "path": path, "n": len(uniq), "by_source": by, "cached": False}


def describe():
    return {
        "connector": "points",
        "purpose": "Resolve a species name to a cached, source-merged points CSV (GBIF + iNaturalist).",
        "produces": "a deterministic CSV path other tools consume (geo.cooccur, predict, invasive).",
        "functions": ["get(species, bbox=[w,s,e,n], sources=('gbif','inat'), limit=500, refresh=False) -> {path,n,by_source}"],
        "use": "Call this FIRST when a tool needs a species' points — then pass the returned `path` to the "
               "tool. Never invent a points filename; use the path `points.get` returns. Adding a new points "
               "source = edit ONLY this file, not every skill.",
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
    args = ap.parse_args(argv)
    if args.describe or not args.cmd:
        print(json.dumps(describe(), indent=2)); return
    print(json.dumps(get(args.species, args.bbox.split(",") if args.bbox else None,
                         limit=args.limit, refresh=args.refresh), indent=2))


if __name__ == "__main__":
    _main()
