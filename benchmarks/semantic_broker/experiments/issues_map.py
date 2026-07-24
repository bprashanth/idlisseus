#!/usr/bin/env python3
"""Field-priorities map: overlay the top DSS findings (Lantana hotspots, elephant records, the site
outline) on a satellite base, with a GPS waypoint table so the EBTL team can go verify/collect today.
Reads a base JPEG + a markers.json {region:[w,s,e,n], lantana:[{lat,lon,lik}], elephants:[{lat,lon}], ...}.
Self-contained HTML — hand back the file (served at :8000)."""
import base64
import io
import json
import sys

from PIL import Image, ImageEnhance


def build(base_jpg, markers_json, out, site_bbox=(78.170, 12.721, 78.197, 12.747)):
    m = json.load(open(markers_json))
    w, s, e, n = m["region"]
    im = Image.open(base_jpg).convert("RGB")
    im = ImageEnhance.Brightness(im).enhance(1.35)
    im = ImageEnhance.Contrast(im).enhance(1.15)
    im = ImageEnhance.Color(im).enhance(1.3)
    W, H = im.size
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=90)
    b64 = base64.b64encode(buf.getvalue()).decode()

    def X(lon): return (lon - w) / (e - w) * W
    def Y(lat): return (n - lat) / (n - s) * H

    svg = []
    # site outline
    sx0, sy0, sx1, sy1 = X(site_bbox[0]), Y(site_bbox[3]), X(site_bbox[2]), Y(site_bbox[1])
    svg.append(f'<rect x="{sx0:.0f}" y="{sy0:.0f}" width="{sx1-sx0:.0f}" height="{sy1-sy0:.0f}" '
               f'fill="none" stroke="#ffffff" stroke-width="3" stroke-dasharray="10 6"/>')
    svg.append(f'<text x="{sx0+6:.0f}" y="{sy0+22:.0f}" fill="#fff" font-size="18" font-weight="700">your site</text>')
    wpts = []
    for i, c in enumerate(m.get("lantana", []), 1):
        x, y = X(c["lon"]), Y(c["lat"])
        svg.append(f'<rect x="{x-11:.0f}" y="{y-11:.0f}" width="22" height="22" fill="none" '
                   f'stroke="#ff7b00" stroke-width="3"/>')
        wpts.append(("Lantana hotspot", c["lat"], c["lon"], f"confirm Lantana (model {c.get('lik','')})"))
    for c in m.get("elephants", []):
        x, y = X(c["lon"]), Y(c["lat"])
        svg.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="11" fill="none" stroke="#c77dff" stroke-width="3"/>'
                   f'<circle cx="{x:.0f}" cy="{y:.0f}" r="3" fill="#c77dff"/>')
        wpts.append(("Elephant record", c["lat"], c["lon"], "look for dung / feeding sign"))
    for c in m.get("ponds", []):
        x, y = X(c["lon"]), Y(c["lat"])
        svg.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="10" fill="none" stroke="#4cc9f0" stroke-width="3"/>')
        wpts.append(("Pond", c["lat"], c["lon"], "measure water level / depth"))

    rows = "".join(
        f'<tr><td>{i}</td><td><span class="dot {t.split()[0].lower()}"></span>{t}</td>'
        f'<td>{la:.5f}, {lo:.5f}</td><td>{note}</td>'
        f'<td><a target="_blank" href="https://www.google.com/maps/search/?api=1&query={la:.5f},{lo:.5f}">open ▸</a></td></tr>'
        for i, (t, la, lo, note) in enumerate(wpts, 1))

    doc = f"""<style>
html,body{{margin:0;background:#0b0d12;color:#c9d1d9;font:13px/1.5 system-ui,sans-serif}}
header{{padding:10px 18px;background:#12151c;border-bottom:1px solid #262b36}}
.ttl{{font-weight:700;font-size:16px;color:#e6edf3}} .sub{{color:#8b949e;font-size:12px;margin-top:2px}}
.legend{{display:flex;gap:18px;padding:7px 18px;font-size:12px;flex-wrap:wrap;border-bottom:1px solid #262b36}}
.legend span{{display:inline-flex;align-items:center;gap:6px}}
.k{{width:13px;height:13px;border-radius:3px;display:inline-block}}
.wrap{{display:flex;gap:14px;padding:12px 18px;align-items:flex-start;flex-wrap:wrap}}
.stage{{position:relative;flex:1 1 640px;min-width:340px}} .stage img{{width:100%;display:block;border-radius:6px}}
.stage svg{{position:absolute;inset:0;width:100%;height:100%}}
table{{border-collapse:collapse;font-size:12px;flex:1 1 380px}} th,td{{border:1px solid #262b36;padding:4px 9px;text-align:left}}
th{{background:#12151c}} td a{{color:#58a6ff;text-decoration:none}}
.dot{{width:9px;height:9px;border-radius:50%;display:inline-block;margin-right:5px}}
.lantana{{background:#ff7b00}} .elephant{{background:#c77dff}} .pond{{background:#4cc9f0}}
.note{{font-size:11px;color:#8b949e;padding:0 18px 14px}}</style>
<header><div class="ttl">EBTL field priorities — where to verify / collect data</div>
<div class="sub">Sentinel-2 (dry season) base · the top DSS findings mapped, with GPS to navigate.
<b style="color:#ffb454">All are model estimates / opportunistic records — go confirm on the ground.</b></div></header>
<div class="legend">
<span><i class="k" style="background:#ff7b00"></i> Lantana hotspot (confirm)</span>
<span><i class="k" style="background:#c77dff"></i> Elephant record (dung/sign)</span>
<span><i class="k" style="background:#4cc9f0"></i> Pond (measure)</span>
<span><i class="k" style="background:#fff"></i> your ~70-acre site</span></div>
<div class="wrap"><div class="stage"><img src="data:image/jpeg;base64,{b64}">
<svg viewBox="0 0 {W} {H}" preserveAspectRatio="none">{''.join(svg)}</svg></div>
<table><tr><th>#</th><th>issue</th><th>lat, lon</th><th>go check</th><th>map</th></tr>{rows}</table></div>
<div class="note">Notes: Lantana squares are the model's highest-likelihood cells (verify — evergreen natives
can false-trigger). Elephants are sparse here; the dense corridor is further west — 6 of 11 site
waterbodies are ephemeral (~1 month/yr), so measuring your ponds' depth/timing is high-value. Send us pond
GPS + any Lantana / not-Lantana points and we sharpen every layer.</div>"""
    open(out, "w").write(doc)
    print(f"wrote {out}  ({len(wpts)} field waypoints)")


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2], sys.argv[3])
