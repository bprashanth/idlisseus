"""landcover connector — ESA WorldCover v200 (10 m) via Earth Engine.

POINT ANNOTATOR: classify(points) adds `landcover` (class NAME) + `landcover_code`.
Also area_by_class(bbox). The legend is OWNED here and discoverable via describe()
— the agent must never guess a class code (v-1 Q5 called class 50 "Shrubland";
it is Built-up).

CLI:
  python -m connectors.landcover --describe
  python -m connectors.landcover classify --points sites.csv
  python -m connectors.landcover area_by_class --bbox 76.3,10.2,77.2,11.6
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _base import init_ee, read_points, write_points

DATASET = "ESA/WorldCover/v200"
BAND = "Map"
# ESA WorldCover v200 legend — verified. NOTE: there is NO plantation/tea/coffee
# class; plantations show up as "Tree cover" or "Cropland".
LEGEND = {
    10: "Tree cover", 20: "Shrubland", 30: "Grassland", 40: "Cropland",
    50: "Built-up", 60: "Bare / sparse vegetation", 70: "Snow and ice",
    80: "Permanent water bodies", 90: "Herbaceous wetland",
    95: "Mangroves", 100: "Moss and lichen",
}


def _img(ee):
    return ee.ImageCollection(DATASET).first().select(BAND)


def classify(points, project="plantwars"):
    """Annotate points with land-cover class name. points: [{'id','lat','lon'}]."""
    ee = init_ee(project)
    feats = [ee.Feature(ee.Geometry.Point([p["lon"], p["lat"]]), {"_i": i})
             for i, p in enumerate(points)]
    sampled = _img(ee).sampleRegions(
        collection=ee.FeatureCollection(feats), scale=10, geometries=False)
    code_by_i = {int(f["properties"]["_i"]): f["properties"].get(BAND)
                 for f in sampled.getInfo()["features"]}
    out = []
    for i, p in enumerate(points):
        code = code_by_i.get(i)
        out.append({**p, "landcover_code": code,
                    "landcover": LEGEND.get(code, "unknown") if code is not None else None})
    return out


def area_by_class(bbox, project="plantwars", scale=100):
    """Return {class_name: area_km2} over bbox=[w,s,e,n]. scale in metres."""
    ee = init_ee(project)
    geom = ee.Geometry.Rectangle(list(bbox))
    hist = _img(ee).reduceRegion(
        reducer=ee.Reducer.frequencyHistogram(), geometry=geom,
        scale=scale, maxPixels=1e10).getInfo().get(BAND, {})
    px_km2 = (scale * scale) / 1e6
    return {LEGEND.get(int(c), f"code_{c}"): round(n * px_km2, 2)
            for c, n in sorted(hist.items(), key=lambda kv: -kv[1])}


def describe():
    return {
        "connector": "landcover",
        "purpose": "ESA WorldCover v200 (10 m) land cover.",
        "dataset": DATASET, "band": BAND,
        "produces": "POINT annotator: adds `landcover` (name) + `landcover_code`.",
        "functions": [
            "classify(points) -> points + landcover, landcover_code",
            "area_by_class(bbox=[w,s,e,n]) -> {class_name: km2}",
        ],
        "legend": LEGEND,
        "gotcha": "No plantation/tea/coffee class — plantations appear as "
                  "'Tree cover' or 'Cropland'. For plantations use the land-use assets.",
        "example": "python -m connectors.landcover classify --points sites.csv",
    }


def _main(argv=None):
    ap = argparse.ArgumentParser(prog="landcover")
    ap.add_argument("--describe", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    c = sub.add_parser("classify"); c.add_argument("--points", required=True); c.add_argument("--out")
    a = sub.add_parser("area_by_class"); a.add_argument("--bbox", required=True); a.add_argument("--scale", type=int, default=100)
    args = ap.parse_args(argv)
    if args.describe or not args.cmd:
        print(json.dumps(describe(), indent=2)); return
    if args.cmd == "classify":
        write_points(classify(read_points(args.points)), args.out)
    elif args.cmd == "area_by_class":
        bbox = [float(x) for x in args.bbox.split(",")]
        print(json.dumps(area_by_class(bbox, scale=args.scale), indent=2))


if __name__ == "__main__":
    _main()
