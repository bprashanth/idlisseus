#!/usr/bin/env python3
"""EBTL DSS front-end — single self-contained page (public S3), desktop + mobile.

Landing = zoomed-out Sentinel-2 overview with 3 broad problem markers. Scroll / pinch-zoom (or tap) a
marker => smooth zoom into the high-res 35 cm Maxar map, auto-focused on that problem. Each issue's
in-depth panel carries: a plain-language PROBLEM description, the QUESTIONS that surfaced it (from the EBTL
syllabus) + PAPERS consulted (DOIs), the METHOD (clarified: stay-green vegetation phenology, NOT wildfire),
the ecological DRIVERS from the literature, an honest limit, and the data we still need.

Lantana has three toggleable layers: Prediction (cells where BOTH the satellite model and the stay-green
phenology score high), Drivers (canopy-gap cells — Lantana favours open/disturbed canopy), and Records
(the ACTUAL 14 GBIF+iNaturalist points on a wide base, with distance rings — all >13 km from the site).

  python issues_app.py   # -> agents/hermes/gt/index.html
"""
import base64
import csv
import io
import json
import math
import os

from PIL import Image, ImageEnhance

HERE = os.path.dirname(os.path.abspath(__file__))
GT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "agents", "hermes", "gt"))
CROP = [78.176867, 12.727863, 78.190131, 12.740135]     # Maxar crop w,s,e,n
DONOR = [77.98, 12.55, 78.35, 12.86]                    # wide S2 base for the records view
SITE = (78.170, 12.721, 78.197, 12.747)
SITE_C = (78.18344, 12.73394)                            # lon, lat


def _b64(path, enhance=None, maxpx=2000):
    im = Image.open(path).convert("RGB")
    im.thumbnail((maxpx, maxpx))
    if enhance:
        im = ImageEnhance.Brightness(im).enhance(enhance[0])
        im = ImageEnhance.Contrast(im).enhance(enhance[1])
        im = ImageEnhance.Color(im).enhance(enhance[2])
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=88)
    return base64.b64encode(buf.getvalue()).decode(), im.size


def _heat(t):
    """blue (low) -> purple -> red (high). Only high-agreement cells are drawn, so they read red/orange."""
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    stops = [(0, (37, 99, 235)), (0.5, (150, 60, 190)), (1, (226, 26, 12))]
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            f = (t - t0) / (t1 - t0) if t1 > t0 else 0
            return "#%02x%02x%02x" % tuple(int(a + (b - a) * f) for a, b in zip(c0, c1))
    return "#e21a0c"


def _cell_size(grid, bbox, W, H):
    w, s, e, n = bbox
    lons = sorted({round(c["lon"], 6) for c in grid}); lats = sorted({round(c["lat"], 6) for c in grid})
    dl = min((b - a for a, b in zip(lons, lons[1:])), default=(e - w) / 12)
    da = min((b - a for a, b in zip(lats, lats[1:])), default=(n - s) / 12)
    return dl / (e - w) * W, da / (n - s) * H


def _overlap_squares(grid, bbox, W, H, T=0.5):
    """Only cells where BOTH the RF (satellite) model AND the stay-green phenology score above T of their
    own max — the agreement of two independent transfer methods. Colour = agreement strength, blue->red."""
    w, s, e, n = bbox
    rfmax = max((c.get("rf_prob") or 0) for c in grid) or 1e-6
    pemax = max((c.get("persist") or 0) for c in grid) or 1e-6
    cw, ch = _cell_size(grid, bbox, W, H)
    rects = []
    for c in grid:
        lon, lat = c["lon"], c["lat"]
        if not (w <= lon <= e and s <= lat <= n):
            continue
        rf = (c.get("rf_prob") or 0) / rfmax; pe = (c.get("persist") or 0) / pemax
        if rf < T or pe < T:
            continue
        t = min(rf, pe); col = _heat((t - T) / (1 - T))
        x = (lon - w) / (e - w) * W - cw / 2; y = (n - lat) / (n - s) * H - ch / 2
        rects.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{cw:.0f}" height="{ch:.0f}" rx="3" '
                     f'fill="{col}" fill-opacity="0.28" stroke="{col}" stroke-width="{2+2*t:.1f}"/>')
    return "".join(rects), len(rects)


def _driver_squares(grid, bbox, W, H, thr=0.225):
    """Canopy-gap driver: cells with low dry-season greenness (open / disturbed canopy) — the conditions
    the literature ties to Lantana establishment. Amber hollow squares, distinct from the red prediction."""
    w, s, e, n = bbox
    cw, ch = _cell_size(grid, bbox, W, H)
    rects = []
    for c in grid:
        lon, lat, nd = c["lon"], c["lat"], c.get("ndvi_dry")
        if nd is None or not (w <= lon <= e and s <= lat <= n) or nd > thr:
            continue
        x = (lon - w) / (e - w) * W - cw / 2; y = (n - lat) / (n - s) * H - ch / 2
        rects.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{cw:.0f}" height="{ch:.0f}" rx="3" '
                     f'fill="#f5b301" fill-opacity="0.14" stroke="#f5b301" stroke-width="2.4"/>')
    return "".join(rects), len(rects)


def _pond_svg(bbox, W, H):
    w, s, e, n = bbox
    out = []
    with open(os.path.join(GT, "ebtl_pond_points.csv")) as f:
        for r in csv.DictReader(f):
            lat, lon = float(r["lat"]), float(r["lon"])
            if w <= lon <= e and s <= lat <= n:
                out.append(f'<circle cx="{(lon-w)/(e-w)*W:.0f}" cy="{(n-lat)/(n-s)*H:.0f}" r="16" '
                           f'fill="#22d3ee" fill-opacity="0.20"/>')
    return "".join(out), len(out)


def _records_svg(bbox, W, H):
    """The ACTUAL Lantana occurrence points on the wide base, with the site + distance rings."""
    w, s, e, n = bbox
    def X(lon): return (lon - w) / (e - w) * W
    def Y(lat): return (n - lat) / (n - s) * H
    cx, cy = X(SITE_C[0]), Y(SITE_C[1])
    kx = 1 / (111.32 * math.cos(math.radians(SITE_C[1]))) / (e - w) * W   # px per km, lon
    ky = 1 / 110.57 / (n - s) * H                                         # px per km, lat
    svg = [f'<rect x="{X(SITE[0]):.0f}" y="{Y(SITE[3]):.0f}" width="{X(SITE[2])-X(SITE[0]):.0f}" '
           f'height="{Y(SITE[1])-Y(SITE[3]):.0f}" fill="none" stroke="#fff" stroke-width="3"/>']
    for km in (5, 10, 15):
        svg.append(f'<ellipse cx="{cx:.0f}" cy="{cy:.0f}" rx="{km*kx:.0f}" ry="{km*ky:.0f}" fill="none" '
                   f'stroke="#ffffff" stroke-opacity="0.35" stroke-dasharray="6 7" stroke-width="1.6"/>'
                   f'<text x="{cx:.0f}" y="{cy-km*ky-4:.0f}" fill="#fff" fill-opacity="0.6" font-size="15" '
                   f'text-anchor="middle">{km} km</text>')
    svg.append(f'<text x="{cx:.0f}" y="{cy-6:.0f}" fill="#fff" font-size="18" font-weight="700" '
               f'text-anchor="middle" style="paint-order:stroke;stroke:#000a;stroke-width:4">EBTL</text>')
    n_pts = 0
    with open(os.path.join(GT, "lantana_points.csv")) as f:
        for r in csv.DictReader(f):
            lat, lon = float(r["lat"]), float(r["lon"])
            if not (w <= lon <= e and s <= lat <= n):
                continue
            svg.append(f'<circle cx="{X(lon):.0f}" cy="{Y(lat):.0f}" r="9" fill="#ff7b00" '
                       f'stroke="#fff" stroke-width="2"/>')
            n_pts += 1
    return "".join(svg), n_pts


def build():
    reg = json.load(open(os.path.join(GT, "region_markers.json")))
    w, s, e, n = reg["region"]
    s2, (SW, SH) = _b64(os.path.join(GT, "region_base.jpg"), enhance=(1.35, 1.15, 1.35))
    mx, (MW, MH) = _b64(os.path.join(GT, "ebtl_base.jpg"))
    dn, (DW, DH) = _b64(os.path.join(GT, "donor_base.jpg"), enhance=(1.3, 1.12, 1.3), maxpx=1500)
    grid = json.load(open(os.path.join(GT, "lantana_data.json"))).get("grid", [])
    squares, nsq = _overlap_squares(grid, CROP, MW, MH)
    gaps, ngap = _driver_squares(grid, CROP, MW, MH)
    ponds, npond = _pond_svg(CROP, MW, MH)
    records, nrec = _records_svg(DONOR, DW, DH)
    ramp = "".join(f'<i style="background:{_heat(k/24)}"></i>' for k in range(25))

    def SX(lon): return (lon - w) / (e - w) * SW
    def SY(lat): return (n - lat) / (n - s) * SH

    lant = reg.get("lantana", [])
    lc_lat = sum(c["lat"] for c in lant) / len(lant) if lant else 12.734
    lc_lon = sum(c["lon"] for c in lant) / len(lant) if lant else 78.183
    eles = reg.get("elephants", []) or [{"lat": 12.735, "lon": 78.14}]
    el_lat, el_lon = eles[0]["lat"], eles[0]["lon"]
    wl_lat, wl_lon = 12.7335, 78.1835

    def bigmark(lat, lon, col, tag, label):
        x, y = SX(lon), SY(lat)
        return (f'<g class="hot" onclick="zoomEnter(\'{tag}\')">'
                f'<circle cx="{x:.0f}" cy="{y:.0f}" r="30" fill="{col}" fill-opacity="0.16" stroke="{col}" '
                f'stroke-width="3"><animate attributeName="r" values="30;36;30" dur="2.4s" '
                f'repeatCount="indefinite"/></circle><circle cx="{x:.0f}" cy="{y:.0f}" r="6" fill="{col}"/>'
                f'<text x="{x:.0f}" y="{y-38:.0f}" fill="#fff" font-size="15" font-weight="700" '
                f'text-anchor="middle" style="paint-order:stroke;stroke:#000a;stroke-width:4">{label}</text></g>')
    site_rect = (
        f'<rect x="{SX(SITE[0]):.0f}" y="{SY(SITE[3]):.0f}" width="{SX(SITE[2])-SX(SITE[0]):.0f}" '
        f'height="{SY(SITE[1])-SY(SITE[3]):.0f}" fill="none" stroke="#fff" stroke-width="3" '
        f'stroke-dasharray="9 6"/><text x="{SX(SITE[0])+6:.0f}" y="{SY(SITE[3])+22:.0f}" fill="#fff" '
        f'font-size="17" font-weight="700">EBTL</text>')
    ovmarks = site_rect + bigmark(lc_lat, lc_lon, "#ff7b00", "lantana", "Lantana") \
        + bigmark(el_lat, el_lon, "#c77dff", "elephant", "Elephants") \
        + bigmark(wl_lat, wl_lon, "#22d3ee", "water", "Water")
    probs = json.dumps([
        {"id": "lantana", "fx": (lc_lon - w) / (e - w), "fy": (n - lc_lat) / (n - s)},
        {"id": "elephant", "fx": (el_lon - w) / (e - w), "fy": (n - el_lat) / (n - s)},
        {"id": "water", "fx": (wl_lon - w) / (e - w), "fy": (n - wl_lat) / (n - s)},
    ])

    def doi(t, d):
        return f'<a href="https://doi.org/{d}" target="_blank">{t}</a>'

    def side(desc, qs, method, drivers, papers, honest, need):
        ql = "".join(f"<li>{q}</li>" for q in qs)
        dl = f'<div class="wl"><b>Drivers (literature):</b> {drivers}</div>' if drivers else ""
        pl = f'<div class="wl"><b>Papers consulted:</b> {papers}</div>' if papers else ""
        return (f'<div class="desc">{desc}</div>'
                f'<div class="qbox"><div class="qh">Questions that surfaced this</div><ul>{ql}</ul></div>'
                f'<div class="why"><div class="wh">▸ where this comes from</div>'
                f'<div class="wl"><b>Method:</b> {method}</div>{dl}{pl}'
                f'<div class="wl"><b>Honest limit:</b> {honest}</div>'
                f'<div class="need"><b>Data we need:</b> {need}</div></div>')

    lant_side = side(
        "<b>Lantana camara</b> is a fast-spreading evergreen shrub that forms dense thickets, shades out "
        "native seedlings and stalls dry-deciduous restoration. It exploits canopy gaps and disturbed edges. "
        "We have <b>no confirmed records on the EBTL site yet</b> — this map estimates where it is most "
        "likely so the team can walk and confirm.",
        ["is lantana taking over our forest?", "what always grows near lantana?",
         "show me where the lantana is on our land", "is prosopis or parthenium spreading near us?"],
        "RandomForest on Sentinel-2 indices + a multi-year <b>dry-season stay-green</b> signal — evergreen "
        "invaders stay green when native deciduous trees drop their leaves. <i>This is vegetation phenology, "
        "NOT wildfire.</i> The <b>Prediction</b> layer shows only cells where BOTH methods score high.",
        "canopy openness / gaps, disturbed edges &amp; roads, and habitat fragmentation. The <b>Drivers</b> "
        "layer highlights open-canopy (low dry-season greenness) cells — where Lantana tends to establish.",
        doi("Osuri et al. — tree &amp; habitat structure, Western Ghats fragments", "10.5281/zenodo.10077040")
        + "; " + doi("roadkill / edge-disturbance seasonality", "10.5281/zenodo.7060430")
        + "; " + doi("rainforest-fragment plant community structure", "10.5281/zenodo.7457732")
        + " <span class='cav'>(Western Ghats wet-forest studies — a transfer caveat for our dry site)</span>",
        "invasive-LIKELIHOOD, not a confirmed ID — evergreen natives can false-trigger. The nearest actual "
        "records (see the <b>Records</b> layer) are &gt;13&nbsp;km away.",
        "walk the red cells + GPS a few Lantana / not-Lantana patches → we retrain into a calibrated map.")

    ele_side = side(
        "Elephants move through this landscape between forest patches; where they cross farmland they raise "
        "conflict risk. Knowing their routes and forage lets the team plan planting and avoid conflict. "
        "Records here are <b>sparse and opportunistic</b>.",
        ["what do the elephants here eat?", "where do elephants move through our area?",
         "are elephants likely to raid crops near the village?", "where do elephants and people overlap most?"],
        "direct opportunistic occurrence records (iNaturalist) — no model / transfer.",
        None, None,
        "opportunistic sightings (people report where people are), not systematic movement.",
        "camera traps (3 months) + dung transects → real movement + usage, not just where someone stood.")

    wat_side = side(
        "The site's ponds are the dry-season lifeline for wildlife and young saplings. Several hold water only "
        "briefly after the monsoon. Knowing which dry first tells the team which to deepen or shade — "
        "<b>6 of 11 waterbodies are ephemeral (~1 month/yr)</b>; the NE pond is most precarious.",
        ["which of our ponds dries up first?", "how much water is in our ponds through the year?"],
        "JRC Global Surface Water (38-yr, 30&nbsp;m) seasonality/occurrence + Sentinel-2 detected water "
        f"pixels ({npond} highlighted here) — no transfer.",
        None, None,
        "30&nbsp;m misses sub-30&nbsp;m check-dams; a 38-yr average, not this year's rain.",
        "your ponds' GPS + depth → exact per-pond persistence, which to deepen / shade.")

    CSS = """
*{box-sizing:border-box}
html,body{margin:0;height:100%;background:#0b0d12;color:#c9d1d9;font:13px/1.5 system-ui,-apple-system,sans-serif;overflow:hidden}
header{padding:9px 16px;background:#12151c;border-bottom:1px solid #262b36;display:flex;align-items:baseline;gap:12px;position:relative;z-index:5}
.brand{font-weight:800;font-size:16px;color:#e6edf3;letter-spacing:.3px}.brand span{color:#ff7b00}
.tag{color:#8b949e;font-size:12px}
#app{position:relative;height:calc(100vh - 46px);height:calc(100dvh - 46px)}
.view{position:absolute;inset:0;display:flex;opacity:0;visibility:hidden;transition:opacity .4s}
.view.on{opacity:1;visibility:visible}
.panel{width:322px;min-width:300px;background:#0e1117;border-right:1px solid #262b36;overflow:auto;padding:12px 14px;z-index:2}
.panel h3{margin:2px 0 8px;font-size:13px;color:#8b949e;text-transform:uppercase;letter-spacing:.5px}
.card{background:#161b22;border:1px solid #262b36;border-radius:8px;padding:11px 13px;margin-bottom:10px;cursor:pointer;transition:border-color .15s}
.card:active{border-color:#ff7b0088}.card b{color:#e6edf3}.card .m{color:#8b949e;font-size:12px;margin-top:3px}
.card .pill{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px}
.mapwrap{flex:1;position:relative;overflow:hidden;background:#000;touch-action:none}
.zoom{position:absolute;top:0;left:0;width:100%;height:100%;transform-origin:0 0}
.zoom img{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;display:block}
.zoom svg{position:absolute;inset:0;width:100%;height:100%}
.zoom svg *{pointer-events:auto}
.hot{cursor:zoom-in}
.hint{position:absolute;left:10px;bottom:9px;background:#000a;color:#c9d1d9;font-size:11px;padding:4px 9px;border-radius:5px;z-index:3;pointer-events:none}
.detail{flex:1;display:flex;flex-direction:column;min-width:0}
.dhead{padding:7px 14px;background:#12151c;border-bottom:1px solid #262b36;display:flex;align-items:center;gap:12px;flex-wrap:wrap;z-index:3}
.back{cursor:pointer;color:#58a6ff;font-weight:600;white-space:nowrap}.dttl{font-weight:700;color:#e6edf3;font-size:13px}
.tabs{display:flex;gap:6px;margin-left:auto}
.tabs button{background:#161b22;color:#8b949e;border:1px solid #30363d;border-radius:6px;padding:6px 12px;font:inherit;font-weight:600;cursor:pointer}
.tabs button.on{color:#0b0d12;background:#ff7b00;border-color:#ff7b00}
.dbody{flex:1;display:flex;min-height:0}
.mapstack{flex:1;position:relative;min-width:0;display:flex}
.stage{position:absolute;inset:0;display:none}.stage.on{display:flex}
.side{width:342px;min-width:322px;background:#0e1117;border-left:1px solid #262b36;overflow:auto;padding:14px;z-index:2}
.legend{display:flex;align-items:center;gap:8px;font-size:11px;color:#8b949e;margin-bottom:12px;flex-wrap:wrap}
.ramp{display:flex;height:11px;width:120px;border-radius:3px;overflow:hidden}.ramp i{flex:1}
.desc{font-size:12.5px;line-height:1.55;margin-bottom:12px;color:#c9d1d9}.desc b{color:#e6edf3}
.qbox{background:#161b22;border:1px solid #262b36;border-radius:8px;padding:10px 12px;margin-bottom:12px}
.qbox .qh{color:#8b949e;font-size:11px;text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px}
.qbox ul{margin:0;padding-left:17px}.qbox li{margin:2px 0;font-style:italic;color:#adbac7}
.why{background:#12261a;border:1px solid #1f6f3f55;border-radius:8px;padding:11px 13px;font-size:12.5px}
.why .wh{color:#7ee787;font-weight:700;margin-bottom:6px}.why .wl{margin:5px 0}.why b{color:#e6edf3}
.why a{color:#58a6ff}.cav{color:#8b949e;font-style:italic}
.need{margin-top:8px;padding-top:8px;border-top:1px solid #1f6f3f33;color:#ffb454}
@media (max-width:760px){
  header{flex-direction:column;gap:2px;padding:8px 14px}.tag{font-size:11px}
  .view{flex-direction:column}
  .panel{width:100%;min-width:0;max-height:42%;border-right:none;border-top:1px solid #262b36;order:2}
  #overview .mapwrap{order:1;min-height:56%}
  .dbody{flex-direction:column}
  .mapstack{min-height:0;flex:1 1 54%}
  .side{width:100%;min-width:0;flex:1 1 46%;border-left:none;border-top:1px solid #262b36}
  .dttl{font-size:12px}.tabs{margin-left:0;width:100%}.tabs button{flex:1;padding:8px 6px}
}
"""

    def stage(wid, zid, iid, vb, par, overlay, on=False):
        return (f'<div class="stage{" on" if on else ""}" id="st_{wid}">'
                f'<div class="mapwrap" id="{wid}"><div class="zoom" id="{zid}"><img id="{iid}">'
                f'<svg viewBox="{vb}" preserveAspectRatio="{par}">{overlay}</svg></div>'
                f'<div class="hint">scroll / pinch to zoom · drag to pan</div></div></div>')

    OVB, MVB = f"0 0 {SW} {SH}", f"0 0 {MW} {MH}"
    DVB = f"0 0 {DW} {DH}"
    lan_stack = (stage("lanwrap_p", "lanzoom_p", "img_lanp", MVB, "xMidYMid meet", squares, on=True)
                 + stage("lanwrap_d", "lanzoom_d", "img_land", MVB, "xMidYMid meet", gaps)
                 + stage("lanwrap_r", "lanzoom_r", "img_lanr", DVB, "xMidYMid meet", records))
    ele_overlay = (site_rect + f'<circle cx="{SX(el_lon):.0f}" cy="{SY(el_lat):.0f}" r="13" fill="none" '
                   f'stroke="#c77dff" stroke-width="3"/><circle cx="{SX(el_lon):.0f}" cy="{SY(el_lat):.0f}" '
                   f'r="4" fill="#c77dff"/>')

    BODY = f"""<header><div class="brand">EBTL <span>·</span> Decision Support</div>
<div class="tag">Elephants by the Lake — restoration DSS · zoom a marker to dive into the 35&nbsp;cm map</div></header>
<div id="app">

  <div id="overview" class="view on">
    <div class="panel"><h3>Issues that need data</h3>
      <div class="card" onclick="zoomEnter('lantana')"><b><span class="pill" style="background:#ff7b00"></span>Lantana (invasive)</b>
        <div class="m">Where two satellite methods agree it's likely — no records on the site yet.</div></div>
      <div class="card" onclick="zoomEnter('elephant')"><b><span class="pill" style="background:#c77dff"></span>Elephants</b>
        <div class="m">Sparse records near the site; the dense corridor is further west.</div></div>
      <div class="card" onclick="zoomEnter('water')"><b><span class="pill" style="background:#22d3ee"></span>Water / ponds</b>
        <div class="m">6 of 11 waterbodies are ephemeral (~1 month/yr).</div></div>
      <div style="color:#6e7681;font-size:11px;margin-top:8px">Everything here is a model estimate or opportunistic
      record — the map decides where to go collect the data that confirms it.</div>
    </div>
    <div class="mapwrap" id="ovwrap"><div class="zoom" id="ovzoom"><img id="img_ov">
      <svg viewBox="{OVB}" preserveAspectRatio="xMidYMid meet">{ovmarks}</svg></div>
      <div class="hint">scroll / pinch to zoom · tap a marker</div></div>
  </div>

  <div id="lantana" class="view"><div class="detail">
    <div class="dhead"><span class="back" onclick="reset()">← issues</span>
      <span class="dttl">Lantana (invasive)</span>
      <div class="tabs"><button class="on" data-l="p" onclick="setL('p')">Prediction</button>
        <button data-l="d" onclick="setL('d')">Drivers</button>
        <button data-l="r" onclick="setL('r')">Records</button></div></div>
    <div class="dbody">
      <div class="mapstack" id="lanstack">{lan_stack}</div>
      <div class="side">
        <div class="legend" id="lanleg">low<div class="ramp">{ramp}</div>high · {nsq} agreeing cells</div>
        {lant_side}
      </div>
    </div>
  </div></div>

  <div id="water" class="view"><div class="detail">
    <div class="dhead"><span class="back" onclick="reset()">← issues</span>
      <span class="dttl">Water — pond areas (35&nbsp;cm Maxar)</span></div>
    <div class="dbody"><div class="mapstack">
      {stage("watwrap", "watzoom", "img_wat", MVB, "xMidYMid meet", ponds, on=True)}</div>
      <div class="side"><div class="legend"><span style="width:12px;height:12px;border-radius:50%;background:#22d3ee;display:inline-block"></span>
        detected water</div>{wat_side}</div>
    </div>
  </div></div>

  <div id="elephant" class="view"><div class="detail">
    <div class="dhead"><span class="back" onclick="reset()">← issues</span>
      <span class="dttl">Elephants — records near the site</span></div>
    <div class="dbody"><div class="mapstack">
      {stage("elewrap", "elezoom", "img_ele", OVB, "xMidYMid meet", ele_overlay, on=True)}</div>
      <div class="side">{ele_side}</div>
    </div>
  </div></div>

</div>"""

    IMGJS = (f'var S2="data:image/jpeg;base64,{s2}",MX="data:image/jpeg;base64,{mx}",'
             f'DN="data:image/jpeg;base64,{dn}";'
             'var A={img_ov:S2,img_ele:S2,img_lanp:MX,img_land:MX,img_wat:MX,img_lanr:DN};'
             'for(var k in A){document.getElementById(k).src=A[k];}')

    JS = IMGJS + """
var probs = __PROBS__, OVAR = __OVAR__;
function apply(z){z.el.style.transform='translate('+z.tx+'px,'+z.ty+'px) scale('+z.sc+')';}
function clampReset(z){if(z.sc<=1.001){z.sc=1;z.tx=0;z.ty=0;}}
function dispBox(r,ar){var wa=r.width/r.height;
  if(wa>ar){var h=r.height,w=h*ar;return{w:w,h:h,ox:(r.width-w)/2,oy:0};}
  var w=r.width,h=w/ar;return{w:w,h:h,ox:0,oy:(r.height-h)/2};}
function dist(t){return Math.hypot(t[0].clientX-t[1].clientX,t[0].clientY-t[1].clientY);}
function enter(id){document.querySelectorAll('.view').forEach(function(v){v.classList.remove('on');});document.getElementById(id).classList.add('on');
  if(location.hash.slice(1)!==(id==='overview'?'':id))location.hash=id==='overview'?'':id;}
function reset(){enter('overview');ov.sc=1;ov.tx=0;ov.ty=0;ov.el.style.transition='';apply(ov);}
function setL(l){['p','d','r'].forEach(function(x){
  document.getElementById('st_lanwrap_'+x).classList.toggle('on',x===l);
  document.querySelector('.tabs [data-l="'+x+'"]').classList.toggle('on',x===l);});
  var leg=document.getElementById('lanleg');
  leg.innerHTML = l==='p' ? 'low<div class="ramp">__RAMP__</div>high · __NSQ__ agreeing cells'
    : l==='d' ? '<span style="width:12px;height:12px;background:#f5b301;display:inline-block;border-radius:2px"></span> canopy gaps (a driver) · __NGAP__ cells'
    : '<span style="width:11px;height:11px;background:#ff7b00;border-radius:50%;display:inline-block;border:2px solid #fff"></span> actual records · __NREC__ points, nearest &gt;13&nbsp;km';}
function initZoom(wrapId, zoomId, onTrigger){
  var wrap=document.getElementById(wrapId), el=document.getElementById(zoomId), z={el:el,sc:1,tx:0,ty:0};
  function zoomAt(cx,cy,f){var ns=Math.min(9,Math.max(1,z.sc*f));
    z.tx=cx-(cx-z.tx)*(ns/z.sc);z.ty=cy-(cy-z.ty)*(ns/z.sc);z.sc=ns;clampReset(z);apply(z);}
  function trig(cx,cy,r){if(!onTrigger||z.sc<2.4)return;
    var b=dispBox(r,OVAR),fx=((cx-z.tx)/z.sc-b.ox)/b.w,fy=((cy-z.ty)/z.sc-b.oy)/b.h,best=null,bd=9;
    probs.forEach(function(p){var d=Math.hypot(p.fx-fx,p.fy-fy);if(d<bd){bd=d;best=p;}});
    z.sc=1;z.tx=0;z.ty=0;apply(z);if(best)enter(best.id);}
  wrap.addEventListener('wheel',function(e){e.preventDefault();var r=wrap.getBoundingClientRect();
    var cx=e.clientX-r.left,cy=e.clientY-r.top;zoomAt(cx,cy,e.deltaY<0?1.2:1/1.2);trig(cx,cy,r);},{passive:false});
  var md=false,mx=0,my=0;
  wrap.addEventListener('mousedown',function(e){if(z.sc<=1)return;md=true;mx=e.clientX;my=e.clientY;});
  window.addEventListener('mouseup',function(){md=false;});
  window.addEventListener('mousemove',function(e){if(!md)return;z.tx+=e.clientX-mx;z.ty+=e.clientY-my;mx=e.clientX;my=e.clientY;apply(z);});
  var tm=0,tx0=0,ty0=0,d0=0,s0=1;
  wrap.addEventListener('touchstart',function(e){var r=wrap.getBoundingClientRect();
    if(e.touches.length===1){tm=1;tx0=e.touches[0].clientX;ty0=e.touches[0].clientY;}
    else if(e.touches.length>=2){tm=2;d0=dist(e.touches);s0=z.sc;}},{passive:false});
  wrap.addEventListener('touchmove',function(e){var r=wrap.getBoundingClientRect();
    if(tm===1&&z.sc>1){e.preventDefault();z.tx+=e.touches[0].clientX-tx0;z.ty+=e.touches[0].clientY-ty0;
      tx0=e.touches[0].clientX;ty0=e.touches[0].clientY;apply(z);}
    else if(tm===2&&e.touches.length>=2){e.preventDefault();var d=dist(e.touches),ns=Math.min(9,Math.max(1,s0*d/d0));
      var cx=(e.touches[0].clientX+e.touches[1].clientX)/2-r.left,cy=(e.touches[0].clientY+e.touches[1].clientY)/2-r.top;
      z.tx=cx-(cx-z.tx)*(ns/z.sc);z.ty=cy-(cy-z.ty)*(ns/z.sc);z.sc=ns;clampReset(z);apply(z);trig(cx,cy,r);}},{passive:false});
  wrap.addEventListener('touchend',function(e){if(e.touches.length===0)tm=0;
    else if(e.touches.length===1){tm=1;tx0=e.touches[0].clientX;ty0=e.touches[0].clientY;}},{passive:false});
  return z;
}
function zoomEnter(id){
  var p=probs.filter(function(x){return x.id===id;})[0];if(!p){enter(id);return;}
  var wrap=document.getElementById('ovwrap'),r=wrap.getBoundingClientRect(),ts=3.4;
  var b=dispBox(r,OVAR),mx=b.ox+p.fx*b.w,my=b.oy+p.fy*b.h;
  ov.sc=ts;ov.tx=r.width/2-mx*ts;ov.ty=r.height/2-my*ts;ov.el.style.transition='transform .5s ease';apply(ov);
  setTimeout(function(){enter(id);ov.el.style.transition='';ov.sc=1;ov.tx=0;ov.ty=0;apply(ov);},470);
}
var ov=initZoom('ovwrap','ovzoom',true);
['lanwrap_p','lanwrap_d','lanwrap_r','watwrap','elewrap'].forEach(function(w){initZoom(w,w.replace('wrap','zoom').replace('lanwrap','lanzoom'),null);});
(function(){var h=location.hash.slice(1);if(h&&h!=='overview'&&document.getElementById(h))enter(h);})();
""".replace("__PROBS__", probs).replace("__OVAR__", f"{SW/SH:.6f}") \
    .replace("__RAMP__", ramp).replace("__NSQ__", str(nsq)).replace("__NGAP__", str(ngap)) \
    .replace("__NREC__", str(nrec))

    head = ('<!doctype html><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">'
            '<title>EBTL · Decision Support</title>')
    doc = head + "<style>" + CSS + "</style>" + BODY + "<script>" + JS + "</script>"
    out = os.path.join(GT, "index.html")
    open(out, "w").write(doc)
    print(f"wrote {out}  ({len(doc)//1024} KB) · lantana: {nsq} agree / {ngap} gaps / {nrec} records · {npond} ponds")
    return out


if __name__ == "__main__":
    build()
