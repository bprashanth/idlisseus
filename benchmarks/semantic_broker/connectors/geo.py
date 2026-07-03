"""geo connector — pure-python spatial joins (no Earth Engine, no API).

The asset-to-asset glue the agent kept hand-rolling: proximity and containment.
- nearest(points, others)        -> + nearest_dist_km (+ nearest_id)
- buffer_count(points, others, r)-> + n_within  (count of others within r km)
- within(points, polygons)       -> + inside (bool) (+ poly_name)

CLI:
  python -m connectors.geo nearest --points lantana.csv --others fields.csv
  python -m connectors.geo buffer_count --points sites.csv --others fires.csv --radius-km 5
  python -m connectors.geo within --points occ.csv --polygons areas.geojson
"""
import argparse
import json
import os
import sys
from math import asin, cos, radians, sin, sqrt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _base import read_points, write_points


def _km(a, b):
    dlat, dlon = radians(b["lat"] - a["lat"]), radians(b["lon"] - a["lon"])
    h = sin(dlat / 2) ** 2 + cos(radians(a["lat"])) * cos(radians(b["lat"])) * sin(dlon / 2) ** 2
    return 2 * 6371 * asin(sqrt(h))


def nearest(points, others):
    out = []
    for p in points:
        best, bid = None, None
        for o in others:
            d = _km(p, o)
            if best is None or d < best:
                best, bid = d, o.get("id")
        out.append({**p, "nearest_dist_km": round(best, 3) if best is not None else None,
                    "nearest_id": bid})
    return out


def buffer_count(points, others, radius_km=5):
    return [{**p, "n_within": sum(1 for o in others if _km(p, o) <= radius_km)}
            for p in points]


def _in_ring(lat, lon, ring):
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]   # lon, lat
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def within(points, polygons_geojson):
    """polygons_geojson: a GeoJSON FeatureCollection of Polygons (optionally with a name)."""
    feats = polygons_geojson.get("features", polygons_geojson) if isinstance(polygons_geojson, dict) else polygons_geojson
    polys = []
    for f in feats:
        geom = f.get("geometry", f)
        name = (f.get("properties") or {}).get("name") or (f.get("properties") or {}).get("NAME")
        coords = geom["coordinates"]
        rings = coords if geom["type"] == "Polygon" else [c[0] for c in coords]
        polys.append((name, rings if geom["type"] == "Polygon" else coords))
    out = []
    for p in points:
        hit_name = None
        for name, coords in polys:
            outer = coords[0]
            if _in_ring(p["lat"], p["lon"], outer):
                hit_name = name or True
                break
        out.append({**p, "inside": bool(hit_name), "poly_name": hit_name if isinstance(hit_name, str) else None})
    return out


def describe():
    return {
        "connector": "geo",
        "purpose": "Pure-python spatial joins between two point/polygon sets (no API).",
        "produces": "POINT annotator over asset data.",
        "functions": [
            "nearest(points, others) -> + nearest_dist_km, nearest_id",
            "buffer_count(points, others, radius_km) -> + n_within",
            "within(points, polygons_geojson) -> + inside, poly_name",
        ],
        "gotcha": "Distances are great-circle km; fine for ranking at landscape "
                  "scale. within() uses outer rings only (ignores holes).",
        "example": "python /opt/data/connectors/geo.py nearest --points lantana.csv --others fields.csv",
    }


def _main(argv=None):
    ap = argparse.ArgumentParser(prog="geo")
    ap.add_argument("--describe", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    ne = sub.add_parser("nearest"); ne.add_argument("--points", required=True); ne.add_argument("--others", required=True); ne.add_argument("--out")
    bc = sub.add_parser("buffer_count"); bc.add_argument("--points", required=True); bc.add_argument("--others", required=True)
    bc.add_argument("--radius-km", type=float, default=5); bc.add_argument("--out")
    wi = sub.add_parser("within"); wi.add_argument("--points", required=True); wi.add_argument("--polygons", required=True); wi.add_argument("--out")
    args = ap.parse_args(argv)
    if args.describe or not args.cmd:
        print(json.dumps(describe(), indent=2)); return
    if args.cmd == "nearest":
        write_points(nearest(read_points(args.points), read_points(args.others)), args.out)
    elif args.cmd == "buffer_count":
        write_points(buffer_count(read_points(args.points), read_points(args.others), args.radius_km), args.out)
    elif args.cmd == "within":
        with open(args.polygons) as f:
            polys = json.load(f)
        write_points(within(read_points(args.points), polys), args.out)


if __name__ == "__main__":
    _main()
