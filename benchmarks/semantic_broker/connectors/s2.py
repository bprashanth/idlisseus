"""s2 connector — Sentinel-2 10 m detail (canopy density / greenness) on Earth Engine.

Our other layers are coarser: WorldCover is 10 m but only broad CLASSES; MODIS greenness is ~250 m;
AlphaEarth embeds S2 but as an opaque 64-d vector. When a question needs FINER structure than a
land-cover class — "how dense is the canopy here", "is this patch bare or vegetated", dry-season
stress at fine scale — raw Sentinel-2 (COPERNICUS/S2_SR_HARMONIZED, 10 m, free) is the right tool.

  at(points, year)   -> annotate points with NDVI (canopy-density proxy) + a dense/sparse label
  summary(bbox, year)-> mean NDVI + % dense (canopy) over an area

NOTE: 10 m NDVI is a canopy/greenness proxy — it does NOT identify tree species (that needs
hyperspectral: EMIT/Pixxel). Cloud-masked seasonal median.

CLI:
  python -m connectors.s2 --describe
  python -m connectors.s2 at --points sites.csv --out /opt/data/work/s2.csv
  python -m connectors.s2 summary --bbox 78.170,12.721,78.197,12.747
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _base import init_ee, read_points, write_points  # noqa: E402

S2 = "COPERNICUS/S2_SR_HARMONIZED"
WORLDCOVER = "ESA/WorldCover/v200"
DENSE = 0.5   # NDVI >= this ~ closed/dense canopy; 0.2-0.5 ~ sparse/scrub; < 0.2 ~ bare/built

# --- phenology windows for the Krishnagiri / dry-Deccan NE-monsoon cycle ---
# green/wet flush lands AFTER the NE monsoon (Dec-Feb); peak dry/brown is Mar-mid-Jun (pre-SW-monsoon).
WET = ("-12-15", "-03-01")   # (year-1) Dec 15 -> (year) Mar 01  : greenest
DRY = ("-03-15", "-06-15")   # (year)   Mar 15 -> (year) Jun 15  : brownest
STAY_GREEN = 0.40   # dry-season NDVI still >= this = canopy retained through the dry season
RETAIN = 0.70       # dry/wet NDVI ratio >= this = keeps most of its greenness (evergreen-like)


def _mask(img):
    scl = img.select("SCL")
    ok = scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10)).And(scl.neq(11))  # shadow/cloud/cirrus/snow
    return img.updateMask(ok)


def _ndvi(ee, year, geom):
    """Cloud-masked annual median NDVI at 10 m."""
    col = (ee.ImageCollection(S2).filterDate(f"{year}-01-01", f"{year + 1}-01-01")
           .filterBounds(geom).filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 40)).map(_mask))
    return col.median().normalizedDifference(["B8", "B4"]).rename("ndvi")


def _ndvi_window(ee, year, window, geom):
    """Cloud-masked median NDVI over a seasonal window (start may be in year-1, e.g. the wet flush)."""
    s_md, e_md = window
    start = f"{year - 1 if s_md.startswith('-12') else year}{s_md}"
    end = f"{year}{e_md}"
    col = (ee.ImageCollection(S2).filterDate(start, end)
           .filterBounds(geom).filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 40)).map(_mask))
    return col.median().normalizedDifference(["B8", "B4"]).rename("ndvi")


def _anomaly_img(ee, year, geom):
    """The invasive-LIKELIHOOD phenology stack for the AOI.
    Native dry-deciduous forest DROPS its leaves in the dry season (NDVI falls); Lantana & other
    evergreen invaders STAY GREEN. So a pixel that is vegetated in the wet flush AND retains greenness
    through the dry season is an evergreen/invasive CANDIDATE. Crops/built/water are masked (they also
    stay green under irrigation) via ESA WorldCover — what's left is the honest natural-veg signal.
    Bands: ndvi_wet, ndvi_dry, retain(=dry/wet), stay_green(0/1 candidate)."""
    wet = _ndvi_window(ee, year, WET, geom)
    dry = _ndvi_window(ee, year, DRY, geom)
    retain = dry.divide(wet.max(0.05)).rename("retain")           # avoid /0 on bare
    wc = ee.ImageCollection(WORLDCOVER).first().select("Map")
    natural = wc.neq(40).And(wc.neq(50)).And(wc.neq(80))          # drop cropland(40)/built(50)/water(80)
    vegetated = wet.gte(0.30)                                      # was green in the wet flush
    candidate = (dry.gte(STAY_GREEN).And(retain.gte(RETAIN))
                 .And(vegetated).And(natural)).rename("stay_green")
    return (wet.rename("ndvi_wet").addBands(dry.rename("ndvi_dry"))
            .addBands(retain).addBands(candidate).addBands(wc.rename("worldcover")))


def anomaly(bbox, year=2024, project="plantwars"):
    """AREA SUMMARY of the dry-season stay-green (invasive-likelihood) signal over a bbox."""
    ee = init_ee(project)
    geom = ee.Geometry.Rectangle([float(x) for x in bbox])
    img = _anomaly_img(ee, year, geom)
    r = img.select(["ndvi_wet", "ndvi_dry", "retain", "stay_green"]).reduceRegion(
        ee.Reducer.mean(), geom, 10, maxPixels=1e10).getInfo()
    return {"aoi": bbox, "year": year,
            "mean_ndvi_wet": round(r.get("ndvi_wet") or 0, 3),
            "mean_ndvi_dry": round(r.get("ndvi_dry") or 0, 3),
            "mean_retain": round(r.get("retain") or 0, 3),
            "pct_stay_green_candidate": round((r.get("stay_green") or 0) * 100, 1),
            "windows": {"wet": WET, "dry": DRY}, "thresholds": {"stay_green_ndvi": STAY_GREEN, "retain": RETAIN},
            "note": "Stay-green = vegetated in the wet flush AND retains greenness through the dry season, "
                    "on natural land (crop/built/water masked via ESA WorldCover). It is an INVASIVE-"
                    "LIKELIHOOD proxy (evergreen riparian natives also stay green) — NOT a species ID. "
                    "Confirm candidates by AlphaEarth similarity to known presence + a 3 m Planet scene."}


def anomaly_at(rows, year=2024, project="plantwars"):
    """Annotate points with the phenology anomaly (ndvi_wet, ndvi_dry, retain, stay_green flag)."""
    ee = init_ee(project)
    fc = ee.FeatureCollection([ee.Feature(ee.Geometry.Point([r["lon"], r["lat"]]), {"_i": i})
                               for i, r in enumerate(rows)])
    img = _anomaly_img(ee, year, fc.geometry().bounds())
    samp = img.select(["ndvi_wet", "ndvi_dry", "retain", "stay_green", "worldcover"]).reduceRegions(
        collection=fc, reducer=ee.Reducer.mean(), scale=10).getInfo()["features"]
    by = {int(f["properties"]["_i"]): f["properties"] for f in samp}
    out = []
    for i, r in enumerate(rows):
        p = by.get(i, {})
        out.append({**r,
                    "ndvi_wet": round(p.get("ndvi_wet"), 3) if p.get("ndvi_wet") is not None else None,
                    "ndvi_dry": round(p.get("ndvi_dry"), 3) if p.get("ndvi_dry") is not None else None,
                    "retain": round(p.get("retain"), 3) if p.get("retain") is not None else None,
                    "stay_green": int(round(p.get("stay_green"))) if p.get("stay_green") is not None else None,
                    "worldcover": int(p["worldcover"]) if p.get("worldcover") is not None else None})
    return out


def anomaly_grid(bbox, year=2024, n=30, project="plantwars"):
    """Sample an n×n grid over the bbox and return each cell's anomaly fields — the raw material
    for a free invasive-LIKELIHOOD map. One reduceRegions call, so keep n modest (<=40)."""
    w, s, e, nth = [float(x) for x in bbox]
    rows = [{"lat": s + (nth - s) * (r + 0.5) / n, "lon": w + (e - w) * (c + 0.5) / n}
            for r in range(n) for c in range(n)]
    return anomaly_at(rows, year, project)


def at(rows, year=2023, project="plantwars"):
    """Annotate points with 10 m NDVI (canopy-density proxy) + a plain dense/sparse/bare label."""
    ee = init_ee(project)
    fc = ee.FeatureCollection([ee.Feature(ee.Geometry.Point([r["lon"], r["lat"]]), {"_i": i})
                               for i, r in enumerate(rows)])
    ndvi = _ndvi(ee, year, fc.geometry().bounds())
    samp = ndvi.reduceRegions(collection=fc, reducer=ee.Reducer.mean(), scale=10).getInfo()["features"]
    by = {int(f["properties"]["_i"]): f["properties"].get("mean") for f in samp}
    out = []
    for i, r in enumerate(rows):
        v = by.get(i)
        label = "dense canopy" if (v or 0) >= DENSE else ("sparse/scrub" if (v or 0) >= 0.2 else "bare/built")
        out.append({**r, "ndvi_10m": round(v, 3) if v is not None else None, "cover_10m": label})
    return out


def summary(bbox, year=2023, project="plantwars"):
    """Mean NDVI + % dense canopy over the bbox at 10 m."""
    ee = init_ee(project)
    geom = ee.Geometry.Rectangle([float(x) for x in bbox])
    ndvi = _ndvi(ee, year, geom)
    mean = ndvi.reduceRegion(ee.Reducer.mean(), geom, 10, maxPixels=1e10).get("ndvi").getInfo()
    dense = ndvi.gte(DENSE).reduceRegion(ee.Reducer.mean(), geom, 10, maxPixels=1e10).get("ndvi").getInfo()
    return {"aoi": bbox, "year": year, "mean_ndvi_10m": round(mean, 3) if mean is not None else None,
            "pct_dense_canopy": round((dense or 0) * 100, 1),
            "note": "Sentinel-2 10 m NDVI (canopy-density/greenness proxy, cloud-masked seasonal median). "
                    "Finer than WorldCover classes & MODIS greenness. Does NOT identify tree species "
                    "(that needs hyperspectral — EMIT/Pixxel)."}


def describe():
    return {
        "connector": "s2",
        "purpose": "Sentinel-2 10 m canopy-density / greenness detail (finer than land-cover classes).",
        "produces": "at(points)->+ndvi_10m,+cover_10m; summary(bbox)->mean_ndvi + %dense.",
        "functions": [
            "at(points, year) -> +ndvi_10m + cover_10m (dense canopy / sparse-scrub / bare)",
            "summary(bbox, year) -> mean_ndvi_10m + pct_dense_canopy",
            "anomaly(bbox, year) -> SUMMARY of dry-season STAY-GREEN (invasive-likelihood): natives go "
            "bare in the dry season, evergreen invaders (Lantana) stay green. crop/built/water masked.",
            "anomaly_at(points, year) -> + ndvi_wet, ndvi_dry, retain, stay_green(0/1), worldcover",
            "anomaly_grid(bbox, year, n) -> n×n sampled grid of the anomaly fields (raw material for a "
            "free invasive-likelihood MAP; feed to embedding-similarity + GBIF to confirm).",
        ],
        "use": "When 'Tree cover' (WorldCover) is too coarse and you need canopy DENSITY / bare-vs-veg at "
               "10 m, or fine dry-season stress. For 'where are the invasives / where is the lantana' use "
               "anomaly/anomaly_grid (stay-green phenology) then confirm with embedding + occurrence. "
               "Pair with greenness (trend over time), landcover (class).",
        "gotcha": "10 m NDVI is a density proxy, NOT species ID (use hyperspectral for that). Stay-green is "
                  "invasive-LIKELIHOOD, not proof (evergreen riparian natives also stay green — confirm by "
                  "similarity to known presence). Cloud-masked median; sparse-data seasons can be noisy. Free.",
        "example": "python /opt/data/connectors/s2.py anomaly --bbox 78.170,12.721,78.197,12.747",
    }


def _main(argv=None):
    ap = argparse.ArgumentParser(prog="s2")
    ap.add_argument("--describe", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    a = sub.add_parser("at"); a.add_argument("--points", required=True); a.add_argument("--out")
    a.add_argument("--year", type=int, default=2023)
    s = sub.add_parser("summary"); s.add_argument("--bbox", required=True); s.add_argument("--year", type=int, default=2023)
    an = sub.add_parser("anomaly"); an.add_argument("--bbox", required=True); an.add_argument("--year", type=int, default=2024)
    aa = sub.add_parser("anomaly_at"); aa.add_argument("--points", required=True); aa.add_argument("--out")
    aa.add_argument("--year", type=int, default=2024)
    ag = sub.add_parser("anomaly_grid"); ag.add_argument("--bbox", required=True); ag.add_argument("--out")
    ag.add_argument("--year", type=int, default=2024); ag.add_argument("--n", type=int, default=30)
    args = ap.parse_args(argv)
    if args.describe or not args.cmd:
        print(json.dumps(describe(), indent=2)); return
    if args.cmd == "at":
        rows = at(read_points(args.points), args.year)
        if args.out:
            write_points(rows, args.out); print(f"wrote {len(rows)} -> {args.out}")
        else:
            print(json.dumps(rows, indent=2))
    elif args.cmd == "summary":
        print(json.dumps(summary([float(x) for x in args.bbox.split(",")], args.year), indent=2))
    elif args.cmd == "anomaly":
        print(json.dumps(anomaly([float(x) for x in args.bbox.split(",")], args.year), indent=2))
    elif args.cmd in ("anomaly_at", "anomaly_grid"):
        rows = (anomaly_at(read_points(args.points), args.year) if args.cmd == "anomaly_at"
                else anomaly_grid([float(x) for x in args.bbox.split(",")], args.year, args.n))
        if args.out:
            write_points(rows, args.out); print(f"wrote {len(rows)} -> {args.out}")
        else:
            print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    _main()
