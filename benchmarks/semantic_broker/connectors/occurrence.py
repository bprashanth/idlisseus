"""occurrence connector — GBIF species occurrence (public REST API, no key).

POINT PRODUCER: search(species, bbox) -> [{id,lat,lon,species,year,dataset}].
Also species(bbox) -> which species are recorded there. Uses urllib (system CA)
per the Hermes SSL note. No Earth Engine.

CLI:
  python -m connectors.occurrence --describe
  python -m connectors.occurrence search --species "Lantana camara" --bbox 76.3,10.2,77.2,11.6
  python -m connectors.occurrence species --bbox 76.3,10.2,77.2,11.6
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _base import write_points

API = "https://api.gbif.org/v1/occurrence/search"


def _get(params):
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "idlisseus-connector"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def search(species, bbox, limit=300, years=None):
    """bbox=[w,s,e,n]. Returns occurrence points with coordinates."""
    w, s, e, n = bbox
    base = {"hasCoordinate": "true", "hasGeospatialIssue": "false",
            "decimalLatitude": f"{s},{n}", "decimalLongitude": f"{w},{e}"}
    if species:
        base["scientificName"] = species
    if years:
        a, _, b = str(years).partition("-")
        base["year"] = f"{a.strip()},{(b or a).strip()}"
    out, offset = [], 0
    while len(out) < limit:
        d = _get({**base, "limit": min(300, limit - len(out)), "offset": offset})
        for r in d.get("results", []):
            if r.get("decimalLatitude") is None:
                continue
            out.append({"id": r.get("key"), "lat": r["decimalLatitude"],
                        "lon": r["decimalLongitude"],
                        "species": r.get("species") or r.get("scientificName"),
                        "year": r.get("year"), "dataset": (r.get("datasetName") or "")[:40]})
        offset += 300
        if d.get("endOfRecords") or not d.get("results"):
            break
    return out


def species(bbox, limit=30):
    """Which species are recorded in bbox — via GBIF facet."""
    w, s, e, n = bbox
    d = _get({"hasCoordinate": "true", "decimalLatitude": f"{s},{n}",
              "decimalLongitude": f"{w},{e}", "limit": 0,
              "facet": "speciesKey", "facetLimit": limit})
    return d.get("count"), [f for f in d.get("facets", [])]


def describe():
    return {
        "connector": "occurrence",
        "purpose": "GBIF species occurrence records (public, no key).",
        "produces": "POINT producer: search() returns occurrence points.",
        "functions": [
            "search(species, bbox=[w,s,e,n], limit=300, years=None) -> [{id,lat,lon,species,year,dataset}]",
            "species(bbox) -> (total_count, facets)",
        ],
        "gotcha": "Occurrence density reflects sampling effort, not just true "
                  "abundance — many points near roads/reserves. Good for presence/"
                  "where-recorded, weak for absolute density.",
        "example": 'python /opt/data/connectors/occurrence.py search --species "Lantana camara" --bbox 76.3,10.2,77.2,11.6',
    }


def _main(argv=None):
    ap = argparse.ArgumentParser(prog="occurrence")
    ap.add_argument("--describe", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    se = sub.add_parser("search"); se.add_argument("--species", default=""); se.add_argument("--bbox", required=True)
    se.add_argument("--limit", type=int, default=300); se.add_argument("--years"); se.add_argument("--out")
    sp = sub.add_parser("species"); sp.add_argument("--bbox", required=True)
    args = ap.parse_args(argv)
    if args.describe or not args.cmd:
        print(json.dumps(describe(), indent=2)); return
    bbox = [float(x) for x in args.bbox.split(",")]
    if args.cmd == "search":
        write_points(search(args.species, bbox, args.limit, args.years), args.out)
    elif args.cmd == "species":
        total, facets = species(bbox)
        print(json.dumps({"total": total, "facets": facets[:30]}, indent=2))


if __name__ == "__main__":
    _main()
