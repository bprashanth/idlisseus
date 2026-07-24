# Data strategies (the toolbox)

The reusable strategies we employ to fight AOI data-scarcity. Each: **what it is**, **when to use
it**, the **EBTL example**, and **where the code is**. Keep adding as we find more.

---

## 1. Corpus building — crawl papers/datasets for the AOI
Layered crawl, each hop widening coverage:
- **Curated community** — a clean, high-signal source (NCF's Zenodo community) as the seed.
- **Author-graph crawl** — for each dataset's authors, pull their *other* datasets; co-authors
  surface via shared work. Grows the corpus along the people who study the region.
- **Broad theme keyword search, RETARGETED to the AOI's ecoregion** — the key lesson: generic
  "Western Ghats" pulls the wet-forest bias; for EBTL we retargeted to dry-Deccan places
  (Bandipur/BRT/Mudumalai/Cauvery) + themes (Prosopis/Senna, elephant-corridor, dry-deciduous).
- **Authenticated ("login") sources** — Dryad (OAuth), eBird (key). Pattern: creds outside the repo,
  a connector that logs in. (See §7.)
- **Messy-file parsing** — xlsx/zip, and **relational joins** (values in one file, coords in another,
  keyed by plot id needing key-normalization).
- **Catalog everything** — keep a card for every inspected study even if it yields no points.
**EBTL:** 17→256 datasets. **Honest limit:** open repos are structurally thin for a dry-deciduous
site → don't expect the crawl to fill the gap; it feeds the *card* corpus + transfer, not dense
in-AOI points. **Code:** `benchmarks/algebra/research/paper_crawl.py`, `connectors/paper_data.py`.

## 2. Paper search & document embeddings (the discovery layer)
Make **buried** data findable: a study about wildfire may hold a `prosopis` presence column.
**Data card** per study = title + all columns + **codebook column-definitions** + value-types/species.
Retrieve: keyword pre-filter → **embeddings (bge-small) top-k** → **LLM re-rank**. Finding: one-prompt
LLM-over-cards wins at tiny corpora but **degrades as the corpus grows**; embeddings/hybrid are
scale-robust (~0.91 semantic recall@3). **Code:** `benchmarks/algebra/discovery/`.

## 3. Axis of maximum data reliance (the abundant-dataset bridge)
Anchor the answer in whatever data type is MOST abundant for the AOI, and bridge to the question via
**known ecology**. Don't hardcode which is abundant — census it (§Step 2).
**EBTL:** birds are abundant (136 eBird species) → `ebird.frugivore_dispersers` finds **11 Lantana-
dispersing frugivores** present → a mechanistic invasive-spread + connectivity signal *even with 0
plant records*. Also: keystone/indicator birds → biodiversity health; bird movement → corridors.
Then fill missing fields ourselves (eBird has no habitat field → annotate bird points with landcover)
and **ask** for the confirming data. **Code:** `ebird.py`, `indicators.py`, PLAYBOOK "abundant-dataset hook".

## 4. Transfer & interpolate algebra
Carry analog data into a data-poor AOI, honestly. Three notions of "similar", each its own gate:
- **Looks-alike** (AlphaEarth 64-d embedding, nearest-neighbour, calibrated vs training's own
  tightness) → **RF transfer** (fine, local, does NOT cross ecoregions).
- **Same climate** (WorldClim bioclim envelope, MESS) → **SDM** (coarse, CAN cross ecoregions within
  the trained climate range).
- **Same ecoregion** (a coarse categorical pre-filter).
`gate(train, aoi)` reports these; `route(question, aoi)` picks **overlap / transfer_rf / sdm_climate /
refuse** and classifies the SITUATION → *answerable* / *need-more-data (data gap)* / *need-better-
models (methods disagree)*. Interpolation (IDW for near-surrounding points) is the pending 4th method.
**EBTL:** dry-Deccan Lantana → EBTL = transfer valid (climate envelope covers it); wet-Valparai →
EBTL = refuse. SDM fed by pooled GBIF + camera-trap occurrence. **Code:** `predict.py` (gate,
sdm_climate, transfer, route), `TRANSFER_ALGEBRA.md`. **Perf:** covariate cache so it's fast.

## 5. Satellite & hyperspectral
- **AlphaEarth Satellite Embedding** (64-d/yr, 10 m) — general appearance/structure fingerprint;
  the RF-transfer covariate + the analog metric.
- **EMIT hyperspectral** (285 bands, 60 m) — material/chemistry; separates invasives (Lantana) from
  native scrub where general appearance can't, but coarse (a "likely-heavy" hint, not crisp mapping).
- **Higher-res HS (Pixxel ~5 m)** — the *ask* for patch-scale invasive/canopy-chemistry mapping.
- **Explain disagreements per channel** — if HS points at something AlphaEarth doesn't correlate with,
  break it down to specific reflectance channels and build an explanation rather than hand-wave.
**Code:** `hyperspectral.py`, `embedding.py`, `predict.py`; asks in `DATA_GAPS.md`.

## 6. Question-type routing (match method to question)
- **Spatial value** (canopy/pH/biomass) → RF/AlphaEarth if analog, else refuse/collect.
- **Species suitability/presence** → SDM(climate) + occurrence.
- **Trend** (closer/greener over time) → occurrence-by-year + distance, greenness trend.
- **Human-use / livelihood** (firewood, grazing, who-does-what) → satellites can't see behaviour:
  give the observable PROXY (greenness/landcover near settlements) + honest limit + community-data ask;
  do NOT force species modelling (that was our 2 benchmark losses).
- **Robustness rule:** never return empty; retry once smaller, then answer from data-on-hand + ecology.
**Code:** PLAYBOOK skill.

## 7. Requests for data (turn gaps into asks) + authenticated sources
Every scarcity becomes a **specific acquirable ask**, ideally startable today: Pixxel HS, acoustic
bird hardware (AudioMoth+BirdNET), eBird habitat logging, targeted taxon surveys (dung-beetle pitfall
traps), community/household surveys for human-use. Authenticated sources follow the **login-connector**
pattern (creds outside the repo; a `configured()` check; loud warning if missing). **Code:**
`ebtl/DATA_GAPS.md`, `ROADBLOCKS.md`, `research/DRYAD_SETUP.md`, `ebird.py`, preflight `preflight.py`.

---

### The meta-loop
For a data-starved AOI: **census → (transfer what's analog) + (ingest what's crawlable) + (bridge
from the abundant axis toward the scarce) → answer honestly → request the rest.** Repeat as data arrives.
