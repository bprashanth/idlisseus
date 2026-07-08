# EBTL live DSS map — the front-end approach

The **site-level front-end** for the EBTL decision-support demo: a single self-contained `index.html`
that a non-technical restoration team opens on a phone or laptop. It is the composition layer that sits
**above** the connector-level verify lens ([`groundtruth_lens.md`](../connectors/groundtruth_lens.md)):
the lens ground-truths one transfer; this app tells the whole "issues that need data" story.

Builder: **`issues_app.py`** → writes `agents/hermes/gt/index.html`. Deployed to a **public S3 bucket**.
(Earlier/simpler variant: `issues_map.py` = a static field-priorities map with a GPS waypoint table.)

## What it does
- **Landing = zoomed-out Sentinel-2 overview** of the region with the EBTL site outlined and three broad,
  pulsing problem markers (Lantana / Elephants / Water) + an "issues that need data" panel.
- **Zoom in** (scroll / pinch, or tap a marker) → a smooth transform-zoom that crosses a threshold and
  **crossfades into the 35 cm Maxar (Vantor) detail**, auto-focused on the problem nearest the zoom point.
- Each issue's in-depth panel is the honesty contract: a plain **problem description**, the **questions**
  that surfaced it (from `SYLLABUS.md` / the night run), the **papers consulted** (clickable DOIs via the
  `paper_data` connector), the **method**, the ecological **drivers**, an **honest limit**, and the **one
  dataset we still need**.
- **Lantana has three toggle layers** — this is the core pattern:
  - **Prediction** — only cells where *multiple methods agree* (RF on S2 indices **AND** dry-season
    stay-green phenology both above threshold), coloured blue→red. Fewer, higher-confidence squares.
  - **Drivers** — canopy-gap cells (bottom-percentile dry-season NDVI = open/disturbed canopy), the
    condition the literature ties to establishment. Amber, visually distinct from the prediction.
  - **Records** — the **actual** GBIF+iNaturalist occurrence points on a wide base with distance rings,
    making the transfer honest: every real record is >13 km from the site.

## Design principles (why it's built this way)
- **Self-contained, no external deps.** All images are base64-embedded; CSS/JS inline; no CDN, no fetch.
  It renders from a single file on S3 (or a dead laptop's disk). Each base image is embedded **once** and
  assigned to its `<img>`s via JS to avoid doubling the payload (~5 MB total).
- **Honest by construction.** Every layer states "model estimate / opportunistic record — not a
  confirmed sighting", names its source, and asks for the field data that would confirm it. Colour =
  concern/agreement, never decoration. "Stay-green phenology" is labelled *vegetation phenology, NOT
  wildfire* (a real point of confusion — we model stay-green, not fire; `fire.py` is separate).
- **Overlap over volume.** Show the *intersection* of independent methods, not every cell one method lit.
- **Mobile-first.** `<meta viewport>`, responsive layout (map on top, panel/tabs stacked below on
  narrow), and touch gestures (one-finger pan, two-finger pinch-zoom) in the same zoom engine as wheel.
- **Aspect-locked overlays.** `<img object-fit:contain>` + SVG `preserveAspectRatio="xMidYMid meet"` so
  overlays letterbox identically to the imagery and never stretch off the ground at odd window sizes.
- **Deep-linkable.** `#lantana` / `#water` / `#elephant` open that view (also how we screenshot-verify).

## Data pipeline (all deterministic, cached)
Bases live in `agents/hermes/gt/` (mounted into the container at `/opt/data/work/gt/`):
- `region_base.jpg` — S2 dry-season overview (landing).
- `ebtl_base.jpg` — 35 cm Vantor/Maxar crop (`bbox 78.176867,12.727863,78.190131,12.740135`), dehazed.
- `donor_base.jpg` — **wide** S2 base (`77.98,12.55,78.35,12.86`) for the Records layer, generated via
  EE `getThumbURL` (dry-season median, cloud-masked) — see the snippet in git history / this dir.
- `lantana_data.json` — the invasive grid (`rf_prob`, `persist`, `ndvi_dry`, `likelihood`) from `s2.anomaly_grid` + `predict`.
- `lantana_points.csv` — actual occurrences from the **`points` resolver** (GBIF+iNaturalist+paper, merged, deduped).
- `ebtl_pond_points.csv` — detected water pixels (JRC / S2) for the Water layer.
- Drivers cited from **`paper_data.find`** (NCF/Zenodo DOIs); honest caveat that they're Western Ghats
  wet-forest studies transferred onto our dry site.

## Build & deploy
```bash
# 1. build (reads the bases above; regenerates the single file)
python benchmarks/semantic_broker/experiments/issues_app.py      # -> agents/hermes/gt/index.html

# 2. verify locally (served by the always-on mapserver on :8000 → agents/hermes/gt)
#    or headless (snap Firefox CANNOT write /tmp — screenshot to $HOME; use #hash to hit a view):
firefox --headless --window-size=390,844 --screenshot "$HOME/shot.png" "file://.../index.html#lantana"

# 3. deploy to a PUBLIC bucket (ap-south-1; temporary demo — take down after)
BUCKET=ebtl-dss-<n>
aws s3api create-bucket --bucket $BUCKET --region ap-south-1 \
  --create-bucket-configuration LocationConstraint=ap-south-1
aws s3api put-public-access-block --bucket $BUCKET \
  --public-access-block-configuration BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false
aws s3 website s3://$BUCKET --index-document index.html
aws s3api put-bucket-policy --bucket $BUCKET --policy '{"Version":"2012-10-17","Statement":[{"Sid":"PublicRead","Effect":"Allow","Principal":"*","Action":"s3:GetObject","Resource":"arn:aws:s3:::'"$BUCKET"'/*"}]}'
aws s3 cp agents/hermes/gt/index.html s3://$BUCKET/index.html --content-type "text/html; charset=utf-8"
# URL: http://$BUCKET.s3-website.ap-south-1.amazonaws.com/
# Teardown:  aws s3 rb s3://$BUCKET --force
```
AWS: account 024848460644, region ap-south-1, user prashanth@tech4goodcommunity.com. **Sensitivity:** the
map exposes the site + elephant coordinates on a public bucket — only deploy for the demo window, then
`rb --force`.

## Relationship to the other map pieces
- `groundtruth_lens.py` — connector-level VERIFY output for **one** transfer (method toggle + cursor lens).
  The app's Lantana Prediction/Drivers layers are the same idea, composed into the site story.
- `issues_map.py` — the earlier static field-priorities map + GPS waypoint table (print-and-walk).
- `issues_app.py` — this interactive, deployable front-end. Prefer it for the live demo.
