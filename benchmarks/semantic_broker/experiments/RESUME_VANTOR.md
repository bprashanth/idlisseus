# ▶ RESUME HERE when the Vantor scene arrives — imagery pickup handoff

*Written 2026-07-06. If you are a fresh agent (possibly many compactions later): this is the single
entry point for finishing the SkyFi/Vantor invasive-map experiment. Read it top to bottom first.*

## ⛔ STOP — before you touch the delivered image, CHECKPOINT WITH THE USER (bprashanth)
Do **not** silently proceed. Message the user and confirm, explicitly:
1. **Plan still good?** Re-summarise the plan below and get a "go".
2. **SkyFi balance.** Phase A ($44.88) bills **on delivery** — so after it lands only ~**₹1300 (~$15)**
   remains of the ₹5000 budget. **Phase B needs a top-up** — do NOT order it without the user funding it.
   Check balance: `curl -s -A Mozilla/5.0 -H "X-Skyfi-Api-Key: $(python3 -c "import json;print(json.load(open('$HOME/.config/idlisseus/skyfi.json'))['api_key'].strip())")" https://app.skyfi.com/platform-api/auth/whoami` → `budgetAmount - currentBudgetUsage` (INR).
3. **Disk.** COG is ~200–500 MB; ensure ~1 GB free (`df -h ~`). 235 G was free at write time.
Only after the user confirms all three, proceed.

## Where things stand (2026-07-06)
- **Phase A ORDERED, delivering (~24 h).** VANTOR **SUPER HIGH 35 cm**, cloud-free capture **2026-04-02**,
  crop **`78.177,12.728,78.190,12.740`** (~1.87 km², EBTL restoration core + western hotspots wpts 5–8),
  **$44.88**. `orderId = 168c903d-71a9-4e04-a0a6-ba2d979c7bc8`, `archiveId = f8669acf-acbe-4d30-be3d-2b0d24eadb10`.
- A background poller (`/tmp/skyfi_poll.py`, log `/tmp/skyfi_poll.log`) checks status every 20 min; it may
  not survive a reboot — if gone, just poll manually (below).

## Step 1 — is it ready? download it
```
cd benchmarks/semantic_broker/connectors
python3 skyfi.py status --order-id 168c903d-71a9-4e04-a0a6-ba2d979c7bc8      # look for a non-null downloadCogUrl / status DELIVERED
python3 skyfi.py download --order-id 168c903d-71a9-4e04-a0a6-ba2d979c7bc8 --deliverable cog --out /home/beeps/skyfi/ebtl_superhigh.tif
```
**Get the `cog` (analytical multispectral — has NIR), NOT just `view_ready_cog` (8-bit RGB).** A2 needs NIR.
If the download URL 302-redirects, `skyfi.py download` already follows it. Report the actual band count.

## Step 2 — run A2 (spatial segmentation + concordance with the free map)
Pipeline: `benchmarks/semantic_broker/experiments/a2_segment.py`. Runs on the **host** venv `/tmp/a2venv`
(rasterio/skimage/scipy/numpy/affine). **If `/tmp/a2venv` is gone** (reboot), recreate:
`python3 -m venv /tmp/a2venv && /tmp/a2venv/bin/pip install numpy scipy scikit-image rasterio affine`.
```
/tmp/a2venv/bin/python a2_segment.py analyze \
   --cog /home/beeps/skyfi/ebtl_superhigh.tif \
   --a1  ~/.hermes/work/invasive/lantana_camara/data.json \
   --out /home/beeps/skyfi/a2_out/
```
(The A1 free-map data.json is written by `connectors/invasive.py map --species "Lantana camara"`, in the
hermes container, to `/opt/data/work/invasive/lantana_camara/` = `~/.hermes/work/invasive/...` on host,
owned uid 10000 — `sudo` to read, or re-run the map.) Outputs: `a2_result.json` (H1 concordance rho/IoU +
verdict), `a2_segments.png`. **Then TUNE**: inspect NDVI/texture histograms on the real scene, adjust the
veg gate / score weights in `a2_score()`, and photo-interpret a few obvious Lantana thickets at 35 cm to
sanity-check. Self-test proves the mechanics (`a2_segment.py selftest` → rho ~0.45); real thresholds differ.

## Step 3 — interpret & decide Phase B (WITH the user)
- **H1 concordance** (a2_result.json `spearman_rho`, `top_decile_iou`, `H1_verdict`): does the free S2 map
  predict where high-res shows Lantana? → your a/b/c. If concordant, "screen free, buy high-res only on
  hotspots" is validated.
- Build the **fused/agreement map** (A1∩A2 tiers) + waypoints, send to user.
- **Phase B** (real accuracy number): reference-region Vantor scene over a GBIF-Lantana cluster (~$48) →
  train the A2 signature on real GBIF + matched negatives → held-out AUC → apply to EBTL. **Needs balance
  top-up + user go.** See `INVASIVE_MAP_BENCHMARK.md` (H2).

## The full plan & contracts (read these)
- `INVASIVE_MAP_BENCHMARK.md` — hypotheses H1/H2/H3, 4 ground-truth substitutes, phased cost (A $45 done /
  B $48 / C $45 optional), map-products table, the `data.json` UX-fork contract.
- `../SKILL_ALGEBRA.md` — skill taxonomy (invasive map = CHANGE+TRANSFER free, STATE+TRANSFER paid).
- `../connectors/skyfi.py` (client, budget-guarded), `../connectors/invasive.py` (free map, any species),
  `../connectors/PLAYBOOK.md` ("where are the invasives" skill).

## Cost ledger
- Phase A: **$44.88** SkyFi (bills on delivery). Model×skill matrix: **$1.79** OpenRouter. Nothing else spent.

## Gotchas (won't be obvious)
- SkyFi is behind Cloudflare → needs a browser `User-Agent` (already in `skyfi.py`). Key at
  `~/.config/idlisseus/skyfi.json`. Vantor EULA already accepted.
- The **hermes container venv lacks rasterio/skimage** — A2 runs on the host venv. To make A2 a Hermes
  skill later, bake those libs into the image (like the ee/pymupdf preinstall in `agents/hermes/Dockerfile`).
- SkyFi crop must sit inside the archive footprint or you get "Area size not supported / <1.0 km²".
