"""water connector — surface-water bodies + how long they hold water (JRC GSW, on GEE).

"Which pond dries up first?" / "how much water do our ponds hold?" need per-waterbody HYDROLOGY,
which we don't get from greenness alone. JRC Global Surface Water (1984-2021, 30 m) gives, per pixel:
  - seasonality: months/yr water is present (0-12) -> low = dries first, high = near-permanent
  - occurrence:  % of time water was present
  - recurrence:  % of years water returns
This connector finds the distinct waterbodies near a site and RANKS them by how early they dry
(ascending seasonality), and annotates points (known ponds) with their water metrics.

  ponds(bbox)      -> distinct waterbodies ranked by dries-first (seasonality/occurrence + area)
  at(points_csv)   -> annotate each point with seasonality/occurrence/recurrence

CLI:
  python -m connectors.water --describe
  python -m connectors.water ponds --bbox 78.15,12.70,78.22,12.77
  python -m connectors.water at --points ponds.csv --out /opt/data/work/ponds_water.csv
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _base import init_ee, read_points, write_points  # noqa: E402

GSW = "JRC/GSW1_4/GlobalSurfaceWater"


def ponds(bbox, max_bodies=20, min_area_ha=0.05, project="plantwars"):
    """Distinct surface-waterbodies near bbox, ranked by how EARLY they dry (low seasonality)."""
    ee = init_ee(project)
    region = ee.Geometry.Rectangle([float(x) for x in bbox])
    gsw = ee.Image(GSW).select(["seasonality", "occurrence", "recurrence"])
    mask = gsw.select("seasonality").gt(0).selfMask()
    bodies = mask.reduceToVectors(geometry=region, scale=30, geometryType="polygon",
                                  eightConnected=True, maxPixels=1e9, bestEffort=True)

    def enrich(f):
        s = gsw.reduceRegion(ee.Reducer.mean(), f.geometry(), 30, maxPixels=1e9)
        a = f.geometry().area(5).divide(1e4)
        return f.set({"seasonality": s.get("seasonality"), "occurrence": s.get("occurrence"),
                      "recurrence": s.get("recurrence"), "area_ha": a})
    bodies = bodies.map(enrich).filter(ee.Filter.gte("area_ha", min_area_ha))
    bodies = bodies.sort("area_ha", False).limit(max_bodies)
    feats = bodies.getInfo()["features"]
    out = []
    for f in feats:
        p = f["properties"]
        c = f["geometry"]
        # rough centroid from bbox of the polygon
        try:
            coords = c["coordinates"][0]
            lons = [x[0] for x in coords]; lats = [x[1] for x in coords]
            cen = [round(sum(lats) / len(lats), 5), round(sum(lons) / len(lons), 5)]
        except Exception:
            cen = None
        out.append({"centroid_latlon": cen, "area_ha": round(p.get("area_ha") or 0, 2),
                    "seasonality_months": round(p.get("seasonality") or 0, 1),
                    "occurrence_pct": round(p.get("occurrence") or 0, 1),
                    "recurrence_pct": round(p.get("recurrence") or 0, 1)})
    out.sort(key=lambda x: (x["seasonality_months"], x["occurrence_pct"]))  # dries first = first
    for i, b in enumerate(out):
        b["dries_first_rank"] = i + 1
    return {"aoi": bbox, "n_waterbodies": len(out), "waterbodies_ranked_dries_first": out,
            "note": "JRC Global Surface Water (1984-2021, 30 m). seasonality=months/yr water present "
                    "(LOW dries first), occurrence=% time wet, recurrence=% years water returns. "
                    "Historical satellite record — validate against this year's field observations; "
                    "small farm ponds < ~30 m may be missed (a data gap → note it)."}


def at(rows, project="plantwars"):
    """Annotate points (known ponds) with GSW seasonality/occurrence/recurrence."""
    ee = init_ee(project)
    gsw = ee.Image(GSW).select(["seasonality", "occurrence", "recurrence"])
    fc = ee.FeatureCollection([ee.Feature(ee.Geometry.Point([r["lon"], r["lat"]]), {"_i": i})
                               for i, r in enumerate(rows)])
    samp = gsw.reduceRegions(collection=fc, reducer=ee.Reducer.mean(), scale=30).getInfo()["features"]
    by = {int(f["properties"]["_i"]): f["properties"] for f in samp}
    out = []
    for i, r in enumerate(rows):
        p = by.get(i, {})
        out.append({**r, "seasonality_months": round(p.get("seasonality") or 0, 1),
                    "occurrence_pct": round(p.get("occurrence") or 0, 1),
                    "recurrence_pct": round(p.get("recurrence") or 0, 1)})
    return out


def describe():
    return {
        "connector": "water",
        "purpose": "Surface-water bodies + how long they hold water (JRC Global Surface Water, GEE). "
                   "Answers 'which pond dries first' (seasonality) and 'how reliable is this water'.",
        "produces": "ponds(bbox)->waterbodies ranked dries-first; at(points)->+seasonality/occurrence.",
        "functions": [
            "ponds(bbox) -> distinct waterbodies ranked by dries-first + area/seasonality/occurrence",
            "at(points) -> annotate known ponds with seasonality/occurrence/recurrence",
        ],
        "use": "Rank ponds by dries-first (low seasonality). Pair with greenness (dry-season stress) "
               "and terrain (catchment). Small farm ponds <30 m may be missed → honest gap + field ask.",
        "gotcha": "Historical (1984-2021) satellite record — a long-run pattern, not this year's level; "
                  "validate with field notes. Sub-30 m ponds under-detected.",
        "example": "python /opt/data/connectors/water.py ponds --bbox 78.15,12.70,78.22,12.77",
    }


def _main(argv=None):
    ap = argparse.ArgumentParser(prog="water")
    ap.add_argument("--describe", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("ponds"); p.add_argument("--bbox", required=True)
    a = sub.add_parser("at"); a.add_argument("--points", required=True); a.add_argument("--out")
    args = ap.parse_args(argv)
    if args.describe or not args.cmd:
        print(json.dumps(describe(), indent=2)); return
    if args.cmd == "ponds":
        print(json.dumps(ponds([float(x) for x in args.bbox.split(",")]), indent=2))
    elif args.cmd == "at":
        rows = at(read_points(args.points))
        if args.out:
            write_points(rows, args.out); print(f"wrote {len(rows)} -> {args.out}")
        else:
            print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    _main()
