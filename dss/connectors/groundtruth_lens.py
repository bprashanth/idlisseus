"""groundtruth_lens — a REUSABLE ground-truthing view for ANY transfer/prediction.

The cross-cutting VERIFY layer (see ../SKILL_ALGEBRA.md): whenever a skill TRANSFERS a signal onto an
area (invasive likelihood, SDM/RF suitability, colocation, greening trend…), it can emit this instead of
just numbers — a self-contained HTML map showing **every method's prediction** (toggle between them) with a
**cursor lens** that reveals the high-res imagery underneath, so the user eyeballs what's actually there.
Often the truth is obvious in that one view; when the hot cells sit on orchards/scrub, the transfer is
visibly wrong. Generalises to invasives, "what grows here", "where is X vs Y", "is Y greening".

PIL-only (no numpy/rasterio) so it runs anywhere incl. the Hermes container. Self-contained (base image +
layers embedded as base64) → static .html, no server, no RAM. The agent hands back the file/link.

  build(base_img, bbox_wsen, layers, out, title)   # layers = {"name": [{"lat","lon","value"}...], ...}
  CLI: build --base <jpg/png> --bbox w,s,e,n --a1 <invasive data.json> --out <html>
"""
import argparse
import base64
import importlib.util
import io
import json
import os
import sys

# self-heal: the agent may run this with a `python` that lacks PIL. Re-exec with the venv that has it
# (same idea as _base does for `ee`), so `python groundtruth_lens.py …` just works.
_VENV = "/opt/hermes/.venv/bin/python3"
if (importlib.util.find_spec("PIL") is None and os.path.exists(_VENV)
        and not os.environ.get("_GT_REEXEC")):
    os.environ["_GT_REEXEC"] = "1"
    os.execv(_VENV, [_VENV] + sys.argv)

from PIL import Image


def _heat(t):
    """Concern ramp (intuitive): low = amber, mid = orange, high = red. On imagery, redder+thicker = the
    model is MORE confident this cell is the target (higher likelihood / higher concern)."""
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    stops = [(0, (255, 214, 64)), (0.5, (255, 122, 0)), (1, (226, 26, 12))]
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            f = (t - t0) / (t1 - t0) if t1 > t0 else 0
            return tuple(int(a + (b - a) * f) for a, b in zip(c0, c1))
    return (226, 26, 12)


def _b64(img, fmt="PNG"):
    buf = io.BytesIO(); img.save(buf, fmt, quality=88)
    return base64.b64encode(buf.getvalue()).decode()


def _render_base(base_path, maxpx=1500):
    im = Image.open(base_path).convert("RGB")
    im.thumbnail((maxpx, maxpx))
    return _b64(im, "JPEG"), im.size            # (W, H)


def _hex(t):
    return "#%02x%02x%02x" % _heat(t)


def _layer_svg(grid, bbox, W, H, thresh=0.4):
    """HOLLOW coloured squares outlining the modelled-transfer cells, drawn over the full imagery.
    Returns SVG <rect> markup (fill:none, coloured stroke) in the base's pixel coords. Only cells above
    threshold are drawn, so the imagery stays fully visible and attention lands on the outlined areas."""
    w, s, e, n = bbox
    pts = [(p["lon"], p["lat"], p["value"]) for p in grid if p.get("value") is not None]
    if not pts:
        return ""
    vmax = max(v for _, _, v in pts) or 1e-6
    lons = sorted({round(p[0], 6) for p in pts}); lats = sorted({round(p[1], 6) for p in pts})
    dl = min((b - a for a, b in zip(lons, lons[1:])), default=(e - w) / 12)
    da = min((b - a for a, b in zip(lats, lats[1:])), default=(n - s) / 12)
    cw = dl / (e - w) * W; ch = da / (n - s) * H
    rects = []
    for lon, lat, val in pts:
        if not (w <= lon <= e and s <= lat <= n):     # only draw cells inside the visible imagery
            continue
        t = val / vmax
        if t < thresh:
            continue
        x = (lon - w) / (e - w) * W - cw / 2
        y = (n - lat) / (n - s) * H - ch / 2
        rects.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{cw:.0f}" height="{ch:.0f}" rx="3" '
                     f'fill="none" stroke="{_hex(t)}" stroke-width="{2 + 2*t:.1f}" stroke-opacity="0.95"/>')
    return "".join(rects)


def build(base_img, bbox, layers, out, title="Where the model expects Lantana", subject="Lantana"):
    base_b64, (W, H) = _render_base(base_img)
    lp = {name: _layer_svg(grid, bbox, W, H) for name, grid in layers.items()}
    lp = {k: v for k, v in lp.items() if v}                      # keep only layers that have cells to draw
    names = list(lp.keys())
    radios = "".join(f'<input type=radio name=ly id=ly{i}{" checked" if i == 0 else ""}>' for i in range(len(names)))
    labels = "".join(f'<label for=ly{i}>{n}</label>' for i, n in enumerate(names))
    # aspect-locked stage: the SVG shares the image's exact box, so squares never stretch.
    overlays = "".join(f'<svg class="ov" id="ov{i}" viewBox="0 0 {W} {H}" preserveAspectRatio="none">{lp[n]}</svg>'
                       for i, n in enumerate(names))
    show = "".join(f"#ly{i}:checked~.stagewrap #ov{i}{{opacity:1}} "
                   f"#ly{i}:checked~.tabbar label[for=ly{i}]{{color:#e6edf3;border-bottom-color:#ff7b00}}"
                   for i in range(len(names)))
    ramp = "".join(f'<i style="background:{_hex(k/24)}"></i>' for k in range(25))
    doc = f"""<style>
html,body{{margin:0;height:100%;background:#0b0d12;color:#c9d1d9;font:13px/1.4 system-ui,-apple-system,sans-serif;overflow:hidden}}
header{{padding:9px 18px;background:#12151c;border-bottom:1px solid #262b36}}
.ttl{{font-weight:700;font-size:15px;color:#e6edf3}}
.sub{{color:#8b949e;font-size:12px;margin-top:2px}}
.sub b{{color:#ffb454}}
.bar{{display:flex;align-items:center;gap:16px;padding:6px 18px;background:#12151c;border-bottom:1px solid #262b36;flex-wrap:wrap}}
.tabbar label{{display:inline-block;padding:5px 13px;cursor:pointer;font-weight:600;color:#7d8590;border-bottom:2px solid transparent}}
.legend{{display:flex;align-items:center;gap:8px;font-size:11px;color:#8b949e;margin-left:auto}}
.ramp{{display:flex;height:11px;width:150px;border-radius:3px;overflow:hidden;box-shadow:0 0 0 1px #0006}}
.ramp i{{flex:1}}
.wrap>input{{display:none}}
.stagewrap{{text-align:center}}
.stage{{position:relative;display:inline-block;margin:8px auto;line-height:0}}
.stage img{{max-height:calc(100vh - 108px);max-width:98vw;display:block;border-radius:6px}}
.ov{{position:absolute;inset:0;width:100%;height:100%;opacity:0;transition:opacity .12s;pointer-events:none}}
{show}</style>
<header><div class="ttl">{title}</div>
<div class="sub">Full 35&nbsp;cm imagery. Coloured squares mark where the model expects {subject}. <b>These are
model estimates (likelihood) — not confirmed sightings; walk them to verify.</b></div></header>
<div class="wrap">{radios}
<div class="bar"><div class="tabbar">{labels}</div>
<div class="legend">less likely<div class="ramp">{ramp}</div>more likely {subject}</div></div>
<div class="stagewrap"><div class="stage"><img src="data:image/jpeg;base64,{base_b64}">{overlays}</div></div></div>"""
    open(out, "w").write(doc)
    print(f"wrote {out}  ({len(names)} layers: {names})")
    return out


def _layers_from_a1(a1_json):
    grid = json.load(open(a1_json)).get("grid", [])
    return {
        "RF (satellite model)": [{"lat": c["lat"], "lon": c["lon"], "value": c.get("rf_prob")} for c in grid],
        "phenology (stay-green)": [{"lat": c["lat"], "lon": c["lon"], "value": c.get("persist")} for c in grid],
        "combined likelihood": [{"lat": c["lat"], "lon": c["lon"], "value": c.get("likelihood")} for c in grid],
    }


def describe():
    return {
        "connector": "groundtruth_lens",
        "purpose": "Reusable VERIFY map: show a transfer/prediction with a cursor lens onto high-res imagery.",
        "produces": "a self-contained static HTML (no server) to eyeball predictions vs the ground.",
        "functions": ["build(base_img, bbox_wsen, layers, out, title)",
                      "CLI build --base <jpg/png> --bbox w,s,e,n --a1 <invasive data.json> --out <html>"],
        "use": "AFTER any transfer that maps a modelled signal (invasive, predict/RF/SDM, greening): build "
               "this so the user toggles methods + lenses onto high-res. --a1 auto-extracts the invasive "
               "map's RF/phenology/combined layers. --base is a plain JPEG/PNG of the scene; --bbox is its "
               "geographic extent w,s,e,n (a staged high-res JPEG lives at /opt/data/work/gt/).",
        "gotcha": "PIL-only (runs in-container). base + bbox must cover the SAME area as the layers. Static "
                  "HTML — hand back the file path, no server. Verify against occurrence (GBIF) + iNaturalist.",
        "example": "python /opt/data/connectors/groundtruth_lens.py build --base /opt/data/work/gt/ebtl_base.jpg "
                   "--bbox 78.176867,12.727863,78.190131,12.740135 --a1 /opt/data/work/invasive/lantana_camara/data.json "
                   "--out /opt/data/work/gt/lens.html",
    }


def _main(argv=None):
    ap = argparse.ArgumentParser(prog="groundtruth_lens")
    ap.add_argument("--describe", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    b = sub.add_parser("build")
    b.add_argument("--base", required=True); b.add_argument("--bbox", required=True)
    b.add_argument("--a1", required=True); b.add_argument("--out", required=True)
    b.add_argument("--title", default="Where the model expects Lantana")
    b.add_argument("--subject", default="Lantana")
    args = ap.parse_args(argv)
    if args.describe or not args.cmd:
        print(json.dumps(describe(), indent=2)); return
    bbox = [float(x) for x in args.bbox.split(",")]
    build(args.base, bbox, _layers_from_a1(args.a1), args.out, args.title, args.subject)


if __name__ == "__main__":
    _main()
