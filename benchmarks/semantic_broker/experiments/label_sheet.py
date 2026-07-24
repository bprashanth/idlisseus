#!/usr/bin/env python3
"""Build a self-contained labelling sheet from the Vantor scene: a grid of 35 cm crops the user tags as
Lantana / not / unsure by clicking. Emits a CSV (in-page, copy-paste) that trains the A2 classifier.

  /tmp/a2venv/bin/python label_sheet.py --cog scene.tif --a2 a2_out/a2_result.json --ref lantana_ref.jpg --out sheet.html
"""
import argparse
import base64
import io
import json
import os

import numpy as np
import rasterio
from rasterio.warp import transform as wt
from PIL import Image


def _u8(band):
    lo, hi = np.percentile(band, 2), np.percentile(band, 98)
    return (np.clip((band - lo) / (hi - lo + 1e-9), 0, 1) ** 0.8 * 255)


def _b64(ds, r, c, px=130, size=150):
    win = ((max(0, r - px), r + px), (max(0, c - px), c + px))
    a = ds.read([5, 3, 2], window=win).astype("float32")   # WV-3 true colour R,G,B
    if a.shape[1] < 20 or a.shape[2] < 20:
        return None
    rgb = np.dstack([_u8(a[i]) for i in range(3)]).astype("uint8")
    if rgb.mean() < 12:                                     # nodata / black border
        return None
    buf = io.BytesIO(); Image.fromarray(rgb).resize((size, size)).save(buf, "JPEG", quality=82)
    return base64.b64encode(buf.getvalue()).decode()


def build(cog, a2json, ref, out, grid=7):
    ds = rasterio.open(cog)
    H, W = ds.height, ds.width
    tiles = []
    for gr in range(grid):
        for gc in range(grid):
            r, c = int((gr + 0.5) / grid * H), int((gc + 0.5) / grid * W)
            b = _b64(ds, r, c)
            if b:
                x, y = rasterio.transform.xy(ds.transform, r, c)
                lon, lat = wt(ds.crs, "EPSG:4326", [x], [y])
                tiles.append((f"g{gr}{gc}", round(lat[0], 6), round(lon[0], 6), b))
    if a2json and os.path.exists(a2json):                  # add the A2 candidates to confirm/deny
        for cd in json.load(open(a2json)).get("candidates", []):
            x, y = wt("EPSG:4326", ds.crs, [cd["lon"]], [cd["lat"]])
            r, c = ds.index(x[0], y[0])
            b = _b64(ds, int(r), int(c))
            if b:
                tiles.append((f"cand{cd['rank']}", cd["lat"], cd["lon"], b))
    refimg = ""
    if ref and os.path.exists(ref):
        im = Image.open(ref).convert("RGB"); im.thumbnail((260, 260))
        buf = io.BytesIO(); im.save(buf, "JPEG", quality=85)
        refimg = f'<img src="data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}">'

    cells = "".join(
        f'<div class="tile" data-id="{tid}" data-lat="{lat}" data-lon="{lon}" onclick="cyc(this)">'
        f'<img src="data:image/jpeg;base64,{b}"><div class="cap">{tid}</div></div>'
        for tid, lat, lon, b in tiles)
    html = f"""<style>
body{{font:14px system-ui;margin:0;background:#0d1117;color:#c9d1d9}}
header{{padding:12px 16px;background:#161b22;border-bottom:1px solid #30363d}}
.ref{{display:flex;gap:14px;align-items:center;padding:10px 16px;background:#12261a}}
.ref img{{border-radius:8px;border:2px solid #7ee787}} .ref b{{color:#7ee787}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px;padding:14px}}
.tile{{position:relative;cursor:pointer;border-radius:8px;overflow:hidden;border:3px solid #30363d}}
.tile img{{width:100%;display:block}} .cap{{position:absolute;top:0;left:0;background:#000a;color:#fff;font-size:11px;padding:1px 5px}}
.tile.lantana{{border-color:#3fb950;box-shadow:0 0 0 2px #3fb95066}} .tile.not{{border-color:#f85149}}
.tile.unsure{{border-color:#d29922}}
.tile .lab{{position:absolute;bottom:0;right:0;font-size:11px;font-weight:700;padding:1px 6px;color:#fff}}
.lantana .lab{{background:#3fb950}} .not .lab{{background:#f85149}} .unsure .lab{{background:#d29922}}
.bar{{position:sticky;bottom:0;background:#161b22;border-top:1px solid #30363d;padding:10px 16px}}
textarea{{width:100%;height:80px;background:#0d1117;color:#7ee787;border:1px solid #30363d;border-radius:6px;font:12px monospace}}
button{{background:#238636;color:#fff;border:0;padding:7px 14px;border-radius:6px;cursor:pointer;font-weight:600}}</style>
<header><b>Label the Lantana</b> — click a tile to cycle: <span style="color:#3fb950">Lantana</span> →
<span style="color:#f85149">not</span> → <span style="color:#d29922">unsure</span> → blank. Aim for ~15–20
tiles (a mix of yes and no). Then click <b>Copy CSV</b> and send it back.</header>
<div class="ref">{refimg}<div>Your reference — <b>Lantana</b> is the brownish-tawny, finely-mottled tangled
carpet. Tiles are 35 cm Vantor, ~90 m across, dry season. <br><small>cand* tiles are the detector's guesses —
confirming/denying those is especially useful.</small></div></div>
<div class="grid">{cells}</div>
<div class="bar"><button onclick="cp()">Copy CSV</button> <span id="n">0 labelled</span>
<textarea id="out" readonly></textarea></div>
<script>
var S=['','lantana','not','unsure'];
function cyc(el){{var i=(S.indexOf(el.dataset.s||'')+1)%4;el.dataset.s=S[i];el.className='tile'+(S[i]?' '+S[i]:'');
 el.querySelector('.lab')&&el.querySelector('.lab').remove();
 if(S[i]){{var d=document.createElement('div');d.className='lab';d.textContent=S[i];el.appendChild(d);}}upd();}}
function upd(){{var rows=['id,lat,lon,label'],k=0;document.querySelectorAll('.tile').forEach(function(t){{
 if(t.dataset.s){{k++;rows.push(t.dataset.id+','+t.dataset.lat+','+t.dataset.lon+','+t.dataset.s);}}}});
 document.getElementById('out').value=rows.join('\\n');document.getElementById('n').textContent=k+' labelled';}}
function cp(){{var o=document.getElementById('out');o.select();document.execCommand('copy');}}
</script>"""
    open(out, "w").write(html)
    print(f"wrote {out}  ({len(tiles)} tiles)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cog", required=True); ap.add_argument("--a2"); ap.add_argument("--ref")
    ap.add_argument("--out", default="label_sheet.html"); ap.add_argument("--grid", type=int, default=7)
    a = ap.parse_args()
    build(a.cog, a.a2, a.ref, a.out, a.grid)
