"""inaturalist connector — species occurrence points from iNaturalist (open API, no key).

Complements `occurrence` (GBIF, research-grade only). iNaturalist direct returns far more for well-visited
sites — the EBTL bbox has 218 obs (97 plants) where GBIF research-grade had ~0 for Lantana. A POINT
PRODUCER with the same schema as occurrence: search(species, bbox) -> [{id,lat,lon,species,year,dataset}].

Prefer calling `points.py` (the resolver) which MERGES this with GBIF and caches — but this works standalone.

  python inaturalist.py search --species "Lantana camara" --bbox 78.170,12.721,78.197,12.747 --out out.csv
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _base import write_points  # noqa: E402

API = "https://api.inaturalist.org/v1/observations"
_UA = "idlisseus-dss/1.0 (conservation research)"


def search(species, bbox, limit=500, quality=None):
    """iNaturalist observations for a species in a bbox [w,s,e,n]. quality='research' to restrict."""
    w, s, e, n = [float(x) for x in bbox]
    out, page, per = [], 1, 200
    while len(out) < limit and page <= 10:
        q = {"taxon_name": species, "swlng": w, "swlat": s, "nelng": e, "nelat": n,
             "geo": "true", "per_page": per, "page": page, "order_by": "observed_on"}
        if quality:
            q["quality_grade"] = quality
        req = urllib.request.Request(API + "?" + urllib.parse.urlencode(q), headers={"User-Agent": _UA})
        try:
            d = json.loads(urllib.request.urlopen(req, timeout=40).read())
        except Exception as e:
            if not out:
                raise SystemExit(f"iNaturalist error: {e}")
            break
        res = d.get("results", [])
        if not res:
            break
        for r in res:
            g = (r.get("geojson") or {}).get("coordinates")   # [lon, lat]
            if not g:
                loc = (r.get("location") or "").split(",")     # "lat,lon" fallback
                if len(loc) == 2:
                    g = [float(loc[1]), float(loc[0])]
            if not g:
                continue
            od = r.get("observed_on") or ""
            out.append({"id": r.get("id"), "lat": g[1], "lon": g[0],
                        "species": ((r.get("taxon") or {}).get("name")) or species,
                        "year": int(od[:4]) if od[:4].isdigit() else None,
                        "dataset": "iNaturalist" + ("/research" if r.get("quality_grade") == "research" else "")})
        if len(res) < per:
            break
        page += 1
    return out[:limit]


def describe():
    return {
        "connector": "inaturalist",
        "purpose": "Species occurrence points from iNaturalist (open, no key) — richer locally than GBIF.",
        "produces": "POINT producer: search(species, bbox) -> [{id,lat,lon,species,year,dataset}].",
        "functions": ["search(species, bbox=[w,s,e,n], limit=500, quality=None|'research')"],
        "use": "For local points where GBIF research-grade is sparse. Prefer `points.py` (merges GBIF+iNat, "
               "caches). Standalone for iNat-only pulls.",
        "gotcha": "No key. Casual-grade included by default (set quality='research' to restrict). "
                  "Paginates to ~2000 max; wide bboxes may truncate.",
        "example": "python /opt/data/connectors/inaturalist.py search --species \"Lantana camara\" "
                   "--bbox 78.170,12.721,78.197,12.747",
    }


def _main(argv=None):
    ap = argparse.ArgumentParser(prog="inaturalist")
    ap.add_argument("--describe", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    sp = sub.add_parser("search"); sp.add_argument("--species", required=True); sp.add_argument("--bbox", required=True)
    sp.add_argument("--limit", type=int, default=500); sp.add_argument("--quality"); sp.add_argument("--out")
    args = ap.parse_args(argv)
    if args.describe or not args.cmd:
        print(json.dumps(describe(), indent=2)); return
    rows = search(args.species, args.bbox.split(","), args.limit, args.quality)
    if args.out:
        write_points(rows, args.out); print(f"wrote {len(rows)} -> {args.out}")
    else:
        print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    _main()
