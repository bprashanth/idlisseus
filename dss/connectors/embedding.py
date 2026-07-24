"""embedding connector — Google AlphaEarth Satellite Embedding (64-dim, 10 m, annual).

The similarity primitive: instead of one band value, each pixel is a 64-d learned
vector (unit-norm). Cosine similarity between two places = how alike they are across
everything the model saw. Powerful for restoration: how close is the site to an
intact reference forest, and is it *converging* year on year?

POINT ANNOTATOR:
  similarity(points, ref)        -> + embed_sim   (cosine to a reference point)
  similarity_trend(points, ref)  -> + sim_start, sim_end, sim_slope, converging
Vectors are unit-norm, so cosine == dot product.

CLI:
  python -m connectors.embedding --describe
  python -m connectors.embedding similarity --points sites.csv --ref 12.60,78.05 --year 2023
  python -m connectors.embedding similarity_trend --points sites.csv --ref 12.60,78.05 --years 2019-2024
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _base import init_ee, read_points, write_points

DATASET = "GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL"
NDIM = 64
SIM_EPS = 0.01   # cosine-sim change/yr above which we call it converging/diverging


def _img(ee, year):
    return ee.ImageCollection(DATASET).filterDate(f"{year}-01-01", f"{year + 1}-01-01").mosaic()


def _vectors(ee, img, latlons):
    """Sample the 64-d embedding at each (lat,lon). Returns list of 64-vectors."""
    bands = [f"A{ i:02d}" for i in range(NDIM)]
    feats = [ee.Feature(ee.Geometry.Point([lon, lat]), {"_i": i})
             for i, (lat, lon) in enumerate(latlons)]
    got = img.select(bands).sampleRegions(
        collection=ee.FeatureCollection(feats), scale=10, geometries=False).getInfo()["features"]
    by_i = {int(f["properties"]["_i"]): [f["properties"].get(b) for b in bands]
            for f in got}
    return [by_i.get(i) for i in range(len(latlons))]


def _cos(a, b):
    if not a or not b or None in a or None in b:
        return None
    return round(sum(x * y for x, y in zip(a, b)), 4)   # unit-norm -> dot == cosine


def similarity(points, ref, year=2023, project="plantwars"):
    """+embed_sim: cosine similarity of each point to the reference (lat,lon)."""
    ee = init_ee(project)
    img = _img(ee, year)
    refv = _vectors(ee, img, [ref])[0]
    vecs = _vectors(ee, img, [(p["lat"], p["lon"]) for p in points])
    return [{**p, "embed_sim": _cos(v, refv), "ref": f"{ref[0]},{ref[1]}", "year": year}
            for p, v in zip(points, vecs)]


def similarity_trend(points, ref, years="2019-2024", project="plantwars"):
    """+sim_start/sim_end/sim_slope/converging: is each point getting more like ref?"""
    ee = init_ee(project)
    a, _, b = years.partition("-")
    yrs = list(range(int(a), int(b) + 1)) if b else [int(a)]
    refvs = {y: _vectors(ee, _img(ee, y), [ref])[0] for y in yrs}
    series = {y: _vectors(ee, _img(ee, y), [(p["lat"], p["lon"]) for p in points]) for y in yrs}
    out = []
    for i, p in enumerate(points):
        sims = [(y, _cos(series[y][i], refvs[y])) for y in yrs]
        sims = [(y, s) for y, s in sims if s is not None]
        if len(sims) < 2:
            out.append({**p, "sim_start": None, "sim_end": None, "sim_slope": None,
                        "converging": None}); continue
        n = len(sims); mx = sum(y for y, _ in sims) / n; my = sum(s for _, s in sims) / n
        den = sum((y - mx) ** 2 for y, _ in sims)
        slope = sum((y - mx) * (s - my) for y, s in sims) / den if den else 0.0
        out.append({**p, "sim_start": sims[0][1], "sim_end": sims[-1][1],
                    "sim_slope": round(slope, 5),
                    "converging": "converging" if slope > SIM_EPS else
                    "diverging" if slope < -SIM_EPS else "stable"})
    return out


def describe():
    return {
        "connector": "embedding",
        "purpose": "AlphaEarth Satellite Embedding (64-d, 10 m, annual) — how alike two "
                   "places are, and whether a site is converging toward a reference over time.",
        "dataset": DATASET, "ndim": NDIM,
        "produces": "POINT annotator: similarity()->+embed_sim; similarity_trend()->"
                    "+sim_start,sim_end,sim_slope,converging.",
        "functions": [
            "similarity(points, ref=[lat,lon], year=2023) -> + embed_sim (cosine 0..1)",
            "similarity_trend(points, ref=[lat,lon], years='2019-2024') -> convergence",
        ],
        "use": "restoration convergence: similarity of the site to an INTACT reference "
               "forest; a rising trend = the site is becoming more forest-like. Cosine is "
               "unit-norm dot product; ~0.85 = very alike, ~0.5 = unlike (city vs forest).",
        "gotcha": "Embeddings mix everything (structure/phenology/moisture); high similarity "
                  "means 'looks alike to the model', not a specific variable. Pick the "
                  "reference carefully — it defines the target.",
        "example": "python /opt/data/connectors/embedding.py similarity_trend --points sites.csv --ref 12.60,78.05 --years 2019-2024",
    }


def _main(argv=None):
    ap = argparse.ArgumentParser(prog="embedding")
    ap.add_argument("--describe", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("similarity"); s.add_argument("--points", required=True)
    s.add_argument("--ref", required=True); s.add_argument("--year", type=int, default=2023); s.add_argument("--out")
    t = sub.add_parser("similarity_trend"); t.add_argument("--points", required=True)
    t.add_argument("--ref", required=True); t.add_argument("--years", default="2019-2024"); t.add_argument("--out")
    args = ap.parse_args(argv)
    if args.describe or not args.cmd:
        print(json.dumps(describe(), indent=2)); return
    ref = [float(x) for x in args.ref.split(",")]
    if args.cmd == "similarity":
        write_points(similarity(read_points(args.points), ref, args.year), args.out)
    elif args.cmd == "similarity_trend":
        write_points(similarity_trend(read_points(args.points), ref, args.years), args.out)


if __name__ == "__main__":
    _main()
