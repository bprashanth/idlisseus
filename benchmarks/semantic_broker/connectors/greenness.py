"""greenness connector — MODIS MOD13Q1 NDVI trend over time via Earth Engine.

The first TREND primitive: turns "is this plot recovering?" (a slope over years,
which v-1 could not hand-write in EE) into one call. POINT ANNOTATOR:
trend(points, years) adds `ndvi_start`, `ndvi_end`, `ndvi_slope` (NDVI change per
year, from a least-squares fit over annual-mean NDVI) and `trend_class`
(greening / flat / declining).

Owns the fiddly bits the LLM gets wrong: the dataset id, the NDVI band + its
0.0001 scale factor, the annual compositing, and the slope fit.

CLI:
  python -m connectors.greenness --describe
  python -m connectors.greenness trend --points sites.csv --years 2019-2024
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _base import init_ee, read_points, write_points

DATASET = "MODIS/061/MOD13Q1"   # 250 m, 16-day NDVI composite
BAND = "NDVI"
SCALE_FACTOR = 0.0001           # MOD13Q1 NDVI is stored *10000
SCALE_M = 250
# a site is "greening"/"declining" if |slope| exceeds this NDVI-per-year change;
# ~0.005 NDVI/yr is a modest but real vegetation trend at 250 m.
TREND_EPS = 0.005


def _years(years):
    """'2019-2024' -> [2019,2020,...,2024]. Single '2021' -> [2021]."""
    a, _, b = years.partition("-")
    a = int(a.strip()); b = int(b.strip()) if b else a
    return list(range(a, b + 1))


def _annual_ndvi_image(ee, yrs):
    """Multi-band image: one annual-mean NDVI band `y<year>` per year."""
    bands = []
    for y in yrs:
        coll = (ee.ImageCollection(DATASET)
                .filterDate(f"{y}-01-01", f"{y + 1}-01-01").select(BAND))
        bands.append(coll.mean().multiply(SCALE_FACTOR).rename(f"y{y}"))
    return ee.Image.cat(bands)


def _slope(xs, ys):
    """Least-squares slope of ys vs xs (ignoring None). None if < 2 points."""
    pairs = [(x, y) for x, y in zip(xs, ys) if y is not None]
    n = len(pairs)
    if n < 2:
        return None
    mx = sum(x for x, _ in pairs) / n
    my = sum(y for _, y in pairs) / n
    den = sum((x - mx) ** 2 for x, _ in pairs)
    if den == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in pairs) / den


def _classify(slope):
    if slope is None:
        return None
    if slope > TREND_EPS:
        return "greening"
    if slope < -TREND_EPS:
        return "declining"
    return "flat"


def trend(points, years="2019-2024", project="plantwars"):
    """Annotate points with NDVI trend over `years`."""
    ee = init_ee(project)
    yrs = _years(years)
    img = _annual_ndvi_image(ee, yrs)
    feats = [ee.Feature(ee.Geometry.Point([p["lon"], p["lat"]]), {"_i": i})
             for i, p in enumerate(points)]
    got = img.sampleRegions(collection=ee.FeatureCollection(feats),
                            scale=SCALE_M, geometries=False).getInfo()["features"]
    by_i = {int(f["properties"]["_i"]): f["properties"] for f in got}
    out = []
    for i, p in enumerate(points):
        pr = by_i.get(i, {})
        series = [pr.get(f"y{y}") for y in yrs]
        vals = [round(v, 4) if v is not None else None for v in series]
        slope = _slope(yrs, series)
        start = next((v for v in vals if v is not None), None)
        end = next((v for v in reversed(vals) if v is not None), None)
        out.append({**p,
                    "ndvi_start": start, "ndvi_end": end,
                    "ndvi_slope": round(slope, 5) if slope is not None else None,
                    "trend_class": _classify(slope)})
    return out


def describe():
    return {
        "connector": "greenness",
        "purpose": "MODIS MOD13Q1 NDVI trend over time (vegetation recovery/loss).",
        "dataset": DATASET, "band": BAND, "scale_factor": SCALE_FACTOR,
        "produces": "POINT annotator: adds ndvi_start, ndvi_end, ndvi_slope, trend_class.",
        "functions": [
            "trend(points, years='2019-2024') -> + ndvi_start, ndvi_end, ndvi_slope, trend_class",
        ],
        "metric": "ndvi_slope = least-squares NDVI change per year over annual-mean "
                  f"NDVI. trend_class: greening if slope > {TREND_EPS}, declining if "
                  f"< -{TREND_EPS}, else flat. Good for RANKING recovery, not absolute biomass.",
        "gotcha": "250 m pixels — a plot smaller than ~6 ha shares its cell with "
                  "surroundings; NDVI saturates over dense canopy, so a mature intact "
                  "forest reads high-and-flat, not 'not recovering'.",
        "example": "python /opt/data/connectors/greenness.py trend --points sites.csv --years 2019-2024",
    }


def _main(argv=None):
    ap = argparse.ArgumentParser(prog="greenness")
    ap.add_argument("--describe", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    t = sub.add_parser("trend"); t.add_argument("--points", required=True)
    t.add_argument("--years", default="2019-2024"); t.add_argument("--out")
    args = ap.parse_args(argv)
    if args.describe or not args.cmd:
        print(json.dumps(describe(), indent=2)); return
    if args.cmd == "trend":
        write_points(trend(read_points(args.points), args.years), args.out)


if __name__ == "__main__":
    _main()
