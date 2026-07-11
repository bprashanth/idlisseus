"""hyperspectral connector — NASA EMIT (285-band imaging spectroscopy) via Earth Engine.

Narrow-band indices you can't get from broadband satellites — canopy water, red-edge
chlorophyll, and cellulose/dry-matter (litter, senescence, dry invasives). Useful for
restoration quality and native-vs-invasive discrimination.

POINT ANNOTATOR: indices(points) adds ndvi_hyp, ndwi_hyp (canopy water),
rededge (chlorophyll), cai (cellulose absorption). EMIT is targeted/sparse, so a
point with no acquisition returns nulls + coverage=False (honest, not an error).

CLI:
  python -m connectors.hyperspectral --describe
  python -m connectors.hyperspectral indices --points sites.csv
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _base import init_ee, read_points, write_points

DATASET = "NASA/EMIT/L2A/RFL"
# target wavelengths (nm) -> resolved to nearest EMIT band at runtime
_WL = {"r670": 670, "r705": 705, "r750": 750, "r800": 800, "r860": 860,
       "r1240": 1240, "r2000": 2000, "r2100": 2100, "r2200": 2200}


def _bbox(points, pad=0.05):
    lats = [p["lat"] for p in points]; lons = [p["lon"] for p in points]
    return [min(lons) - pad, min(lats) - pad, max(lons) + pad, max(lats) + pad]


def _band_for(wl_list, target):
    return "reflectance_%d" % min(range(len(wl_list)), key=lambda i: abs(wl_list[i] - target))


def indices(points, project="plantwars"):
    ee = init_ee(project)
    coll = ee.ImageCollection(DATASET).filterBounds(ee.Geometry.Rectangle(_bbox(points)))
    wl = ee.Image(coll.first()).get("reflectance_wavelengths").getInfo()
    band = {k: _band_for(wl, t) for k, t in _WL.items()}
    img = coll.select(list(dict.fromkeys(band.values()))).median()
    feats = [ee.Feature(ee.Geometry.Point([p["lon"], p["lat"]]), {"_i": i})
             for i, p in enumerate(points)]
    got = img.sampleRegions(collection=ee.FeatureCollection(feats), scale=60,
                            geometries=False).getInfo()["features"]
    by_i = {int(f["properties"]["_i"]): f["properties"] for f in got}

    def _nd(a, b):
        if a is None or b is None or (a + b) == 0:
            return None
        return round((a - b) / (a + b), 4)

    out = []
    for i, p in enumerate(points):
        r = by_i.get(i, {})
        v = {k: r.get(band[k]) for k in band}
        cov = all(v[k] is not None for k in ("r670", "r800"))
        cai = (round(0.5 * (v["r2000"] + v["r2200"]) - v["r2100"], 4)
               if None not in (v["r2000"], v["r2100"], v["r2200"]) else None)
        out.append({**p, "coverage": cov,
                    "ndvi_hyp": _nd(v["r800"], v["r670"]),
                    "ndwi_hyp": _nd(v["r860"], v["r1240"]),
                    "rededge": _nd(v["r750"], v["r705"]), "cai": cai})
    return out


def describe():
    return {
        "connector": "hyperspectral",
        "purpose": "NASA EMIT imaging spectroscopy (285 bands, 381-2493 nm) narrow-band indices.",
        "dataset": DATASET, "n_bands": 285,
        "produces": "POINT annotator: adds ndvi_hyp, ndwi_hyp (canopy water), rededge "
                    "(chlorophyll), cai (cellulose/dry-matter). coverage=False if no EMIT scene.",
        "functions": ["indices(points) -> + ndvi_hyp, ndwi_hyp, rededge, cai, coverage"],
        "use": "restoration quality + native-vs-invasive/senescence discrimination via canopy "
               "chemistry that broadband (MODIS/WorldCover) can't see. Feed these + embeddings "
               "into the `predict` RF for stronger models.",
        "gotcha": "EMIT is targeted/sparse (ISS) — many points have NO acquisition (coverage="
                  "False, nulls). Never treat a null as zero; it means 'not imaged'.",
        "example": "python /opt/data/connectors/hyperspectral.py indices --points sites.csv",
    }


def _main(argv=None):
    ap = argparse.ArgumentParser(prog="hyperspectral")
    ap.add_argument("--describe", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    c = sub.add_parser("indices"); c.add_argument("--points", required=True); c.add_argument("--out")
    args = ap.parse_args(argv)
    if args.describe or not args.cmd:
        print(json.dumps(describe(), indent=2)); return
    if args.cmd == "indices":
        write_points(indices(read_points(args.points)), args.out)


if __name__ == "__main__":
    _main()
