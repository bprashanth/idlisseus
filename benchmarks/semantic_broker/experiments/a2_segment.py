#!/usr/bin/env python3
"""A2 — spatial Lantana segmentation on a high-res Vantor scene, + concordance with the free A1 map.

STATE-bucket method (see ../SKILL_ALGEBRA.md): detect Lantana by APPEARANCE — NDVI (vegetation) + local
texture roughness (Lantana forms dense tangled thickets, rougher than grass, more clumped than tree
crowns) + SLIC superpixels (OBIA). Without local labels it emits a normalized A2 score; a Phase-B
transfer classifier (learned on reference-region GBIF) can replace the heuristic.

Then H1/H3 from INVASIVE_MAP_BENCHMARK.md: map the A2 score onto the free A1 (S2) grid cells and measure
concordance (Spearman + top-decile IoU) → is "screen free, buy high-res on hotspots" valid? Emit an
agreement map (both / one / neither) + high-confidence waypoints.

Runs on the host A2 venv (rasterio/skimage), NOT the hermes container.
  a2venv/bin/python a2_segment.py analyze --cog scene.tif --a1 <lantana>/data.json --out out/
  a2venv/bin/python a2_segment.py selftest        # synthetic raster, validates the whole path
"""
import argparse
import json
import os
import sys

import numpy as np
import rasterio
from rasterio.warp import transform as warp_transform
from skimage.segmentation import slic
from skimage.filters.rank import entropy
from skimage.morphology import disk
from skimage.util import img_as_ubyte
from scipy.stats import spearmanr


def _read(cog):
    """Read a COG; map bands. Maxar WorldView-3 8-band order = coastal,blue,green,yellow,red,red-edge,
    NIR1,NIR2. Also handles 4-band BGRN and 3-band RGB. Yellow (Lantana's tawny flowering) + red-edge
    (vegetation vigour) are used when present."""
    with rasterio.open(cog) as ds:
        arr = ds.read().astype("float32")
        n = arr.shape[0]
        if n >= 8:                                   # WV-3 8-band
            b = {"blue": arr[1], "green": arr[2], "yellow": arr[3], "red": arr[4],
                 "rededge": arr[5], "nir": arr[6]}
        elif n == 4:                                 # BGRN
            b = {"blue": arr[0], "green": arr[1], "red": arr[2], "nir": arr[3]}
        else:                                        # RGB
            b = {"blue": arr[0], "green": arr[1] if n > 1 else arr[0], "red": arr[2] if n > 2 else arr[0],
                 "nir": None}
        b.setdefault("yellow", None); b.setdefault("rededge", None)
        return b, ds.transform, ds.crs, (ds.height, ds.width), ds


def _norm(x):
    x = np.nan_to_num(x)
    lo, hi = np.percentile(x, 2), np.percentile(x, 98)
    return np.clip((x - lo) / (hi - lo + 1e-9), 0, 1)


def a2_score(b):
    """Per-pixel Lantana-appearance score, tuned to the drone reference: Lantana reads as a VEGETATED
    (moderate–high NDVI), TAWNY/rust-cast (flowering panicles → red raised toward green, unlike the pure
    green of tree crowns), FINELY-ROUGH tangled mid-story. Water / bare rock / built / dry-senescent are
    masked out. Score = vegetated · (texture + tawny). It's still a heuristic — see the agreement map."""
    red, nir, green, blue = b["red"], b["nir"], b["green"], b.get("blue")
    yellow, rededge = b.get("yellow"), b.get("rededge")
    ndvi = ((nir - red) / (nir + red + 1e-6)) if nir is not None else ((green - red) / (green + red + 1e-6))
    veg = _norm(ndvi)
    # tawny/flowering cast: WV-3 yellow band captures Lantana's tan panicles directly; else use red-green.
    if yellow is not None:
        tawny = _norm((yellow - green) / (yellow + green + 1e-6))
    else:
        tawny = _norm((red - green) / (red + green + 1e-6))
    g = np.nan_to_num(green)
    gray = img_as_ubyte(np.clip((g - g.min()) / (np.ptp(g) + 1e-9), 0, 1))
    tex = _norm(entropy(gray, disk(4)).astype("float32"))    # fine local roughness
    score = veg * (0.45 * tex + 0.30 * tawny + 0.25 * veg)   # vegetated AND (rough + tawny)
    # masks: keep only real mid-story vegetation
    bright = _norm((red + green + (blue if blue is not None else red)) / 3.0)
    keep = (ndvi > 0.20)                                     # drop water / bare / built (low NDVI)
    keep &= ~((ndvi < 0.30) & (bright > 0.75))               # drop bright bare rock / rooftops
    score[~keep] = 0
    return _norm(score), veg, tex, ndvi


def segment(b, score, n_segments=1200):
    """OBIA: SLIC superpixels; average the A2 score per segment (object-level, less speckle)."""
    rgb = np.dstack([_norm(b["red"]), _norm(b["green"]), _norm(b["blue"])])
    seg = slic(rgb, n_segments=n_segments, compactness=8, start_label=0, channel_axis=-1,
               enforce_connectivity=True)
    if len(np.unique(seg)) < 10:      # degenerate (near-uniform image) -> skip OBIA, use pixel score
        return score, seg
    out = np.zeros_like(score)
    for s in np.unique(seg):
        m = seg == s
        out[m] = score[m].mean()
    return out, seg


def _u8(band):
    lo, hi = np.percentile(band, 2), np.percentile(band, 98)
    return np.clip((band - lo) / (hi - lo + 1e-9) * 255, 0, 255).astype("uint8")


def verify(b, seg_score, transform, crs, out_dir, n=10, crop_px=140):
    """Export RGB crops + an overview with numbered pins at the top well-separated candidates, so the
    detections can be eyeballed against the drone reference. Returns waypoints (lat/lon)."""
    from skimage.feature import peak_local_max
    from PIL import Image, ImageDraw
    rgb = np.dstack([_u8(b["red"]), _u8(b["green"]), _u8(b["blue"] if b.get("blue") is not None else b["red"])])
    peaks = peak_local_max(seg_score, min_distance=crop_px, threshold_abs=0.45, num_peaks=n)
    wpts = []
    for i, (r, c) in enumerate(peaks, 1):
        x, y = rasterio.transform.xy(transform, int(r), int(c))
        lon, lat = warp_transform(crs, "EPSG:4326", [x], [y])
        wpts.append({"rank": i, "lat": round(lat[0], 6), "lon": round(lon[0], 6),
                     "score": round(float(seg_score[r, c]), 3)})
        y0, y1, x0, x1 = max(0, r - crop_px), r + crop_px, max(0, c - crop_px), c + crop_px
        Image.fromarray(rgb[y0:y1, x0:x1]).resize((280, 280)).save(os.path.join(out_dir, f"cand_{i}.jpg"), quality=88)
    # overview with pins
    H, W = seg_score.shape
    sc = max(H, W) / 1400
    ov = Image.fromarray(rgb).resize((int(W / sc), int(H / sc)))
    dr = ImageDraw.Draw(ov)
    for i, (r, c) in enumerate(peaks, 1):
        px, py = c / sc, r / sc
        dr.ellipse([px - 9, py - 9, px + 9, py + 9], outline=(255, 40, 40), width=3)
        dr.text((px - 3, py - 6), str(i), fill=(255, 255, 0))
    ov.save(os.path.join(out_dir, "overview_pins.jpg"), quality=88)
    return wpts


def _pix_lonlat(transform, crs, shape, step=8):
    """Sample grid of (lon,lat) for pixel centres (subsampled by step)."""
    H, W = shape
    rows, cols = np.meshgrid(np.arange(0, H, step), np.arange(0, W, step), indexing="ij")
    xs, ys = rasterio.transform.xy(transform, rows.ravel(), cols.ravel())
    lon, lat = warp_transform(crs, "EPSG:4326", xs, ys)
    return (np.array(lon), np.array(lat), rows.ravel(), cols.ravel())


def concordance(seg_score, transform, crs, shape, a1_json, step=8):
    """Map the A2 segment score onto A1 (S2) grid cells; Spearman + top-decile IoU (H1)."""
    d = json.load(open(a1_json))
    grid = d["grid"]
    lon, lat, rr, cc = _pix_lonlat(transform, crs, shape, step)
    a2v = seg_score[rr, cc]
    # assign each sampled pixel to its nearest A1 cell, average A2 per cell
    glat = np.array([c["lat"] for c in grid]); glon = np.array([c["lon"] for c in grid])
    a1 = np.array([c["likelihood"] for c in grid])
    cellsum = np.zeros(len(grid)); cellcnt = np.zeros(len(grid))
    for i in range(len(lon)):
        j = int(np.argmin((glat - lat[i])**2 + (glon - lon[i])**2))
        cellsum[j] += a2v[i]; cellcnt[j] += 1
    covered = cellcnt > 0
    a2cell = np.where(covered, cellsum / np.maximum(cellcnt, 1), np.nan)
    m = covered & ~np.isnan(a2cell)
    if m.sum() < 8:
        return {"n_cells": int(m.sum()), "note": "too few overlapping cells for concordance"}
    if np.ptp(a2cell[m]) < 1e-6 or np.ptp(a1[m]) < 1e-6:
        return {"n_cells": int(m.sum()), "spearman_rho": None,
                "note": "A2 or A1 is ~constant over the overlap — concordance undefined"}
    rho, p = spearmanr(a1[m], a2cell[m])
    # top-decile IoU
    ta1 = a1[m] >= np.percentile(a1[m], 90); ta2 = a2cell[m] >= np.percentile(a2cell[m], 90)
    iou = float((ta1 & ta2).sum() / max((ta1 | ta2).sum(), 1))
    verdict = ("a: concordant (S2 screening works — buy high-res only on hotspots)" if rho > 0.4 else
               "b/c: weak/divergent (S2 alone biased here — high-res adds real information)")
    return {"n_cells": int(m.sum()), "spearman_rho": round(float(rho), 3), "p": round(float(p), 4),
            "top_decile_iou": round(iou, 3), "H1_verdict": verdict,
            "a1_at_a2_hot": round(float(a1[m][ta2].mean()), 3) if ta2.any() else None}


def analyze(cog, a1_json, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    b, transform, crs, shape, ds = _read(cog)
    score, veg, tex, ndvi = a2_score(b)
    seg_score, seg = segment(b, score)
    conc = concordance(seg_score, transform, crs, shape, a1_json)
    wpts = verify(b, seg_score, transform, crs, out_dir)          # RGB crops + pinned overview
    # save artifacts
    np.save(os.path.join(out_dir, "a2_score.npy"), seg_score.astype("float32"))
    _save_png(seg_score, os.path.join(out_dir, "a2_segments.png"))
    result = {"cog": cog, "bands": {k: (v is not None) for k, v in b.items()},
              "has_nir": b["nir"] is not None, "shape": list(shape),
              "a2_high_frac": round(float((seg_score >= 0.6).mean()), 4),
              "candidates": wpts, "concordance": conc,
              "method": "STATE: NDVI + tawny(red-green) + local-entropy texture + SLIC OBIA, non-veg masked"}
    json.dump(result, open(os.path.join(out_dir, "a2_result.json"), "w"), indent=1)
    print(json.dumps(result, indent=1))
    return result


def _save_png(arr, path):
    from PIL import Image
    a = (_norm(arr) * 255).astype("uint8")
    # viridis-ish: map through a simple colormap
    r = np.clip(1.5 * a - 100, 0, 255); g = np.clip(a, 0, 255); bl = np.clip(200 - a, 0, 255)
    Image.fromarray(np.dstack([r, g, bl]).astype("uint8")).save(path)


def selftest():
    """Synthetic 4-band scene + fake A1 grid → exercises read/NDVI/texture/SLIC/concordance."""
    import tempfile
    from affine import Affine
    H = W = 200
    rng = np.random.default_rng(0)
    # SMOOTH background (low texture): near-uniform grass/soil
    red = np.full((H, W), 0.20, "float32") + rng.normal(0, 0.01, (H, W)).astype("float32")
    nir = np.full((H, W), 0.26, "float32") + rng.normal(0, 0.01, (H, W)).astype("float32")
    green = np.full((H, W), 0.20, "float32") + rng.normal(0, 0.01, (H, W)).astype("float32")
    blue = np.full((H, W), 0.15, "float32") + rng.normal(0, 0.01, (H, W)).astype("float32")
    # ROUGH vegetated "thicket" (high NIR = veg, and rough/noisy = high local entropy) in one corner
    nir[20:70, 20:70] = 0.80 + rng.uniform(0, 0.15, (50, 50))
    green[20:70, 20:70] = 0.35 + rng.uniform(0, 0.20, (50, 50))
    red[20:70, 20:70] = 0.12 + rng.uniform(0, 0.06, (50, 50))
    d = tempfile.mkdtemp()
    cog = os.path.join(d, "syn.tif")
    tr = Affine.translation(78.177, 12.740) * Affine.scale(0.000065, -0.000060)  # ~ the crop, north-up
    with rasterio.open(cog, "w", driver="GTiff", height=H, width=W, count=4, dtype="float32",
                       crs="EPSG:4326", transform=tr) as dst:
        for i, band in enumerate([blue, green, red, nir], 1):
            dst.write(band, i)
    # fake A1 grid over the same extent, high likelihood in the thicket corner
    grid = []
    for r in range(14):
        for c in range(14):
            lat = 12.740 - 0.060 * 0.000 - (r + 0.5) / 14 * (H * 0.000060)
            lon = 78.177 + (c + 0.5) / 14 * (W * 0.000065)
            hi = 1.0 if (r < 5 and c < 5) else 0.1
            grid.append({"lat": lat, "lon": lon, "likelihood": round(hi + rng.uniform(0, 0.1), 3)})
    a1 = os.path.join(d, "data.json"); json.dump({"grid": grid, "bbox": [78.177, 12.728, 78.190, 12.740]}, open(a1, "w"))
    res = analyze(cog, a1, os.path.join(d, "out"))
    assert res["has_nir"] and res["concordance"].get("spearman_rho") is not None
    print("\nSELFTEST OK — concordance rho:", res["concordance"]["spearman_rho"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze"); a.add_argument("--cog", required=True); a.add_argument("--a1", required=True)
    a.add_argument("--out", default="a2_out")
    sub.add_parser("selftest")
    args = ap.parse_args()
    if args.cmd == "selftest":
        selftest()
    else:
        analyze(args.cog, args.a1, args.out)
