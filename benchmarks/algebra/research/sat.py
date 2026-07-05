#!/usr/bin/env python3
"""Compute the AOI's satellite indicators once (runs in the hermes image). Prints
JSON: NDVI trend, fire, land cover at a point. Real Earth-Engine reads."""
import json
import sys

sys.path.insert(0, "/opt/data")
from connectors.greenness import trend
from connectors.fire import exposure
from connectors.landcover import classify

lat, lon = float(sys.argv[1]), float(sys.argv[2])
pts = [{"id": "center", "lat": lat, "lon": lon}]
g = trend(pts, years="2019-2025")[0]
f = exposure(pts, radius_km=5, years="2020-2025")[0]
lc = classify(pts)[0]
print(json.dumps({
    "ndvi_trend": g["trend_class"], "ndvi_slope": g["ndvi_slope"], "ndvi_end": g["ndvi_end"],
    "fire_count_5km_5yr": f["fire_count"], "landcover": lc["landcover"],
    "source": "MODIS MOD13Q1 (NDVI) / MOD14A1 (fire) / ESA WorldCover"}))
