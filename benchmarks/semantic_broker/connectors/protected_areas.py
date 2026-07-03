"""protected_areas connector — WDPA (WCMC) via Earth Engine.

POINT ANNOTATOR: contains(points) adds in_pa (bool) + pa_name. Also names(bbox).
Reached through Earth Engine (WCMC/WDPA/current/polygons) — no Protected Planet
token needed.

CLI:
  python -m connectors.protected_areas --describe
  python -m connectors.protected_areas contains --points occ.csv
  python -m connectors.protected_areas names --bbox 76.3,10.2,77.2,11.6
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _base import init_ee, read_points, write_points

DATASET = "WCMC/WDPA/current/polygons"
NAME_FIELD = "NAME"


def contains(points, project="plantwars"):
    """Add in_pa (bool) + pa_name for each point (one server round-trip)."""
    ee = init_ee(project)
    pa = ee.FeatureCollection(DATASET)

    def tag(i, p):
        pt = ee.Geometry.Point([p["lon"], p["lat"]])
        hit = pa.filterBounds(pt).first()
        name = ee.Algorithms.If(hit, hit.get(NAME_FIELD), None)
        return ee.Feature(None, {"_i": i, "pa_name": name})

    fc = ee.FeatureCollection([tag(i, p) for i, p in enumerate(points)])
    by_i = {int(f["properties"]["_i"]): f["properties"].get("pa_name")
            for f in fc.getInfo()["features"]}
    return [{**p, "in_pa": bool(by_i.get(i)), "pa_name": by_i.get(i)}
            for i, p in enumerate(points)]


def names(bbox, project="plantwars", limit=50):
    """Protected-area names intersecting bbox=[w,s,e,n]."""
    ee = init_ee(project)
    geom = ee.Geometry.Rectangle(list(bbox))
    pa = ee.FeatureCollection(DATASET).filterBounds(geom)
    return sorted(set(pa.limit(limit).aggregate_array(NAME_FIELD).getInfo()))


def describe():
    return {
        "connector": "protected_areas",
        "purpose": "WDPA protected-area boundaries (via Earth Engine, no token).",
        "dataset": DATASET, "name_field": NAME_FIELD,
        "produces": "POINT annotator: adds in_pa (bool) + pa_name.",
        "functions": [
            "contains(points) -> + in_pa, pa_name",
            "names(bbox=[w,s,e,n]) -> [protected-area names]",
        ],
        "coverage_warning": "WDPA polygon coverage in India is PARTIAL. In the "
                  "Western Ghats AOI the only boundary present is the fragmented "
                  "'Ghâts occidentaux' World Heritage site — major reserves "
                  "(Mudumalai TR, Anamalai TR) have NO boundary in WDPA. So "
                  "in_pa=False means 'no WDPA boundary here', NOT necessarily "
                  "'outside all protected areas'. For reliable inside/outside-PA "
                  "analysis, supply reserve boundaries as an asset (GeoJSON) and "
                  "use the geo.within connector instead.",
        "gotcha": "The one present polygon is a serial WH site, so in_pa can be "
                  "true over scattered components; always check pa_name.",
        "example": "python /opt/data/connectors/protected_areas.py contains --points occ.csv",
    }


def _main(argv=None):
    ap = argparse.ArgumentParser(prog="protected_areas")
    ap.add_argument("--describe", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    c = sub.add_parser("contains"); c.add_argument("--points", required=True); c.add_argument("--out")
    n = sub.add_parser("names"); n.add_argument("--bbox", required=True)
    args = ap.parse_args(argv)
    if args.describe or not args.cmd:
        print(json.dumps(describe(), indent=2)); return
    if args.cmd == "contains":
        write_points(contains(read_points(args.points)), args.out)
    elif args.cmd == "names":
        bbox = [float(x) for x in args.bbox.split(",")]
        print(json.dumps(names(bbox), indent=2))


if __name__ == "__main__":
    _main()
