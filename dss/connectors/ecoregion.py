"""ecoregion connector — RESOLVE Ecoregions 2017 via Earth Engine.

Two jobs: (1) AOI onboarding — name the ecoregion/biome an AOI sits in; (2) the
"analog transfer" harder mode — sample points in the SAME ecoregion OUTSIDE the
AOI, so an out-of-AOI correlation can be called out honestly (NOTES.md Add 3).

POINT ANNOTATOR: at(points) adds `ecoregion`, `biome`.
Also covering(bbox) and analog_points(eco_name, exclude_bbox, n).

CLI:
  python -m connectors.ecoregion --describe
  python -m connectors.ecoregion at --points sites.csv
  python -m connectors.ecoregion covering --bbox 77.95,12.30,78.45,12.80
  python -m connectors.ecoregion analog_points --eco "South Deccan Plateau dry deciduous forests" \
      --exclude-bbox 77.95,12.30,78.45,12.80 --n 20
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _base import init_ee, read_points, write_points

DATASET = "RESOLVE/ECOREGIONS/2017"
NAME_FIELD = "ECO_NAME"
BIOME_FIELD = "BIOME_NAME"


def at(points, project="plantwars"):
    """Annotate points with their ecoregion + biome (one spatial join, one getInfo)."""
    ee = init_ee(project)
    eco = ee.FeatureCollection(DATASET)
    pts = ee.FeatureCollection(
        [ee.Feature(ee.Geometry.Point([p["lon"], p["lat"]]), {"_i": i})
         for i, p in enumerate(points)])
    joined = ee.Join.saveFirst("eco").apply(
        pts, eco, ee.Filter.intersects(leftField=".geo", rightField=".geo"))
    by_i = {}
    for f in joined.getInfo()["features"]:
        e = f["properties"].get("eco", {}).get("properties", {})
        by_i[int(f["properties"]["_i"])] = (e.get(NAME_FIELD), e.get(BIOME_FIELD))
    out = []
    for i, p in enumerate(points):
        name, biome = by_i.get(i, (None, None))
        out.append({**p, "ecoregion": name, "biome": biome})
    return out


def covering(bbox, project="plantwars"):
    """Ecoregion names (+biome) whose polygons intersect bbox=[w,s,e,n]."""
    ee = init_ee(project)
    geom = ee.Geometry.Rectangle(list(bbox))
    fc = ee.FeatureCollection(DATASET).filterBounds(geom)
    props = fc.reduceColumns(ee.Reducer.toList().repeat(2),
                             [NAME_FIELD, BIOME_FIELD]).getInfo()["list"]
    names, biomes = (props + [[], []])[:2]
    seen, out = set(), []
    for n, b in zip(names, biomes):
        if n not in seen:
            seen.add(n); out.append({"ecoregion": n, "biome": b})
    return out


def analog_points(eco_name, exclude_bbox=None, n=20, project="plantwars"):
    """Random points inside ecoregion `eco_name`, optionally outside exclude_bbox.
    The out-of-AOI 'analog' sampler for the Controller's harder mode."""
    ee = init_ee(project)
    fc = ee.FeatureCollection(DATASET).filter(ee.Filter.eq(NAME_FIELD, eco_name))
    geom = fc.geometry()
    if exclude_bbox:
        geom = geom.difference(ee.Geometry.Rectangle(list(exclude_bbox)), maxError=1000)
    rp = ee.FeatureCollection.randomPoints(region=geom, points=n, seed=42)
    out = []
    for f in rp.getInfo()["features"]:
        lon, lat = f["geometry"]["coordinates"]
        out.append({"id": f"analog_{len(out)}", "lat": round(lat, 5), "lon": round(lon, 5),
                    "ecoregion": eco_name, "aoi_status": "analog_ecoregion"})
    return out


def describe():
    return {
        "connector": "ecoregion",
        "purpose": "RESOLVE Ecoregions 2017 — name the ecoregion/biome, and sample analog "
                   "points in the same ecoregion elsewhere (out-of-AOI transfer).",
        "dataset": DATASET, "fields": [NAME_FIELD, BIOME_FIELD],
        "produces": "POINT annotator: adds ecoregion, biome. Also covering(bbox), analog_points(...).",
        "functions": [
            "at(points) -> + ecoregion, biome",
            "covering(bbox=[w,s,e,n]) -> [{ecoregion, biome}]",
            "analog_points(eco_name, exclude_bbox, n) -> points in same ecoregion outside the AOI",
        ],
        "use": "AOI onboarding (which ecoregion is this?) and the analog harder mode: a "
               "correlation from the SAME ecoregion outside the AOI, reported as aoi_status="
               "analog_ecoregion, not as an in-AOI result.",
        "example": "python /opt/data/connectors/ecoregion.py covering --bbox 77.95,12.30,78.45,12.80",
    }


def _main(argv=None):
    ap = argparse.ArgumentParser(prog="ecoregion")
    ap.add_argument("--describe", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    a = sub.add_parser("at"); a.add_argument("--points", required=True); a.add_argument("--out")
    c = sub.add_parser("covering"); c.add_argument("--bbox", required=True)
    p = sub.add_parser("analog_points"); p.add_argument("--eco", required=True)
    p.add_argument("--exclude-bbox", default=None); p.add_argument("--n", type=int, default=20)
    p.add_argument("--out")
    args = ap.parse_args(argv)
    if args.describe or not args.cmd:
        print(json.dumps(describe(), indent=2)); return
    if args.cmd == "at":
        write_points(at(read_points(args.points)), args.out)
    elif args.cmd == "covering":
        print(json.dumps(covering([float(x) for x in args.bbox.split(",")]), indent=2))
    elif args.cmd == "analog_points":
        ex = [float(x) for x in args.exclude_bbox.split(",")] if args.exclude_bbox else None
        write_points(analog_points(args.eco, ex, args.n), args.out)


if __name__ == "__main__":
    _main()
