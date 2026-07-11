# groundtruth_lens — the verify lens (cross-cutting GROUND-TRUTH layer)

- **purpose:** after any TRANSFER puts a modelled signal on a map (invasive, predict/RF/SDM, greening),
  show it with a **method toggle** + a **cursor lens onto high-res imagery** so the user eyeballs reality.
- **produces:** a self-contained **static HTML** (image + layers embedded) — no server, no RAM. Hand back the path.
- **bucket:** GROUND-TRUTH (verify) — a cross-cutting *output* layer (see `../SKILL_ALGEBRA.md`), reusable for
  invasives / "what grows here" / "where is X vs Y" / "is Y greening".

**functions**
- `build(base_img, bbox_wsen, layers, out, title)` — `layers = {name: [{lat,lon,value}...]}`
- CLI `build --base <jpg/png> --bbox w,s,e,n --a1 <invasive data.json> --out <html>` (`--a1` auto-extracts
  the RF / phenology / combined layers)

**PIL-only** → runs in the Hermes container (no numpy/rasterio). Base must be a plain image + its geographic
extent (`--bbox`); it must cover the **same area** as the layers. A staged EBTL high-res base lives at
`/opt/data/work/gt/ebtl_base.jpg` (extent in `ebtl_base.json`).

**example**
```
python /opt/data/connectors/groundtruth_lens.py build \
  --base /opt/data/work/gt/ebtl_base.jpg --bbox 78.176867,12.727863,78.190131,12.740135 \
  --a1 /opt/data/work/invasive/lantana_camara/data.json --out /opt/data/work/gt/lens.html
```

**gotcha:** static HTML (no server). Points to verify against: `occurrence` (GBIF) + iNaturalist direct.
The lens exposes false transfers instantly — hot cells on orchards/scrub ⇒ the model is wrong there.
