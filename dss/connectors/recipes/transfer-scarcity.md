# Recipe: data-scarcity transfer (the predict.route path)

Many EBTL questions are about a **data-poor site**. If `points.get` over the tight AOI returns few/no
records, do **not** give up and do **not** generalise from far-away data blindly. Gather donor points from
a wider analog region and let `predict.route` decide if/how to transfer.

1. **Donor points** over a wider, ecologically-similar region (EBTL dry-Deccan belt `76.0,11.0,79.5,13.6`):
   `python /opt/data/connectors/points.py get --species "<name>" --bbox 76.0,11.0,79.5,13.6`
   (paper_data is folded in — its dataset-embedded points are the highest-grade donors).
2. **Route** — one call decides everything (prints JSON to **stdout**; `--points` = the donor CSV):
   `python /opt/data/connectors/predict.py route --points <donor.csv> --bbox <w,s,e,n> --question presence`
   (`--question value` for a continuous measurement). It runs the **gate** (is the AOI similar to donors in
   satellite appearance AND/OR climate?), runs every **valid** method, and returns a **situation**:
   - `answerable` → report the modelled suggestion **+ caveat** (modelled not observed; if two methods
     agreed, say so — it's stronger).
   - `need_more_data` → the honest answer is a **data gap**: tell the user exactly what to go measure.
   - `need_better_models` → methods disagree; **surface the conflict**, don't average it away.
3. **paper_data = verified ground truth** — check alongside; data found in a paper is confirmed and can
   ground-truth a transfer.
4. **Surface a concrete nice-to-have dataset** on `need_more_data` (don't refuse): higher-res hyperspectral
   (~5 m Pixxel > EMIT 60 m), acoustic detectors (AudioMoth+BirdNET), structured effort by habitat, targeted
   surveys. Give the best gated estimate **and** the acquirable next step. See `ebtl/DATA_GAPS.md`.

Full reasoning: `predict.md` + `TRANSFER_ALGEBRA.md`.
