# Modelling connectors — how `predict` (gate / transfer_rf / sdm_climate / route) actually models

The methodology + honest limits of the transfer/modelling layer, and the roadmap to improve it.
Companion to `predict.md` (interface) and `../../algebra/TRANSFER_ALGEBRA.md` (the framework).

## What runs, and where
- **gate** — pure-Python decision on sampled covariates: AlphaEarth **nearest-neighbour cosine**
  (is the AOI an appearance-analog of the training points?) + WorldClim **MESS** (is the AOI inside
  the training climate envelope?). Cheap; the covariate sampling is cached.
- **transfer_rf** — `ee.Classifier.smileRandomForest` trained **server-side in Earth Engine** on the
  **64-d AlphaEarth embedding** at presence + background points, predicted over the AOI. Local
  (appearance), does not cross ecoregions.
- **sdm_climate** — the SAME RandomForest machinery, but on the **19 WorldClim bioclim bands**.
  "SDM" is generous — it's an RF classifier on climate, not MaxEnt. Crosses ecoregions within the MESS
  envelope.
- **route** — gate → run every valid method → classify the situation (answerable / need-more-data /
  need-better-models). Models are trained **fresh per call**, ephemeral, never pretrained.

## The weak point: ABSENCE / background
GBIF/eBird are **presence-only** — we have no true absence. Both `transfer_rf` and `sdm_climate`
currently use **random background points as pseudo-absence** (`ee.FeatureCollection.randomPoints`,
n≈300–500, over the AOI or the presence extent, labelled 0). This is the standard shortcut but has
real problems:
1. **RF treats presence-vs-background as balanced classification** — output is sensitive to the
   presence:background ratio and the specific background draw; not a clean "suitability".
2. **Uniform random background ignores sampling bias** — GBIF is road/accessibility-biased; random
   background doesn't match that bias, so the model can learn the bias, not the niche.
3. **Random background can be truly suitable** (mislabelled absence), especially for widespread species.

## RF vs MaxEnt — honest take
For **presence-only** data, **MaxEnt** (or a modern infinitely-weighted logistic / point-process model)
is **theoretically better-suited** than RF-with-random-background: it models occurrence intensity
relative to the available background, which is the correct framing. **But two caveats:**
- **Background quality matters more than the algorithm.** The highest-value fix is **target-group
  background** (draw background from where *other* species in the same survey effort were recorded, to
  mimic the same sampling bias) + **spatial thinning** of clustered presences. This helps RF *or* MaxEnt.
- **Practicality:** EE has `smileRandomForest` server-side (no local deps); **EE has no MaxEnt**. MaxEnt
  means pulling covariates to Python + a lib (`elapid`/`maxnet`) — and the Hermes container has no
  numpy/sklearn yet. Heavier integration.

**Roadmap (impact order):** (1) target-group background + spatial thinning, (2) **true absence from
paper plots** (below), (3) MaxEnt/`maxnet` for the presence-only branch if we want it textbook-correct.
Until then, RF stays — always framed as **modelled + gated + caveated**, never authority.

## Experiment: TRUE absence from paper census data
**Idea:** a paper **plot census** records the *complete* species list for a plot — so a species that a
qualifying plot surveyed-for but did NOT record is a **real absence** at that plot's coordinates. That
replaces random background with genuine absence → a much better SDM.

**Conditions a plot must meet to count as a valid absence for target species S:**
1. **Same taxonomic group / community** — the plot must have surveyed S's group (a tree plot gives
   tree absence, not bird absence).
2. **Detectability / stratum match** — the method would have detected S if present (a canopy-tree
   census may miss an understory shrub → not a valid absence for that shrub).
3. **Georeferenced** — the plot has coordinates (directly, or via the relational join in `paper_data`).
4. **Comparable place & (for phenology-sensitive taxa) season/date** to the presence points — so the
   absence is informative for the same environment the presences came from.
5. **S absent from the plot's list** → that coordinate is an absence.

**Quick-check result (our corpus):** **43 plot-census candidate datasets** (species × plot columns),
several georeferenced — e.g. "Plant Community Structure in Tropical Rain Forest" (`plot_no + species +
count`), "Varying impacts of logging frequency on tree communities" (`plot + species_id`, georef),
"Orchards and paddy…" (`plot_id + transect + species`, georef). So the method is viable **now**.
**Caveat:** most are WET Western-Ghats forest → good for *building/validating the method*, but for
EBTL dry-deciduous absences we need dry-Deccan plot censuses (a targeted crawl, or accept analog use
under the gate).

**How it plugs in:** `paper_data` gains an `absence(species, region)` that returns plot coordinates
where qualifying censuses omit the species; `predict.sdm_climate/transfer` take an optional real-absence
set instead of (or blended with) random background. This is the cleanest, most honest SDM upgrade — real
absence beats pseudo-absence, and it's *our* data moat (a plain chatbot can't do this).
