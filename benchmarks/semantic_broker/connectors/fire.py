"""fire connector — MODIS MOD14A1 thermal anomalies via Earth Engine.

POINT ANNOTATOR: exposure(points, radius_km, years) adds `fire_count` (total
pixel-fire-days in a buffer over the period) + `fire_density` (per km2). Also
points(aoi, years) -> fire locations. Owns the FireMask legend and the buffer
reduction the agent must not hand-write (v-1 Q1 failed exactly here).

CLI:
  python -m connectors.fire --describe
  python -m connectors.fire exposure --points sites.csv --radius-km 5 --years 2020-2025
  python -m connectors.fire points --bbox 76.3,10.2,77.2,11.6 --years 2020-2025
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _base import init_ee, read_points, write_points

DATASET = "MODIS/061/MOD14A1"
BAND = "FireMask"
# MOD14A1 FireMask legend. Fire = value >= 7 (7 low / 8 nominal / 9 high conf).
LEGEND = {3: "water", 4: "cloud", 5: "non-fire land", 6: "unknown",
          7: "fire (low conf)", 8: "fire (nominal)", 9: "fire (high conf)"}
FIRE_THRESHOLD = 7
SCALE = 1000  # MOD14A1 native ~1 km


def _dates(years):
    """'2020-2025' -> ('2020-01-01','2026-01-01'). Single '2023' also ok."""
    a, _, b = years.partition("-")
    a = a.strip(); b = (b or a).strip()
    return f"{a}-01-01", f"{int(b) + 1}-01-01"


def _fire_frequency(ee, years):
    """Per-pixel count of fire-days over the period (an ee.Image)."""
    start, end = _dates(years)
    coll = ee.ImageCollection(DATASET).filterDate(start, end).select(BAND)
    return coll.map(lambda img: img.gte(FIRE_THRESHOLD)).sum().rename("fire_days")


def exposure(points, radius_km=5, years="2020-2025", project="plantwars"):
    """Annotate points with fire_count (pixel-fire-days in the buffer) + fire_density."""
    ee = init_ee(project)
    freq = _fire_frequency(ee, years)
    feats = [ee.Feature(ee.Geometry.Point([p["lon"], p["lat"]]).buffer(radius_km * 1000),
                        {"_i": i}) for i, p in enumerate(points)]
    stats = freq.reduceRegions(collection=ee.FeatureCollection(feats),
                               reducer=ee.Reducer.sum(), scale=SCALE).getInfo()
    count_by_i = {int(f["properties"]["_i"]): (f["properties"].get("sum") or 0)
                  for f in stats["features"]}
    area = 3.14159 * radius_km * radius_km
    out = []
    for i, p in enumerate(points):
        c = count_by_i.get(i, 0)
        out.append({**p, "fire_count": round(c, 1),
                    "fire_density": round(c / area, 3), "radius_km": radius_km})
    return out


def points(bbox, years="2020-2025", project="plantwars", max_points=500):
    """Return fire locations in bbox=[w,s,e,n] as [{lat,lon,fire_days}]."""
    ee = init_ee(project)
    geom = ee.Geometry.Rectangle(list(bbox))
    freq = _fire_frequency(ee, years).selfMask()
    samp = freq.sample(region=geom, scale=SCALE, numPixels=max_points,
                       geometries=True).getInfo()["features"]
    out = []
    for f in samp:
        lon, lat = f["geometry"]["coordinates"]
        out.append({"lat": round(lat, 5), "lon": round(lon, 5),
                    "fire_days": f["properties"].get("fire_days")})
    return out


def describe():
    return {
        "connector": "fire",
        "purpose": "MODIS MOD14A1 active fire / thermal anomalies.",
        "dataset": DATASET, "band": BAND, "fire_threshold": f"{BAND} >= {FIRE_THRESHOLD}",
        "produces": "POINT annotator: adds fire_count, fire_density. Also points(bbox).",
        "functions": [
            "exposure(points, radius_km=5, years='2020-2025') -> + fire_count, fire_density",
            "points(bbox=[w,s,e,n], years) -> [{lat,lon,fire_days}]",
        ],
        "legend": LEGEND,
        "metric": "fire_count = sum of pixel-fire-days in the buffer over the period; "
                  "fire_density = fire_count / buffer_area_km2. Good for RANKING, not an "
                  "absolute fire area.",
        "gotcha": "~1 km resolution — buffers < 1 km are meaningless; use radius_km >= 3.",
        "example": "python /opt/data/connectors/fire.py exposure --points sites.csv --radius-km 5 --years 2020-2025",
    }


def _main(argv=None):
    ap = argparse.ArgumentParser(prog="fire")
    ap.add_argument("--describe", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    e = sub.add_parser("exposure"); e.add_argument("--points", required=True)
    e.add_argument("--radius-km", type=float, default=5); e.add_argument("--years", default="2020-2025")
    e.add_argument("--out")
    p = sub.add_parser("points"); p.add_argument("--bbox", required=True)
    p.add_argument("--years", default="2020-2025"); p.add_argument("--out")
    args = ap.parse_args(argv)
    if args.describe or not args.cmd:
        print(json.dumps(describe(), indent=2)); return
    if args.cmd == "exposure":
        write_points(exposure(read_points(args.points), args.radius_km, args.years), args.out)
    elif args.cmd == "points":
        bbox = [float(x) for x in args.bbox.split(",")]
        write_points(points(bbox, args.years), args.out)


if __name__ == "__main__":
    _main()
