"""terrain connector — SRTM elevation / slope / aspect via Earth Engine.

POINT ANNOTATOR: at(points) adds elevation (m), slope (deg), aspect (deg).
Fire and invasion both track terrain, so this is a common covariate.

CLI:
  python -m connectors.terrain --describe
  python -m connectors.terrain at --points sites.csv
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _base import init_ee, read_points, write_points

DATASET = "USGS/SRTMGL1_003"


def at(points, project="plantwars"):
    ee = init_ee(project)
    dem = ee.Image(DATASET)
    img = dem.rename("elevation").addBands(ee.Terrain.slope(dem)).addBands(ee.Terrain.aspect(dem))
    feats = [ee.Feature(ee.Geometry.Point([p["lon"], p["lat"]]), {"_i": i})
             for i, p in enumerate(points)]
    got = img.sampleRegions(collection=ee.FeatureCollection(feats), scale=30,
                            geometries=False).getInfo()["features"]
    by_i = {int(f["properties"]["_i"]): f["properties"] for f in got}
    out = []
    for i, p in enumerate(points):
        pr = by_i.get(i, {})
        out.append({**p, "elevation": pr.get("elevation"),
                    "slope": round(pr["slope"], 1) if pr.get("slope") is not None else None,
                    "aspect": round(pr["aspect"], 0) if pr.get("aspect") is not None else None})
    return out


def describe():
    return {
        "connector": "terrain",
        "purpose": "SRTM 30 m elevation, slope, aspect.",
        "dataset": DATASET,
        "produces": "POINT annotator: adds elevation (m), slope (deg), aspect (deg).",
        "functions": ["at(points) -> + elevation, slope, aspect"],
        "example": "python /opt/data/connectors/terrain.py at --points sites.csv",
    }


def _main(argv=None):
    ap = argparse.ArgumentParser(prog="terrain")
    ap.add_argument("--describe", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    a = sub.add_parser("at"); a.add_argument("--points", required=True); a.add_argument("--out")
    args = ap.parse_args(argv)
    if args.describe or not args.cmd:
        print(json.dumps(describe(), indent=2)); return
    if args.cmd == "at":
        write_points(at(read_points(args.points)), args.out)


if __name__ == "__main__":
    _main()
