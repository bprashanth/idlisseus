# Generic visual chatbot: agent handoff

Status: active architecture plus future data/UX design.

Last checked: 2026-07-24

This is the shortest handoff for an agent developing a generic visual chatbot for data-intensive
social-sector work. The platform and benchmark workstreams are intentionally independent:

- the platform agent develops conversation UX, visual layouts, drill-down, provenance, audit and
  generic result rendering in Idlisseus;
- benchmark agents acquire data, evolve site packs, connectors, skills, indexes and models in
  their own repositories; and
- both sides meet at versioned pack, capability, result and visual-response contracts.

## Read in this order

1. [`../docs/IDLI_INSIGHT_MODEL_COMPOSITION.md`](../docs/IDLI_INSIGHT_MODEL_COMPOSITION.md)

   Current implemented request path, model responsibilities, session isolation, immutable result
   handles, audit behaviour and runtime invariants.

2. [`SITE_PACK_DEPLOYMENT.md`](SITE_PACK_DEPLOYMENT.md)

   Cross-benchmark ownership boundary; pack and launcher contracts; endpoint-per-site POC; UI,
   bridge and pack start/stop/restart operations.

3. [`../docs/VISUAL_FIRST_AOI_DATA_DESIGN.md`](../docs/VISUAL_FIRST_AOI_DATA_DESIGN.md)

   Future acquisition, bronze/silver/gold/serving pipeline, logical data model, visual-ready
   products, response contract, latency targets, governance and acceptance benchmark.

4. [`../chatbots/index.md`](../chatbots/index.md)

   Existing Idlisseus chat, streaming, document panel, HTML iframe and dashboard capabilities.

5. [`../README.md`](../README.md)

   Current host services, UI path, model inventory and health checks.

Read older files below `dss/connectors/`, `dss/loop/`, and the remaining historical DSS planning
only when implementing or migrating a specific benchmark. They are not generic UI contracts.

## Current versus future

Current:

- Idlisseus is the browser-facing multi-user chat application.
- A registered OpenAI-compatible bridge can run a resumable outer agent loop.
- The bridge can stream safe activity, evidence classes, guided actions, visual/report links and
  audit ids.
- One chat maps to one resumable backend thread.
- The site-pack POC uses one bridge endpoint per benchmark/site configuration.
- Site data and benchmark implementation remain outside Idlisseus.

Future:

- precomputed visual-ready indexes answer common questions without reopening raw files;
- almost every evidence-bearing answer begins with a map, chart, matrix, timeline, network or
  comparable visual;
- every aggregate can drill down to source rows or an explicit disclosure boundary;
- generic renderers consume result contracts rather than benchmark vocabulary;
- a session can eventually bind safely to one of many authorised site packs; and
- visual layouts can evolve without rebuilding benchmark ingestion.

Do not describe the future visual data plane as already wired into live chat.

## Ownership

### Idlisseus owns

- authentication and user/session history;
- model endpoint selection;
- streaming answer and activity presentation;
- evidence/provenance badges and audit access;
- clarification and guided-action components;
- generic map, chart, table, network, dashboard and report containers;
- visual-response validation and safe iframe/asset delivery;
- responsive desktop/mobile layout; and
- accessibility, loading, empty, failure and partial-result states.

### Benchmark repositories own

- organisation and site packs;
- raw source versions, licences and hashes;
- Scout/Miner/Syllabus acquisition output;
- schema adapters and canonical indexes;
- benchmark connectors and skills;
- semantic and structured retrieval indexes;
- model inputs, gates, runs and validation;
- data requests and collection-cost inputs;
- benchmark-specific tests; and
- the bridge launcher/configuration that exposes results to Idlisseus.

### Shared contracts

- organisation/site identity and access scope;
- source and pack manifests;
- immutable result handles and lineage;
- evidence classes;
- capability metadata;
- visual response specifications;
- artifact and drill-down references;
- guided actions valid for a completed result;
- audit and failure envelopes; and
- version/digest invalidation.

## Parallel-development rule

The platform agent should be able to test with synthetic or fixture result contracts. It should
not wait for every benchmark connector or infer benchmark meaning in JavaScript.

Benchmark agents should be able to add sources, entities, measurements, models and skills without
editing Idlisseus. They should test that their outputs satisfy the shared contracts and can be
rendered by generic components.

The only coordinated change should be an explicit, versioned contract change with compatibility
tests on both sides.

## Initial UX implementation target

Build the UI around a small generic set of visual contracts:

- AOI or named-place map;
- observed point/cell coverage map;
- coverage plus effort/exposure map;
- time series with coverage strip;
- comparable group panels with denominators;
- entity hierarchy;
- relationship map/network/matrix with disclosed join rule;
- donor/target/gate/model layer map;
- expected-value or data-request map;
- source coverage and audit dashboard; and
- source-row drill-down table.

Each contract must render observed, reported, proxy, modelled, designed and missing classes
distinctly. A failed gate or partial source should leave the valid observed-data visual usable.

## Integration acceptance

A generic implementation is ready for a new benchmark when:

1. the benchmark can add a site pack without changing Idlisseus source;
2. the UI can render fixture and real results through the same visual contract;
3. a site endpoint can be started, stopped and restarted independently;
4. no site data are copied into the Idlisseus repository;
5. visuals drill down to source rows or a disclosed boundary;
6. evidence classes and limitations survive every transformation;
7. mobile and desktop layouts remain usable during streaming and partial results;
8. endpoint, pack and result digests are visible in operator audit;
9. cross-site leakage tests pass; and
10. benchmark and UI work can continue in separate commits and repositories.
