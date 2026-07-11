#!/usr/bin/env python3
"""Free, field-navigable invasive map for EBTL — the cost-aware funnel + a trained classifier, $0 data.

THE FUNNEL, from several directions (no paid imagery required):
  1. PHENOLOGY (Sentinel-2, free, multi-year): native dry-deciduous forest goes bare in the dry season;
     Lantana & evergreen invaders STAY GREEN. Persistence across years = a robust candidate signal.
  2. A TRAINED CLASSIFIER (Earth Engine RandomForest, free): trained on RECENT known Lantana records
     (positives) vs random background (pseudo-absence) over a multi-index S2 feature stack
     (wet/dry NDVI, seasonal delta, red-edge NDRE, moisture NDWI, dry-season SWIR) → per-cell probability.
  3. SIMILARITY (AlphaEarth) + VALIDATION (GBIF) as supporting layers.
  likelihood = 0.6·RF_probability + 0.4·phenology_persistence.
Output: a field-navigable HTML map + a GPS waypoint list (CSV + GeoJSON) of the top candidate cells so
you can walk to them. Honest: this is invasive-LIKELIHOOD (transfer from corridor records), confirm on
the ground or with one SkyFi high-res scene over just the top cells (skyfi.py).

  build [--species "Lantana camara"] : EE work -> runs/invasive_map_data.json  (run in the hermes container)
  render                             : pure-python -> runs/invasive_map.html + invasive_waypoints.{csv,geojson}
"""
import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))    # this file lives IN the connectors dir
CONN = HERE
S2C = "COPERNICUS/S2_SR_HARMONIZED"
# output paths are per-species and go to the first WRITABLE dir (container: /opt/data/work; else repo runs)
DATA = HTML = WPTS_CSV = WPTS_GEO = None


def _out():
    for d in (os.environ.get("INVASIVE_OUT"), "/opt/data/work/invasive",
              os.path.abspath(os.path.join(HERE, "..", "runs"))):
        if not d:
            continue
        try:
            os.makedirs(d, exist_ok=True)
        except Exception:
            continue
        if os.access(d, os.W_OK):
            return d
    return os.getcwd()


def _set_paths(species):
    global DATA, HTML, WPTS_CSV, WPTS_GEO
    slug = species.lower().replace(" ", "_").replace("/", "_")
    base = os.path.join(_out(), slug)
    os.makedirs(base, exist_ok=True)
    DATA = os.path.join(base, "data.json")
    HTML = os.path.join(base, "map.html")
    WPTS_CSV = os.path.join(base, "waypoints.csv")
    WPTS_GEO = os.path.join(base, "waypoints.geojson")
    return base


def _clip(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


# ---------------- EE feature stack + classifier (build) ----------------
def _feature_image(ee, s2, year, geom):
    """Multi-index dry/wet Sentinel-2 stack — the features the RF learns Lantana's signature from."""
    def med(window):
        s_md, e_md = window
        start = f"{year - 1 if s_md.startswith('-12') else year}{s_md}"
        col = (ee.ImageCollection(S2C).filterDate(start, f"{year}{e_md}").filterBounds(geom)
               .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 40)).map(s2._mask))
        return col.median()
    wet, dry = med(s2.WET), med(s2.DRY)
    nd = lambda i, a, b: i.normalizedDifference([a, b])
    ndvi_wet, ndvi_dry = nd(wet, "B8", "B4"), nd(dry, "B8", "B4")
    return (ndvi_wet.rename("ndvi_wet")
            .addBands(ndvi_dry.rename("ndvi_dry"))
            .addBands(ndvi_dry.subtract(ndvi_wet).rename("ndvi_delta"))     # deciduous drop (native) vs retain (invader)
            .addBands(nd(dry, "B8", "B5").rename("ndre_dry"))               # red-edge chlorophyll (evergreen canopy)
            .addBands(nd(dry, "B3", "B8").rename("ndwi_dry"))               # moisture
            .addBands(dry.select("B11").divide(10000).rename("swir_dry")))  # dry-season SWIR brightness


FEATS = ["ndvi_wet", "ndvi_dry", "ndvi_delta", "ndre_dry", "ndwi_dry", "swir_dry"]


def build(species="Lantana camara", year=2024, n=28):
    sys.path.insert(0, CONN)
    import s2, occurrence, embedding                       # noqa: E402
    from _base import init_ee                               # noqa: E402
    ee = init_ee("plantwars")
    site = json.load(open(os.path.join(CONN, "SITE_EBTL.json")))
    bbox, ctr = site["site_bbox_wsen"], site["site_center_latlon"]
    _set_paths(species)

    # --- recent known presence (ground truth); widen search for less-recorded invasives ---
    def pull(box, minyear):
        return [p for p in occurrence.search(species, bbox=box, limit=300)
                if p.get("lat") and p.get("lon") and (p.get("year") or 0) >= minyear]
    cbox = [77.8, 12.37, 78.55, 13.1]
    pres = pull(cbox, 2018)
    train_box = cbox
    if len(pres) < 8:                          # sparse: widen the analog belt + relax recency
        wbox = [76.0, 11.0, 79.5, 13.8]
        wider = pull(wbox, 2010)
        if len(wider) > len(pres):
            pres, train_box = wider, wbox
    ref = min(pres, key=lambda p: (p["lat"] - ctr["lat"])**2 + (p["lon"] - ctr["lon"])**2) if pres else None
    ref_ll = [ref["lat"], ref["lon"]] if ref else [ctr["lat"], ctr["lon"]]
    use_rf = len(pres) >= 3                     # need enough positives for a 2-class probability RF

    # --- train an EE RandomForest (presence=1 vs random background=0) on the S2 feature stack ---
    w, s, e, nth = bbox
    grid_rows = [{"lat": s + (nth - s) * (r + 0.5) / n, "lon": w + (e - w) * (c + 0.5) / n}
                 for r in range(n) for c in range(n)]
    site_geom = ee.Geometry.Rectangle(bbox)
    feat_site = _feature_image(ee, s2, year, site_geom)
    fc = ee.FeatureCollection([ee.Feature(ee.Geometry.Point([r["lon"], r["lat"]]), {"_i": i})
                               for i, r in enumerate(grid_rows)])
    stack = feat_site
    if use_rf:
        train_geom = ee.Geometry.Rectangle(train_box)
        feat_corr = _feature_image(ee, s2, year, train_geom)
        pos = ee.FeatureCollection([ee.Feature(ee.Geometry.Point([p["lon"], p["lat"]]), {"cls": 1}) for p in pres])
        bg = ee.FeatureCollection.randomPoints(train_geom, 120, 42).map(lambda f: f.set("cls", 0))
        training = feat_corr.select(FEATS).sampleRegions(
            collection=pos.merge(bg), properties=["cls"], scale=10, tileScale=2).filter(
            ee.Filter.notNull(FEATS))
        clf = (ee.Classifier.smileRandomForest(80).setOutputMode("PROBABILITY")
               .train(training, "cls", FEATS))
        stack = feat_site.addBands(feat_site.select(FEATS).classify(clf).rename("rf_prob"))
    samp = stack.reduceRegions(collection=fc, reducer=ee.Reducer.mean(), scale=10).getInfo()["features"]
    by = {int(f["properties"]["_i"]): f["properties"] for f in samp}
    # phenology persistence: also compute the previous year's stay-green and require BOTH
    prev = _feature_image(ee, s2, year - 1, site_geom)
    prev_samp = prev.select(["ndvi_dry", "ndvi_wet"]).reduceRegions(
        collection=fc, reducer=ee.Reducer.mean(), scale=10).getInfo()["features"]
    prevby = {int(f["properties"]["_i"]): f["properties"] for f in prev_samp}

    grid = []
    for i, r in enumerate(grid_rows):
        p, pv = by.get(i, {}), prevby.get(i, {})
        nd_w, nd_d = p.get("ndvi_wet"), p.get("ndvi_dry")
        retain = (nd_d / nd_w) if (nd_w and nd_w > 0.05 and nd_d is not None) else None
        phen = _clip(((retain or 0) - 0.4) / 0.5, 0, 1) if (nd_w or 0) >= 0.30 else 0.0
        # persistence: last year also stayed green
        pv_ret = (pv.get("ndvi_dry") / pv["ndvi_wet"]) if (pv.get("ndvi_wet") and pv["ndvi_wet"] > 0.05) else 0
        persist = phen * (1.0 if pv_ret >= 0.65 else 0.6)
        rf = p.get("rf_prob")
        lik = round(0.6 * (rf or 0) + 0.4 * persist, 3) if rf is not None else round(persist, 3)
        grid.append({**r, "ndvi_wet": _rnd(nd_w), "ndvi_dry": _rnd(nd_d), "retain": _rnd(retain),
                     "rf_prob": _rnd(rf), "persist": round(persist, 3), "likelihood": lik})

    insite = [p for p in pres if bbox[0] <= p["lon"] <= bbox[2] and bbox[1] <= p["lat"] <= bbox[3]]
    liks = [c["likelihood"] for c in grid]
    val = {"n_presence_corridor": len(pres), "n_presence_in_site": len(insite),
           "presence_years": sorted({p.get("year") for p in pres if p.get("year")}),
           "mean_likelihood_all": round(sum(liks) / len(liks), 3),
           "max_likelihood": round(max(liks), 3),
           "n_high": sum(1 for x in liks if x >= 0.5),
           "used_rf": use_rf, "rf_features": FEATS if use_rf else [],
           "rf_train_pos": len(pres) if use_rf else 0, "rf_train_bg": 120 if use_rf else 0}
    method = ("EE RandomForest (recent presence vs background, multi-index S2) + multi-year phenology "
              "persistence; likelihood = 0.6*RF + 0.4*persistence." if use_rf else
              f"PHENOLOGY-ONLY: too few recent {species} records ({len(pres)}) to train a classifier, so "
              "likelihood = multi-year stay-green persistence alone. Provide/collect local records to enable the RF.")
    out = {"species": species, "year": year, "grid_n": n, "bbox": bbox, "center": ctr,
           "ref_presence": ref_ll, "grid": grid,
           "presence_corridor": [{"lat": p["lat"], "lon": p["lon"], "year": p.get("year")} for p in pres],
           "presence_in_site": insite, "validation": val, "windows": {"wet": s2.WET, "dry": s2.DRY},
           "method": method}
    json.dump(out, open(DATA, "w"), indent=1)
    print(f"wrote {DATA}  ({len(grid)} cells, {val['n_high']} high-likelihood, "
          f"{len(pres)} recent presence {val['presence_years']})  max={val['max_likelihood']}")
    return out


def _rnd(x):
    return round(x, 3) if isinstance(x, (int, float)) else None


# ---------------- rendering (pure python, no EE) ----------------
def _viridis(t):
    t = _clip(t, 0, 1)
    stops = [(0.0, (68, 1, 84)), (0.25, (59, 82, 139)), (0.5, (33, 145, 140)),
             (0.75, (94, 201, 98)), (1.0, (253, 231, 37))]
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            f = (t - t0) / (t1 - t0) if t1 > t0 else 0
            return "#%02x%02x%02x" % tuple(round(a + (b - a) * f) for a, b in zip(c0, c1))
    return "#fde725"


def render(species="Lantana camara"):
    _set_paths(species)
    d = json.load(open(DATA))
    w, s, e, nth = d["bbox"]
    grid, n = d["grid"], d["grid_n"]
    mx = max((c["likelihood"] for c in grid), default=1) or 1
    # rank waypoints (dedupe to well-separated top cells so they're findable on the ground)
    ranked = sorted(grid, key=lambda c: -c["likelihood"])
    wpts, used = [], []
    for c in ranked:
        if c["likelihood"] < 0.4:
            break
        if all((c["lat"] - u["lat"])**2 + (c["lon"] - u["lon"])**2 > (0.0016)**2 for u in used):
            wpts.append(c); used.append(c)
        if len(wpts) >= 15:
            break
    _write_waypoints(wpts)

    W = H = 660
    pad = 52

    def X(lon): return pad + (lon - w) / (e - w) * (W - 2 * pad)
    def Y(lat): return H - pad - (lat - s) / (nth - s) * (H - 2 * pad)
    cw = (W - 2 * pad) / n
    rects = []
    for c in grid:
        col = _viridis(c["likelihood"] / mx)
        hi = c["likelihood"] >= 0.5
        rects.append(f'<rect x="{X(c["lon"])-cw/2:.1f}" y="{Y(c["lat"])-cw/2:.1f}" width="{cw:.1f}" '
                     f'height="{cw:.1f}" fill="{col}" fill-opacity="{0.92 if hi else 0.5}">'
                     f'<title>likelihood {c["likelihood"]} · RF {c.get("rf_prob")} · '
                     f'persist {c.get("persist")} · {c["lat"]:.5f},{c["lon"]:.5f}</title></rect>')
    # numbered waypoint markers
    wmark = []
    for i, c in enumerate(wpts, 1):
        x, y = X(c["lon"]), Y(c["lat"])
        wmark.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="10" fill="#ff3b3b" fill-opacity="0.85" '
                     f'stroke="#fff" stroke-width="1.5"/><text x="{x:.1f}" y="{y+3.5:.1f}" '
                     f'text-anchor="middle" font-size="11" fill="#fff" font-weight="700">{i}</text>')
    # corridor presence that fall in view
    pres = "".join(f'<circle cx="{X(p["lon"]):.1f}" cy="{Y(p["lat"]):.1f}" r="4" fill="none" '
                   f'stroke="#7ee787" stroke-width="2"/>' for p in d["presence_in_site"])
    # lat/lon ticks (field navigation)
    ticks = []
    for k in range(5):
        lo = w + (e - w) * k / 4; la = s + (nth - s) * k / 4
        ticks.append(f'<text x="{X(lo):.0f}" y="{H-pad+16}" fill="#8b949e" font-size="10" text-anchor="middle">{lo:.4f}</text>')
        ticks.append(f'<text x="{pad-6}" y="{Y(la)+3:.0f}" fill="#8b949e" font-size="10" text-anchor="end">{la:.4f}</text>')
    leg = "".join(f'<rect x="{pad+i*3}" y="{H-26}" width="3" height="9" fill="{_viridis(i/60)}"/>' for i in range(60))
    # scale bar (~500 m)
    m_per_deg = 111320 * math.cos(math.radians(d["center"]["lat"]))
    px_500 = 500 / m_per_deg / (e - w) * (W - 2 * pad)
    v = d["validation"]
    genus = d["species"].split()[0]
    if v.get("used_rf"):
        train_line = f"trained on {v['rf_train_pos']} recent records {v['presence_years']}"
        card1 = (f'<div class="card"><h3>1 · Trained classifier <span>Earth Engine RF, free</span></h3>'
                 f"A RandomForest trained on <b>{v['rf_train_pos']} recent {genus} records</b> "
                 f"({v['presence_years']}) vs background, over a 6-band Sentinel-2 stack (wet/dry NDVI, "
                 f"seasonal drop, red-edge, moisture, SWIR). Each cell gets a probability — {v['n_high']} "
                 f"cells score ≥ 0.5.</div>")
    else:
        train_line = "phenology-only (too few local records for a classifier)"
        card1 = (f'<div class="card"><h3>1 · Phenology-only <span>too few records</span></h3>'
                 f"Not enough recent {genus} records to train a classifier here, so this map is the "
                 f"multi-year stay-green signal alone. GPS a few {genus} / not-{genus} patches on the "
                 f"ground and we can train the RF for a calibrated map.</div>")

    wrows = "".join(
        f'<tr><td><b>{i}</b></td><td>{c["lat"]:.5f}, {c["lon"]:.5f}</td><td>{c["likelihood"]}</td>'
        f'<td>{c.get("rf_prob")}</td>'
        f'<td><a href="https://www.google.com/maps/search/?api=1&query={c["lat"]:.5f},{c["lon"]:.5f}" '
        f'target="_blank">open ▸</a></td></tr>' for i, c in enumerate(wpts, 1))

    html = f"""<h1>Where is the {d['species']}? — free, field-navigable map</h1>
<p class="sub">Elephants by the Lake (~70 acres · {d['center']['lat']:.4f}N {d['center']['lon']:.4f}E) ·
{d['year']} · {train_line} · <b>no paid imagery</b></p>
<div class="wrap"><svg viewBox="0 0 {W} {H}" width="100%" style="max-width:720px">
<rect x="0" y="0" width="{W}" height="{H}" fill="#0d1117"/>
{''.join(rects)}{pres}{''.join(wmark)}{''.join(ticks)}
<line x1="{W-pad-px_500:.0f}" y1="{pad}" x2="{W-pad:.0f}" y2="{pad}" stroke="#fff" stroke-width="2"/>
<text x="{W-pad-px_500/2:.0f}" y="{pad-6}" fill="#fff" font-size="10" text-anchor="middle">~500 m</text>
<text x="{pad}" y="{pad-6}" fill="#fff" font-size="12">▲ N</text>
{leg}<text x="{pad}" y="{H-30}" fill="#8b949e" font-size="10">low</text>
<text x="{pad+188}" y="{H-30}" fill="#8b949e" font-size="10">higher {d['species'].split()[0]}-likelihood · ● numbered = go here · ○ green = known record</text>
</svg></div>
<div class="cards">
{card1}
<div class="card"><h3>2 · Phenology persistence <span>multi-year S2, free</span></h3>
Natives drop leaves in the dry season; {d['species'].split()[0]} stays green — and a real patch stays
green <i>every</i> year. We require stay-green in {d['year']} <b>and</b> {d['year']-1}.</div>
<div class="card"><h3>3 · Go check these <span>{len(wpts)} waypoints</span></h3>
The numbered pins are the top well-separated candidates. Full GPS list below +
<code>invasive_waypoints.csv/.geojson</code> — load on your phone to walk to them.</div>
</div>
<h2>Field waypoints — highest likelihood first</h2>
<table><tr><th>#</th><th>lat, lon</th><th>likelihood</th><th>RF prob</th><th>map</th></tr>{wrows}</table>
<p class="note"><b>Honest limits:</b> this is invasive-<i>likelihood</i>, not a confirmed species map. The
classifier is <b>transferred</b> from corridor records (few/no {d['species'].split()[0]} points fall
inside the 70-acre box itself), and 10 m pixels blur small clumps. <b>To confirm:</b> walk the numbered
pins (a phone GPS + the CSV), or buy ONE recent high-res SkyFi scene over just the top cells
(<code>skyfi.py best --bbox …</code>, budget-guarded) — the funnel has already narrowed where to spend.
GPS a few Lantana / not-Lantana patches on the ground and we retrain for a calibrated map.</p>"""
    css = """<style>body{margin:0;background:#fff}h1{font:600 20px/1.3 system-ui,sans-serif;margin:18px 20px 2px}
h2{font:600 15px system-ui;margin:18px 20px 6px}.sub{font:13px system-ui;color:#57606a;margin:0 20px 10px}
.wrap{padding:0 20px}.cards{display:flex;gap:12px;flex-wrap:wrap;padding:14px 20px}
.card{flex:1 1 210px;background:#f6f8fa;border:1px solid #d0d7de;border-radius:8px;padding:12px 14px;font:13px/1.5 system-ui;color:#24292f}
.card h3{margin:0 0 6px;font-size:13px}.card span{font-weight:400;color:#57606a;font-size:11px;background:#eaeef2;padding:1px 6px;border-radius:10px;margin-left:6px}
table{border-collapse:collapse;margin:2px 20px;font:13px system-ui}th,td{border:1px solid #d0d7de;padding:4px 10px;text-align:left}
th{background:#f6f8fa}td a{color:#0969da;text-decoration:none}code{background:#eff1f3;padding:1px 5px;border-radius:4px;font-size:12px}
.note{font:12px/1.6 system-ui;color:#57606a;background:#fff8c5;border:1px solid #d4a72c55;margin:12px 20px 24px;padding:12px 14px;border-radius:8px}</style>"""
    os.makedirs(os.path.dirname(HTML), exist_ok=True)
    open(HTML, "w").write(css + html)
    print(f"wrote {HTML}  ({len(wpts)} waypoints -> {WPTS_CSV}, {WPTS_GEO})")


def _write_waypoints(wpts):
    import csv
    with open(WPTS_CSV, "w", newline="") as f:
        wr = csv.writer(f); wr.writerow(["name", "lat", "lon", "likelihood", "rf_prob", "gmaps"])
        for i, c in enumerate(wpts, 1):
            wr.writerow([f"invasive_{i}", c["lat"], c["lon"], c["likelihood"], c.get("rf_prob"),
                         f"https://www.google.com/maps/search/?api=1&query={c['lat']:.5f},{c['lon']:.5f}"])
    fc = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"name": f"invasive_{i}", "likelihood": c["likelihood"],
         "rf_prob": c.get("rf_prob")},
         "geometry": {"type": "Point", "coordinates": [c["lon"], c["lat"]]}} for i, c in enumerate(wpts, 1)]}
    json.dump(fc, open(WPTS_GEO, "w"), indent=1)


def describe():
    return {
        "connector": "invasive",
        "purpose": "Free, field-navigable invasive-LIKELIHOOD map for the EBTL site — for ANY invasive.",
        "produces": "an HTML map + GPS waypoints (CSV/GeoJSON) of the top candidate patches.",
        "functions": [
            "map(species, year=2024, n=28) -> build (EE) + render; = the full funnel for one species",
            "build(species) -> data.json (EE RandomForest on recent GBIF records + multi-year S2 phenology)",
            "render(species) -> map.html + waypoints.csv/.geojson",
        ],
        "use": "Regenerate the invasive map for another species: "
               "`python /opt/data/connectors/invasive.py map --species \"Prosopis juliflora\"`. It pulls "
               "that species' RECENT records (GBIF), trains an S2 RandomForest vs background, adds "
               "multi-year stay-green phenology, and writes a field-navigable map + GPS waypoints. Then "
               "confirm the top waypoints with a high-res scene via `skyfi.py best`.",
        "gotcha": "Needs Earth Engine (runs in the hermes container). Output = invasive-LIKELIHOOD, a "
                  "TRANSFER from corridor records, NOT a confirmed species map — walk the waypoints or "
                  "buy one SkyFi scene to confirm. Writes to /opt/data/work/invasive/<species>/.",
        "example": "python /opt/data/connectors/invasive.py map --species \"Lantana camara\"",
    }


def _main(argv=None):
    ap = argparse.ArgumentParser(prog="invasive")
    ap.add_argument("--describe", action="store_true")
    ap.add_argument("cmd", choices=["map", "build", "render"], nargs="?")
    ap.add_argument("--species", default="Lantana camara")
    ap.add_argument("--year", type=int, default=2024)
    ap.add_argument("--n", type=int, default=28)
    a = ap.parse_args(argv)
    if a.describe or not a.cmd:
        print(json.dumps(describe(), indent=2)); return
    if a.cmd in ("map", "build"):
        build(a.species, a.year, a.n)
    if a.cmd in ("map", "render"):
        render(a.species)


if __name__ == "__main__":
    _main()
