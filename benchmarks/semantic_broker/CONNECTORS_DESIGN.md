# Connectors — design (the insights layer)

Motivated directly by v-1 ([`EXPERIMENT_v-1.md`](EXPERIMENT_v-1.md)). Raw Hermes
*found* the right data but failed to *analyse* it: Q5 invented the WorldCover
legend (class 50 = "Shrubland" — it's Built-up), Q1 spent ~25 min fighting the
Earth Engine `reduceRegion` API and never completed the per-site fire join. So
the agent should **never write raw Earth Engine reducer code** and should **never
guess a legend or band name**. Connectors own both.

## The one pattern: points → annotate → group

Every benchmark question reduces to the same shape:

```
1. get POINTS         from an asset CSV (lat/lon cols) or occurrence.search()
2. ANNOTATE points    add a column: landcover, fire_count, elevation, in_pa
3. GROUP / RANK        plain pandas — the agent is good at this
```

The hard, error-prone middle step (step 2) is what connectors provide as
**point-annotators**: a function that takes a table of points and returns the
same table with one new, correctly-labelled column. No EE objects ever cross the
boundary — connectors return plain CSV/JSON. This is the whole trick: it turns
"write a correct EE reduction" (which the agent can't) into "call
`fire.exposure(points)`" (which it can), and then group with pandas (which it's
good at).

## Connector list (v1 — the six that cover all 5 benchmark questions)

Connector **per source**, not per asset. Legends / band names / dataset IDs are
hardcoded *and* verified inside the connector, and emitted by `describe()`.

| Connector | Source | Key functions | Fixes |
|-----------|--------|---------------|-------|
| `landcover` | ESA WorldCover v200 (EE) | `classify(points)→+landcover` (name); `area_by_class(aoi)` | Q5 legend guess |
| `fire` | MODIS MOD14A1 / FIRMS (EE) | `exposure(points, radius_km, years)→+fire_count,+fire_density`; `points(aoi, years)` | Q1 reduceRegion failure |
| `terrain` | SRTM (EE) | `at(points)→+elevation,+slope,+aspect` | (fire-risk covariate) |
| `protected_areas` | WDPA (EE `WCMC/WDPA`) | `contains(points)→+pa_name,+in_pa`; `boundaries(aoi)` | Q4 |
| `occurrence` | GBIF API | `search(species, aoi)→points`; `species(aoi)` | Q2, Q3 |
| `geo` (helper) | pure python (shapely) | `within(points, polys)`; `nearest(a,b)→+dist`; `buffer_count(points, others, km)` | the joins the agent hand-rolled |

`occurrence.search` and asset CSVs are the two ways to *produce* points; the other
four are annotators that *consume* points. `geo` is the glue for asset-to-asset
joins (e.g. lantana points ↔ plantation polygons) that don't need a live API.

## Contract every connector obeys

- **Python + CLI, same surface.** `from connectors import fire; fire.exposure(df, ...)`
  and `python -m connectors.fire exposure --points sites.csv --radius-km 5 --years 2020-2025`.
- **Points in / points out.** Input: a CSV/DataFrame with `lat`,`lon` (+ optional
  `id`). Output: the same rows with new columns. Never returns an EE object.
- **Self-describing.** `connector.describe()` / `python -m connectors.fire --describe`
  emits: purpose, dataset ID(s), band name(s), the full legend, function
  signatures, one example, and known gotchas. This is the "embed the API to
  discover the legend" the design calls for — the agent can query it at runtime
  instead of guessing.
- **Metadata is owned, not guessed.** WorldCover legend, MOD14A1 `FireMask`
  values (3=fire, 4–5=hotspot), WDPA name field — hardcoded and verified once.
- **EE init is internal.** The connector calls `ee.Initialize(project="plantwars")`
  itself; the agent never touches `ee`.
- **Errors are structured**, not tracebacks: `{"error": "...", "hint": "..."}`.

## How the agent goes from search results → insight (all 5 Qs)

The broker (or, for now, the hardcoded finding step) hands the agent: the relevant
**asset paths** + the relevant **connector names + the exact call to make**. Each
question is then ~3–5 tool calls with zero EE code:

**Q1 — restoration sites most fire-exposed**
```
sites = read_csv(ncf_zenodo/10077040/01_sites.csv)         # lat/lon from the card
sites = fire.exposure(sites, radius_km=5, years="2020-2025")  # +fire_count
sites = landcover.classify(sites)                           # +landcover (context)
rank sites by fire_count                                     # pandas
```
(Q1 failed here purely because it hand-wrote the fire reduction. `fire.exposure`
is that reduction, done correctly, once.)

**Q5 — fire risk: scrub vs plantation**
```
pts   = fire.points(aoi, years="2020-2025")                 # fire locations
pts   = landcover.classify(pts)                             # +landcover (CORRECT names)
group by landcover, count → density                         # pandas
```
(No invented classes: `landcover` returns "Shrubland"/"Cropland"; the agent learns
from `describe()` that WorldCover has *no* plantation class and must use the
land-use assets for plantations.)

**Q2 — where to prioritise lantana removal**
```
lant  = occurrence.search("Lantana camara", aoi)           # points
lant  = landcover.classify(lant)                           # which covers have lantana
read Prasad paper (asset) for removal-method evidence
lant  = geo.nearest(lant, cropland_polys)                  # proximity to fields
prioritise high-density lantana near cropland              # pandas
```

**Q4 — invasives inside vs outside protected areas**
```
lant  = occurrence.search("Lantana camara", aoi)
lant  = protected_areas.contains(lant)                     # +in_pa
count inside vs outside                                     # pandas
```

**Q3 — restored plots recovering native species**
```
plots = read_csv(seedling_survival asset)                  # sites + survival
obs   = occurrence.search(aoi=plot_buffers)                # species nearby
join obs↔plots via geo.within; compare to "native" list from Osuri paper
```

In every case the agent's job collapses to: **produce points → annotate →
pandas**. That is a shape a 122B model executes reliably.

## Skill / tool documentation structure (what the agent actually reads)

Two tiers so invocation is generic yet correct:

**Tier 1 — the playbook skill** (`connectors/PLAYBOOK.md`): one short doc, always
in context, teaching the *pattern*, not the specifics:
> To answer a spatial conservation question: (1) get a table of points — from an
> asset CSV's lat/lon columns, or `occurrence.search`; (2) annotate points with
> the relevant connector(s) — `landcover.classify`, `fire.exposure`,
> `terrain.at`, `protected_areas.contains`; (3) group/rank with pandas. **Never
> write Earth Engine code and never guess a class code or band name — call the
> connector, or run its `--describe` to see the legend.**

**Tier 2 — one card per connector** (`connectors/<name>.md`), uniform template:
```
# connector: <name>
purpose:      one line
when to use:  the question shapes it answers
produces/annotates:  POINTS producer | POINT annotator (+columns)
functions:
  - sig → returns
legend/bands: the owned metadata (or "run --describe")
example:      one runnable call
gotchas:      e.g. "WorldCover has no plantation class"
```

The card is also what a broker dataset-card will point at: a retrieved asset card
carries `connector: fire` + `call: fire.exposure(points, radius_km=5)`, so the
finding step spells out the invocation. That is the seam where this connector
layer meets the retrieval layer later (v1+).

## Build order

1. `landcover` — smallest, and fixes the exact Q5 bug (legend). Exemplar for the
   contract. **(building first as proof)**
2. `fire` — unblocks Q1 (the per-site reduction).
3. `protected_areas`, `occurrence`, `terrain`, `geo`.
4. Rerun Q1 and Q5 with the connectors + PLAYBOOK mounted; compare to the raw
   v-1 runs. Success = Q5 gets classes right, Q1 completes a real fire ranking.
