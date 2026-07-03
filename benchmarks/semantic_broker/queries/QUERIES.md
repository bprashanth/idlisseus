# Query set (connector-focused)

Realistic conservation queries for testing the **connector/insights layer**. The
**data-finding step is pre-done**: each query's input points live in `data/`, so
Hermes can focus purely on connector usage (annotate → group), which is where
v-1 failed. Gold answers below were produced by running the connector chains
directly (`connectors/`), and double as the reference for grading a Hermes rerun.

Staged inputs (`queries/data/`):
- `restoration_sites.csv` — 26 sites (id, lat, lon, habitat) from Zenodo 10077040.
- `lantana_occurrence.csv` — 250 GBIF *Lantana camara* points in the AOI.

AOI bbox: `76.3,10.2,77.2,11.7` (Anamalai–Nilgiris).

---

### QA — Which restoration sites are most exposed to wildfire?
- **input:** `restoration_sites.csv`
- **chain:** `fire.exposure(sites, radius_km=5, years="2020-2025")` → rank by `fire_count`
- **gold:** top = Akkamalai (19.4), Akkamalai_Iyerpadi (15.2), Iyerpadi-Top (10.1),
  Andiparai (10). **10/26 sites have zero fire** (wet mature rainforest doesn't burn).
- **tests:** the per-site buffer reduction v-1 Q1 could not write. One call now.

### QB — In what land cover does lantana mostly occur here?
- **input:** `lantana_occurrence.csv`
- **chain:** `landcover.classify(lantana)` → group by `landcover`
- **gold:** Tree cover 186 · Built-up 40 · Grassland 17 · Cropland 5 · (wetland/water 1 each).
- **tests:** correct WorldCover legend (names, not guessed codes) — the exact Q5 failure.

### QC — Over what elevation range has lantana invaded?
- **input:** `lantana_occurrence.csv`
- **chain:** `terrain.at(lantana)` → elevation distribution
- **gold:** min 26 m · median 498 m · max 2346 m (a low–mid-elevation invader; high
  points are sparse observations).
- **tests:** point annotation + the agent summarising a distribution.

### QD — Does wildfire concentrate in particular land cover? (Q5 redux)
- **input:** none — `fire.points(aoi)` produces the points
- **chain:** `fire.points(aoi, years="2020-2025")` → `landcover.classify(fire_pts)` → group
- **gold:** only **14 fire points in the whole AOI over 5 years**; Tree cover 7 ·
  Grassland 6 · Cropland 1. Grassland is over-represented vs its ~15% area share.
  **No "Shrubland", no "plantation" class exists** — directly refutes v-1 Q5's
  "898 km² scrub, 470× more fire-prone" (that was Built-up mislabelled).
- **tests:** whether connectors stop the semantic fabrication; also honesty about
  small N (fire is genuinely rare in this wet zone).

### QE — Are lantana records more inside or outside protected areas?
- **input:** `lantana_occurrence.csv`
- **chain:** `protected_areas.contains(lantana)` → count in/out
- **gold:** in_pa = 0/60. **This is a coverage gap, not a real result** — WDPA
  lacks Mudumalai/Anamalai boundaries. The correct "insight" is to **surface the
  limitation** and recommend supplying reserve boundaries (GeoJSON) + `geo.within`,
  NOT to report "0% inside PAs."
- **tests:** does the agent read `--describe` / the coverage warning and disclose
  the limitation instead of fabricating a clean split?

---

## Connectors these queries exercise

`fire`, `landcover`, `terrain`, `occurrence`, `protected_areas` (+`geo` for the
boundary workaround in QE).

## Connectors the query set suggests we still need (roadmap)

Emerged from writing these — build when a query needs them:
- **`greenness`** — NDVI/EVI time series (MODIS/Landsat) for *restoration recovery*
  ("are restored plots greening up?"). The natural next connector.
- **`forest_change`** — Hansen Global Forest Change loss/gain for degradation history.
- **`rainfall`** — CHIRPS, for fire seasonality / drought context (fire is
  rainfall-gated, per the Prasad removal paper).
- **`accessibility`** — settlement/road proximity (GHSL/OSM) for human-pressure
  and "near fields" questions (currently proxied via landcover Built-up/Cropland).
