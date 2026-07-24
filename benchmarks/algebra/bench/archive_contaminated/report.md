# Head-to-head: our stack (A) vs plain CLI baseline (B)

2 questions run.

**Wins:** A=0 · B=2 · tie=0

## Q0: In our Krishnagiri dry-deciduous restoration blocks (2018–2024 plantings), which 5–50 ha patches show sustained NDVI green-up through three consecutive post-monsoon seasons versus reverting to scrub?
- **A** (204s, connectors: ['greenness']): rs/greenness.py --describe  0.1s

╭─ Ψ Poseidon ─────────────────────────────────────────────────────────────────╮
    I need to generate a grid of sample points across the Krishnagiri restoration area to analyze. Let me first check if there's an existing asset or CSV with planting block coordinates, or I'll create a systematic grid over the AOI.
    
╰──────────────────────────────────────────────────────────────────────────────╯
  │ 💻 $         find /opt/data -name "*.csv" -o -name "*krishnagiri*" -o -name "*planting*" 2>/dev/null | head -20  0.2s
  ┊ 📖 preparing read_file…
  │ 📖 read      /
- **B** (66s): I can’t give you a ranked list of specific 5–50 ha patches from here. That question needs **your restoration-block inventory** plus **seasonal NDVI computed per patch**, and neither is available in this workspace or in the open datasets we’ve searched.

## What’s missing

To answer “which patches greened up for three consecutive post-monsoon seasons vs reverted to scrub,” you need:

1. **Patch polygons (or centroids + area)** for each 2018–2024 planting block, with:
   - `patch_id`, `area_ha` (filter 5–50 ha), `planting_year`
2. **Post-monsoon NDVI time series per patch** — typically an Oct–No
- **judge:** winner=B · site_specific=B · data_grounded=B · B_hallucinated=False · _B correctly identified missing patch GIS and that greenness only yields annual MODIS trends—not three post-monsoon seasons or 5–50 ha blocks—while A mislabeled coarse grid slopes as named restoration patches._

## Q0: In our Krishnagiri dry-deciduous restoration blocks (2018–2024 plantings), which 5–50 ha patches show sustained NDVI green-up through three consecutive post-monsoon seasons versus reverting to scrub?
- **A** (295s, connectors: ['greenness']): s
  ┊ 📖 preparing read_file…
  │ 📖 read      /opt/data/work/krishnagiri_grid.csv  0.1s
  ┊ 📖 preparing read_file…
  │ 📖 read      /opt/data/work/ndvi_trend_krishnagiri.csv  0.1s
  │ 💻 $         python /opt/data/connectors/greenness.py --describe  0.1s
  │ 💻 $         mkdir -p /opt/data/work && python /opt/data/connectors/greenness.py trend --points /opt/data/work/krishnagiri_grid.csv --years 2019-2024 --out /opt/data/work/krishnagiri_ndvi_trend.csv  6.4s
  │ 💻 $         cat /opt/data/work/krishnagiri_ndvi_trend.csv | head -50  0.1s
  │ 🐍 exec      import pandas as pd  0.1s [Traceback (most rec
- **B** (38s): I can’t give you a ranked list of specific 5–50 ha patches from here. That question needs **your restoration-block inventory** plus **seasonal NDVI computed per patch**, and neither is available in this workspace or in the open datasets we’ve searched.

## What’s missing

To answer “which patches greened up for three consecutive post-monsoon seasons vs reverted to scrub,” you need:

1. **Patch polygons (or centroids + area)** for each 2018–2024 planting block, with:
   - `patch_id`, `area_ha` (filter 5–50 ha), `planting_year`
2. **Post-monsoon NDVI time series per patch** — typically an Oct–No
- **judge:** winner=B · site_specific=B · data_grounded=B · B_hallucinated=False · _B correctly refused to rank nonexistent 5–50 ha planting blocks and explained the data gap, while A mislabeled ~2700 ha grid-cell annual slopes as restoration-patch post-monsoon outcomes._

