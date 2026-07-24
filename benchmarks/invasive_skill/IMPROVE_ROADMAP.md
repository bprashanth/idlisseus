# Improvement roadmap — invasive_skill

The menu of experiments to make the free invasive map reliable, ranked by value/effort. Each is a CHANGE-,
STATE-, or VALUE-bucket method (`../semantic_broker/SKILL_ALGEBRA.md`) with TRANSFER + the GROUND-TRUTH lens.
Beat the current skill on the metrics below, then fold the winner back into `invasive.py`.

## Why the current skill is weak (the gap to close)
Static appearance rules fail (flag orchards/dry-soil); the transferred RF is soft (records 20–40 km away);
free-model and high-res disagree (rho ~0.36); nothing is calibrated because there's **no local ground
truth**. So the wins are: (a) better *change* signals, (b) *learned* classifiers on real labels, (c) fusion.

## Ranked experiments
1. **Phenology time-series classifier (CHANGE, free) — highest value.** Replace the crude 2-date stay-green
   with a full-year S2 NDVI/NDRE trajectory per pixel → harmonic fit + phenology metrics (amplitude,
   green-up/senescence timing, flowering pulses). Lantana = low amplitude (evergreen) + flowering bumps vs
   deciduous natives' big amplitude. Classify by curve **shape**. This is the single best *free* upgrade and
   it generalises to any invasive. Extends `s2.py`.
2. **Trained classifier on labels (STATE, calibrated).** Take the `label_sheet.py` CSV (user-tagged 35 cm
   crops) → features = 8 bands + NDVI/NDRE/**yellow-tawny** + multi-scale texture → train RF/GBM → probability
   map. This is what actually fixes EBTL. Pair with **active learning** (label only the uncertain tiles).
3. **Multi-year invasion-front detection (CHANGE).** Lantana *spreads*: detect year-over-year greening/
   thickening at edges (NDVI trend up where natives are stable). Finds the *process*, very invasive-specific.
4. **High-res fusion (the target architecture).** Phenology-change to LOCATE candidate zones (10 m, free) →
   labelled 8-band + texture to DELINEATE within them (35 cm) → multi-method **agreement** = confidence tiers.
5. **Spectral unmixing (VALUE, 8-band).** Estimate a Lantana *fraction* per pixel from endmember spectra —
   uses yellow/red-edge directly; softer than hard classification, good under mixed canopies.
6. **Gudalur drone transfer / validation.** Domain-adapt the drone-labelled Lantana signature (RGB+texture)
   to EBTL; use mainly to validate separability and as a texture prior. See `DATA_AND_KEYS.md` caveats.

## Metrics (from `../semantic_broker/experiments/INVASIVE_MAP_BENCHMARK.md`)
- **H1** concordance (free ↔ high-res): Spearman + top-decile IoU → is "screen free, buy high-res on hotspots" valid?
- **H2** real accuracy: held-out precision/recall/AUC on a labelled set (label_sheet, or a reference region
  with GBIF). AUC ≥ 0.8 ⇒ trust it.
- **H3** agreement map + confidence tiers.
- **Qualitative eyescan**: always emit the `groundtruth_lens.py` map — if hot cells sit on real thickets it holds.

## How to extend the skill CLEANLY (the contract)
`invasive.py` is the public interface. Do NOT fork it per experiment. Instead:
- Keep the entry point `map(species, year, n)` and the **`data.json` schema** (grid of `{lat,lon,likelihood,
  rf_prob,persist,...}` + `validation` + `method`). The UX/lens/waypoints all read that schema — freeze it.
- Add a new method as a **new function** producing the same per-cell fields, and expose a `--method`/`--product`
  flag (e.g. `phenology_ts`, `classifier`, `fusion`). Default stays the current behaviour until a method wins.
- Prototype in *this* dir (`invasive_skill/`), measure on H1/H2/H3, then wire the winner behind the flag.

## How to categorise anything new (so it doesn't sprawl)
Every new tool declares its **bucket + /why template** per `SKILL_ALGEBRA.md`:
- a new detector = STATE or CHANGE (+ TRANSFER if it projects off-site);
- a new "how much invaded" = VALUE;
- a new viewer/verifier = extend the **GROUND-TRUTH** lens (`groundtruth_lens.py`), don't invent a new one.
Add a one-line `/why` sentence so the agent can explain it. If it's genuinely a new question-type, add a
bucket — but prefer reusing one. This keeps the skill set legible as it grows.

## Generalisation beyond Lantana (the real prize)
This whole chain — **identify species X → get points (GBIF + iNaturalist) → transfer via multiple methods →
show all trends on the GROUND-TRUTH lens over high-res → let a human eyecall** — is not Lantana-specific.
It's the pattern for *any* "where is species X / what grows here / is Y greening" question. Invasives are a
special case (change-detection shines). Build the ground-truthing infra once (label_sheet + lens), reuse everywhere.
