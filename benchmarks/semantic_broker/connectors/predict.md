# connector: predict

- **purpose:** Random-Forest prediction from AlphaEarth embeddings (64-d) — train on
  ground truth, predict the pattern where data is missing. The ML/corroboration tool.
- **when to use:** build/corroborate a hypothesis with *modelled* evidence — e.g. train
  on native/invasive/soil clusters at a well-studied site (Bandipur/Nagarahole) and
  predict at a data-poor site (EBTL).
- **produces:** `transfer(train[label],targets)` → predicted_label + test_accuracy;
  `presence(species_points,bbox)` → modelled hotspot fraction + accuracy + top bands.

**functions**
- `gate(train_rows, bbox, year=2023) -> {verdict, why}` — **CALL FIRST.** Two sensors:
  AlphaEarth **NN-analog** (is the AOI spectrally like the training pixels? → is RF/embedding
  transfer valid) + WorldClim **MESS** (is the AOI inside the training *climate* envelope? →
  is climate-SDM valid). verdict ∈ overlap | transfer_rf | sdm_climate | refuse.
- `transfer(train_rows[label], target_rows, year=2023) -> predictions + test_accuracy` (RF+AlphaEarth; LOCAL, cannot cross ecoregions)
- `presence(species_rows, bbox, year=2023) -> modelled_present_fraction + accuracy` (RF+AlphaEarth; LOCAL)
- `sdm(presence_rows, bbox, year=2023) -> climate suitability + aoi_in_climate_envelope_frac`
  (WorldClim bioclim + RF; CAN cross ecoregions within the trained climate envelope). Feed
  from OCCURRENCE (GBIF + camera-trap), e.g. dry-Deccan → EBTL.

**method choice (the two gates fail differently):** RF+AlphaEarth is fine-grained (10 m) but
local — dry EBTL embeddings ≠ wet training, so the analog gate REFUSES wet→dry. Climate SDM is
coarse (~1 km) but crosses ecoregions *within the trained climate envelope* (MESS gate). Pooled
dry-Deccan occurrence makes EBTL in-distribution → `transfer_rf`; wet-Valparai training → `refuse`.

**example**
```
python /opt/data/connectors/predict.py gate --train occ_lantana.csv --bbox 77.4,11.9,78.5,12.9
python /opt/data/connectors/predict.py sdm  --points occ_lantana.csv --bbox 77.4,11.9,78.5,12.9
```

**gotchas:** outputs are **MODELLED, not observed** — always report with the test
accuracy and the SDM caveats (occurrence sampling bias, spatial autocorrelation,
embedding opacity). Corroborative evidence for a hypothesis, never ground truth.
