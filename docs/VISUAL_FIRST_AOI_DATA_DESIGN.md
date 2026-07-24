# Visual-first AOI data design

Status: **future design; not implemented in the chat product**

Feasibility prototype: implemented for the first site pack, but not connected to the live
Idlisseus response path.

Last updated: 2026-07-24

## Purpose

This design prepares place-based programme data so that most questions can be answered with a map,
chart, matrix, timeline, network, or other visual before a long textual explanation is generated.
It is intended for social-sector programmes where presence, location, coverage, change,
relationships, and visible trends are central.

The main design decision is to do expensive interpretation and reshaping at onboarding and update
time. A chat turn should usually select and filter an existing visual-ready view, not reopen a
collection of spreadsheets and improvise a new analysis.

This document designs the data plane, acquisition process, indexes, model-result contracts, and
tests needed for that behaviour. It intentionally does not choose the final screen layout or
depend on a particular language model, planner, or scientific notation.

## Product promise

For an onboarded area of interest (AOI):

- “Tell me about this place” starts with the place on a map and the strongest available spatial
  patterns.
- “Tell me about place A” resolves and highlights place A, not merely text-matches its name.
- A presence question starts with observed points or coverage cells.
- A time question starts with a time series or time-enabled map.
- A comparison starts with comparable panels and disclosed denominators.
- A relationship question starts with a map, network, or matrix showing what was actually joined.
- A transfer question starts with donor observations, target AOI, gate status, and any modelled
  surface as separate layers.
- A data-gap question starts with where information exists and, when supported, where another
  measurement has the greatest expected value.

Short text should explain the visual, its limits, and the next useful choice. It should not be the
primary carrier of evidence.

## Non-negotiable invariants

1. Observed, reported, proxy, modelled, designed, and missing values remain distinct data classes.
2. A local source non-match is not absence.
3. Absence and rate claims require an effort or exposure denominator.
4. A trend requires comparable time support; a sequence of anecdotes is not a trend.
5. A map of observations remains useful even when a model gate fails.
6. Model surfaces never overwrite observed points.
7. Every aggregate drills down to source records or an explicit disclosure boundary.
8. Every modelled cell links to a model run, input snapshot hashes, gates, and validation summary.
9. Embedding similarity finds candidate resources; it does not perform numeric, temporal, or
   spatial analysis.
10. Sensitive coordinates and restricted records are filtered before visual materialisation, not
    merely hidden by browser styling.

## What gets onboarded

The durable unit is an organisation profile with one or more AOIs and a resource pack:

```text
organisation
├── profile and access policy
├── AOIs, named places, boundaries and geometry roles
├── source registry and immutable source versions
├── entity registry, aliases and hierarchies
├── events, observations and reported facts
├── effort, exposure and sampling frames
├── measurements and interventions
├── documents, extracted methods and measured claims
├── spatial and temporal feature layers
├── model registry, model runs and gates
├── data requests and collection costs
└── visual views, tiles, summaries and provenance
```

An organisation can seed any subset. Missing planes are explicit coverage gaps and disable only
the views that require them.

## Acquisition: scout, miner, syllabus

Onboarding should be a repeatable acquisition programme rather than a one-off scrape.

### 1. Establish the AOI and decision context

Collect:

- target boundaries and named sub-places;
- wider context, comparison, and allowed donor regions;
- geometry meaning, such as parcel, programme boundary, administrative unit, study envelope, or
  approximate point;
- the organisation's recurrent decisions and reporting obligations;
- coordinate-sensitivity and access policies; and
- an initial question syllabus in the language staff actually use.

Do not silently promote a study bounding box or centre point to a property boundary.

### 2. Scout candidate sources

The Scout searches breadth-first across:

- organisation-provided files, databases, forms, maps, and reports;
- public repositories and catalogues;
- admitted live APIs;
- author, institution, project, citation, and related-dataset graphs;
- remote or administrative layers relevant to the AOI;
- existing dashboards and publication supplements; and
- previous site-pack source registries.

Scout output is a candidate registry, not admitted data. Each candidate records title, source,
stable identifier, spatial and temporal claims, access path, probable file types, licence,
publisher, and why it may answer a syllabus question.

### 3. Mine actual files and interfaces

The Miner opens each candidate and records:

- exact files, tables, sheets and archive members;
- headers, data types, units, codebooks and value examples;
- coordinate, boundary, time, entity and intervention fields;
- join keys and relationships between files;
- sampling or exposure fields;
- missing-value and precision conventions;
- version, checksum, licence and redistribution terms;
- whether rows are observations, reports, aggregates, model outputs, protocols, or metadata; and
- parse failures, ambiguity and suspected quality problems.

The Miner must inspect the real payload. Abstract text or repository metadata cannot substitute
for the table needed by a visual.

### 4. Use the syllabus to measure coverage

The Syllabus maps representative questions to required data planes and first visuals. For example:

| Question class | Required planes | Default first visual |
|---|---|---|
| Place orientation | AOI, named places, source/event coverage | AOI map with coverage hotspots |
| Presence | entity aliases, events, spatial cells | observed points or density map |
| Presence versus search effort | events, effort/exposure | dual-layer coverage map |
| Trend | comparable measurements, time buckets | time series with coverage strip |
| Comparison | common outcome, groups, denominators | aligned panels or interval chart |
| Relationship | two admitted inputs and a join rule | map, network, flow, or matrix |
| Hierarchy | entity registry and hierarchy | tree, sunburst, or treemap |
| Transfer | donor rows, target AOI, features, gates | donor/target/gate map |
| Data request | uncertainty, candidate actions, cost | expected-value map |

Coverage is a matrix of question classes × places × time × entities × required planes. It guides
the next acquisition pass and prevents a large document corpus from masquerading as analysis-ready
coverage.

### 5. Admit, quarantine, or reject

A source is admitted only when its identity, version, rights, scope, and usable payload are known.
Candidate sources with unclear rights, broken files, unresolvable units, or uncertain geography
remain quarantined. A source can be admitted for semantic discovery while its tables remain
unavailable for computation; those are separate capabilities.

## Processing layers

Use an immutable, staged pipeline:

```text
raw source (bronze)
  -> typed and source-faithful tables (silver)
  -> cross-source canonical dimensions and facts (gold)
  -> multi-resolution aggregates, tiles and visual views (serving)
```

### Bronze: preserve the source

Store the exact downloaded or supplied files, source metadata, content hash, acquisition time,
licence, and adapter version. Never edit source files in place. New upstream content is a new
source version.

### Silver: type without changing meaning

Parse tables and geometry, normalise encodings and nulls, attach units, and retain original column
names and row locators. Convert coordinates to a declared reference system while preserving the
verbatim coordinates and uncertainty.

Do not merge names, infer absence, or calculate cross-source trends at this layer.

### Gold: canonical dimensions and facts

Resolve explicit crosswalks and construct the common analytical planes below. Every gold record
retains source id, source version, source row, adapter version, and transform hash.

### Serving: visual-ready products

Materialise the common groupings, tiles, summaries, and visual contracts. Serving products are
disposable and reproducible from gold tables. They can be rebuilt when an AOI, privacy rule, source,
or model changes.

## Core logical data model

The production physical store can change, but these logical tables should remain stable.

### `sources`

One row per immutable source version:

```text
source_id, version_id, title, publisher, stable_identifier, url,
licence, acquired_at, content_hash, spatial_claim, temporal_claim,
access_class, capabilities, adapter_version
```

Capabilities are explicit: `semantic_searchable`, `inspectable`, `mappable`,
`has_effort`, `has_measurements`, `eligible_as_model_input`, and so on. UI actions and agent tools
must be derived from capabilities, not guessed from the presence of a DOI or filename.

### `aois` and `locations`

Store target, context, donor, comparison, administrative, and restricted geometries with an
explicit `geometry_role`. Named points, routes, plots, facilities, villages, and programme sites
belong in `locations`, with aliases and coordinate uncertainty.

Precompute:

- containment across registered AOIs;
- distance to important named locations;
- a hierarchy of AOI → sub-place → plot/route/point; and
- stable display bounds at several zoom levels.

### `entities`, `entity_aliases`, and `entity_hierarchy`

Any repeated subject belongs in the entity dimension: people, organisations, services, assets,
species, crops, diseases, hazards, interventions, or indicators.

Store:

```text
entity_id, canonical_name, display_name, entity_type, rank,
parent_entity_id, valid_from, valid_to, resolver, resolver_version
```

Aliases retain language, source and date. Never discard the source's original label. Resolution
must support “resolved”, “ambiguous”, “unresolved”, and “broader-than-canonical” states; broad
labels should not be silently treated as precise entities.

### `events`

One row per source-linked event or presence record:

```text
event_id, source_id, source_row, entity_id, event_type, evidence_class,
status, event_time, location_id, geometry, coordinate_uncertainty,
count_value, count_unit, method_id, effort_id, properties
```

This table supports immediate point maps, spatial density, time filters, named-place drill-down,
and entity timelines.

### `effort` and `exposure`

Keep where people looked, how long, how far, what protocol they used, eligibility, population at
risk, or other denominators separate from events:

```text
effort_id, source_id, method_id, time, geometry, duration,
distance, visits, eligible_population, completeness, properties
```

These records enable rates, comparable non-detection displays, coverage gaps, and bias maps.
Without them, the product may show presence and source coverage but not absence or risk rates.

### `measurements`

Use a tidy metric plane:

```text
measurement_id, source_id, entity_id, location_id, time,
metric_id, value, unit, uncertainty, method_id, quality_flags
```

Units and aggregation semantics belong in a metric registry. A monthly sum and daily mean cannot
be combined because they share a label.

### `interventions`

Store intervention identity, geometry, start/end time, intended mechanism, implementer, intensity,
comparison group, and source. Intervention dates make before/after visuals possible; they do not
by themselves establish effect.

### `documents`, `passages`, `methods`, and `claims`

Index documents semantically for discovery, but extract useful structured objects:

- methods with population, sampling design, variables and units;
- datasheet fields and codebook definitions;
- measured claims with outcome, direction, estimate, uncertainty, population, geography, time and
  exact source locator; and
- links from claims to downloadable tables when present.

Model memory can propose a search phrase. Only source-linked structured claims can become a paper
trend, comparison, or protocol visual.

### `spatial_cells` and the feature cube

Create a common multi-resolution grid over target and allowed context regions. H3 or S2 cells are
appropriate for vector facts; raster layers retain their native grid and publish aligned
summaries.

For each cell and time slice, materialise:

```text
cell_id, resolution, geometry, aoi_roles, time_bucket,
feature_id, value, unit, source_id, source_version,
method, uncertainty, quality_flags
```

The feature cube may hold remote measurements, terrain, access, land use, population, services,
weather, administrative indicators, or programme-specific covariates. Feature definitions and
versions are part of the model contract.

### `model_registry`, `model_runs`, and `gate_results`

Models are versioned data products:

```text
model_id, version, outcome, supported_entity_types, required_features,
minimum_sample, allowed_transfer, validation_contract, output_contract
```

Each run records:

```text
run_id, model_version, input_snapshot_hashes, donor_scope, target_scope,
features, training_rows, holdout_rows, gates, metrics, calibration,
created_at, output_surface_id, limitations
```

Outputs are cell-valued surfaces or entity/location estimates with uncertainty. Observed inputs,
modelled outputs, and designed collection points are different layers with different legends.

### `data_requests`

A structured request records the missing response, target scope, time, desired precision, candidate
predictors, labels, validation target, allowed collection methods, safety/access constraints, and
owner. When a model and uncertainty surface exist, attach candidate actions and their expected
information gain.

## Precomputed visual products

Do not pre-render one chart per possible natural-language question. Precompute composable data
products that cover recurring visual grammar.

### Spatial products

- simplified AOI and location geometry by zoom;
- point clusters and multi-resolution event counts;
- distinct-entity richness/count by cell;
- source coverage and freshness by cell;
- explicit effort/exposure by cell;
- event-to-effort rates only where denominators are valid;
- feature tiles and quantile summaries;
- donor/target/gate layers for completed model runs;
- model surfaces with uncertainty;
- designed points and expected-value surfaces; and
- coordinate-redacted tiles for restricted audiences.

### Temporal products

- day, week, month, quarter and year buckets;
- coverage counts beside every trend;
- metric summaries with unit and aggregation method;
- intervention markers;
- event counts and effort-normalised rates;
- freshness and missing-period strips; and
- source-revision boundaries.

### Entity and relationship products

- entity alias autocomplete and ambiguity sets;
- hierarchy trees and counts by parent;
- entity × place and entity × time matrices;
- source-supported pairs with join distance/time and both denominators;
- co-occurrence tables that retain independent inputs; and
- network edges with relation type, source and confidence class.

### Source and audit products

- source × place × time × entity coverage cube;
- source health and last successful refresh;
- drill-down row locators;
- transformation lineage;
- model input/output lineage; and
- question-class readiness.

## Visual response contract

The data service should return a typed visual bundle, not arbitrary HTML:

```json
{
  "visual_id": "stable-id",
  "visual_type": "map",
  "title": "Records and search effort",
  "scope": {"aoi_ids": ["target"], "time": ["2020-01", "2024-12"]},
  "layers": [
    {"id": "observed", "class": "observed", "data_ref": "tile-or-query-ref"},
    {"id": "effort", "class": "effort", "data_ref": "tile-or-query-ref"}
  ],
  "summary": {"headline": "...", "denominators": {}},
  "provenance": {"source_versions": [], "query_hash": "..."},
  "drilldowns": [{"label": "Open records", "data_ref": "..."}],
  "limitations": [],
  "next_capabilities": ["filter_entity", "filter_time", "run_transfer"]
}
```

The UI can render this contract as a main canvas, side panel, report figure, dashboard card, or
download without changing the underlying analysis.

## Query path

The online path should be short:

```text
user question
  -> resolve current message, AOI, entity, time and analytical intent
  -> choose one registered visual view
  -> bind typed arguments
  -> query materialised tables/tiles
  -> return visual bundle immediately
  -> optionally run slower model or source expansion
  -> update/replace the visual and add a short explanation
```

The language model may interpret the question and choose among declared view capabilities. It
should not fabricate SQL schemas, layer names, source capabilities, or chart values. A trusted
query service validates arguments and enforces access, evidence class, denominators and lineage.

If the question contains two unrelated current requests, split them into separate visual tasks or
ask which one matters first. Never concatenate them into one retrieval string.

## Transfer from data-rich to data-sparse places

Data scarcity should first produce a map of where trusted data do exist. Transfer is a later,
explicit calculation:

```text
target question
  -> observed target and donor coverage
  -> candidate donor snapshots
  -> feature availability
  -> sample, support, similarity and validation gates
  -> model surface if gates pass
  -> observed + modelled + uncertainty layers
  -> precise data request if a gate fails
```

Precompute the feature cube and similarity neighbourhoods because they are reusable across
questions. Precompute model surfaces only for frequent, approved outcomes; build and cache
long-tail runs on demand. Every cached surface is invalidated by source, feature, AOI, model, or
policy version—not by time alone.

## Storage topology

Start with the simplest stack that preserves the contracts:

| Plane | First implementation | Scale-out option |
|---|---|---|
| Raw files | content-addressed filesystem/object directory | S3-compatible object store |
| Typed tabular data | Parquet + DuckDB | warehouse or lakehouse |
| Geometry and operational joins | DuckDB spatial or SQLite prototype | PostgreSQL/PostGIS |
| Raster/feature layers | Cloud-optimised GeoTIFF/Zarr | tiled object store |
| Vector serving | GeoParquet + generated tiles | tile service |
| Semantic discovery | local embedding index with source ids | vector database |
| Metadata and lineage | relational tables | metadata catalogue |
| Cached visual bundles | JSON/object cache keyed by query hash | distributed cache |

Do not place all analysis in a vector database. Embeddings are useful for finding sources,
passages, methods and aliases. Exact filters, joins, distances, time aggregation and model input
selection belong in typed stores.

## Refresh and invalidation

Every connector or organisation upload lands as a candidate source version. A refresh:

1. fetches and hashes content;
2. stops if content is unchanged;
3. mines schema and quality;
4. runs the source adapter into silver tables;
5. rebuilds affected gold partitions;
6. invalidates dependent aggregates, tiles, models and visual bundles;
7. runs source and question-class tests; and
8. promotes the version atomically.

Last-known-good serving products stay available during a failed refresh and retain their retrieval
time. The system must not silently switch to a different source measuring something else.

## Performance budgets

Targets for an onboarded AOI:

- cached orientation visual: under 200 ms at the data service;
- filtered point/density/time view: under 500 ms;
- composed multi-plane view: under 2 seconds;
- first progress event: under 300 ms;
- slower connector/model work: streamed as a separate stage, without hiding the first useful
  visual; and
- visual drill-down: paginated or tiled, never a multi-megabyte chat payload.

Common views should be warmed after each successful build. Query hashes include AOI, entity ids,
time, source versions, evidence classes, privacy policy, view version and model run.

## Privacy, safety and governance

The serving build must support:

- source-level and row-level access classes;
- coordinate masking, aggregation or embargo by entity and audience;
- consent and purpose restrictions;
- licence-compatible downloads and attribution;
- removal propagation;
- organisation-owned private layers kept out of public tiles;
- audit of who generated or downloaded restricted views; and
- safety/access constraints in data requests.

The unredacted canonical store is not the default map service.

## Onboarding deliverables

A site is ready for visual-first use when it has:

1. an organisation profile and access policy;
2. target/context/donor geometries with declared roles;
3. a source registry with versions, hashes, rights and capabilities;
4. source adapters and quality reports;
5. entity aliases and unresolved-name queue;
6. event, effort, measurement and location planes where available;
7. a spatial grid and time buckets;
8. a question syllabus and readiness matrix;
9. initial materialised visual views and tiles;
10. model and data-request registries, even if empty;
11. privacy-filtered serving products; and
12. a reproducible build plus regression tests.

## Acceptance benchmark

Use multi-turn, ordinary-language sessions. Score the data system independently of prose quality:

- Did it resolve the intended AOI and current message?
- Was the first useful output visual?
- Did the visual use the correct source versions and evidence classes?
- Could every aggregate drill down?
- Were common/scientific/local aliases resolved without merging ambiguous entities?
- Were broad groups clarified or visualised at the correct hierarchy level?
- Were presence and effort separate?
- Did time visuals disclose coverage and units?
- Did comparisons retain denominators?
- Did relationship visuals disclose the join rule and avoid causal claims?
- Did transfer show donor data and gates before a surface?
- Did failed gates retain an observed-data visual?
- Did data requests identify where collection would help, only when supported?
- Did a source outage preserve the question rather than substitute a different measurement?
- Were common visuals within their latency budgets?

Include source outages, schema changes, mixed coordinate precision, ambiguous aliases, old/new
source versions, restricted rows, empty AOIs, and two adjacent user messages in the regression
bank.

## First-site feasibility result

The maintained first site pack is [`../dss/sites/valparai/`](../dss/sites/valparai/). Its
dependency-light prototype currently:

- ingests seven versioned sources;
- indexes 13,578 events, 229 explicit effort rows and 580 measurements;
- resolves 1,039 aliases into 543 entity records, while retaining unresolved/broad labels;
- joins 3,684 plot records to source coordinates;
- materialises 284 spatial cells;
- produces eight immediately renderable visual contracts;
- builds in roughly 0.4 seconds on the current workstation; and
- answers a filtered entity-to-cell query in under 100 ms.

The prototype deliberately reports two incomplete views. Transfer remains partial until a
versioned feature cube and gate result are onboarded. Expected-value collection mapping remains
blocked until a versioned model run, uncertainty surface and action-cost layer exist. This is the
desired failure mode: prepare and show what is real, and make the missing analytical plane
specific.

## Rollout order

1. Freeze logical schemas and capability metadata after reviewing the first site pack.
2. Add a production DuckDB/Parquet build alongside the dependency-light SQLite proof.
3. Create source adapter conformance tests and a privacy-filtered tile build.
4. Wire the site overview, named-place, observed-point and metric-time views into Idlisseus.
5. Add effort-aware and hierarchy views.
6. Add the feature cube, model-run and gate contracts.
7. Add uncertainty/action-cost products before promising expected-value collection maps.
8. Run the multi-turn benchmark and only then make visual-first the default response policy.
