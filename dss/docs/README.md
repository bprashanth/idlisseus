# dss/docs — the architecture reading order (mirrors heartwood)

The DSS architecture is documented as a set that **mirrors the generalized version** in
`../../heartwood/docs/architecture/memory/` (heartwood = the non-ecological modification of this same
engine). Rather than duplicate content, this index maps the heartwood reading order onto the **existing**
dss docs, and adds only what was genuinely missing (the regression suite + the per-feature benchmark specs).
The rule we hold: **slot into where functionality is already documented; never add a doc that restates one.**

## Reading order (heartwood section → the authoritative dss doc)

| # | Heartwood (general) | dss (ecological, authoritative) | notes |
|---|---|---|---|
| 0 | `README.md` | this file + `../README.md` | entry point |
| 1 | `architecture.md` | [`../ARCHITECTURE.md`](../ARCHITECTURE.md) | 1:1 mirror (constitution · planes · site brain · capability · loop · loading) |
| 2 | `philosophy.md` | [`../PHILOSOPHY.md`](../PHILOSOPHY.md) | scarcity-first, helpful-then-honest, provenance |
| 3 | `algebra.md` | [`../../benchmarks/algebra/TRANSFER_ALGEBRA.md`](../../benchmarks/algebra/TRANSFER_ALGEBRA.md) + `../../benchmarks/semantic_broker/SKILL_ALGEBRA.md` | operation taxonomy + gate/route |
| 4 | `capabilities.md` | [`../connectors/PHILOSOPHY.md`](../connectors/PHILOSOPHY.md) + [`../DATA_STRATEGIES.md`](../DATA_STRATEGIES.md) + [`../loop/README.md`](../loop/README.md) + [`../corpus/README.md`](../corpus/README.md) | connectors · discovery/cards · loop |
| 5 | `improvement-loop.md` | [`REGRESSION_SUITE.md`](REGRESSION_SUITE.md) + [`../loop/README.md`](../loop/README.md) + [`../../agents/hermes/TRACE_INTROSPECTION.md`](../../agents/hermes/TRACE_INTROSPECTION.md) | curriculum → bench → golden → miner |
| 6 | `onboarding.md` | [`../AOI_ONBOARDING.md`](../AOI_ONBOARDING.md) | how a new site joins |

**History & full concept index (dss-specific, no heartwood equivalent):**
[`../HISTORY.md`](../HISTORY.md) (why each piece exists, in discovery order) ·
[`../../benchmarks/CONCEPT_MAP.md`](../../benchmarks/CONCEPT_MAP.md) (every doc + its wiring status) ·
[`../PRODUCTION_MOVE_CHECKPOINT.md`](../PRODUCTION_MOVE_CHECKPOINT.md) (current move).

## The improvement machinery (this directory)
- [`REGRESSION_SUITE.md`](REGRESSION_SUITE.md) — the golden-trace suite + the fixed baseline. **Every code
  change must keep this green.**
- [`benchmarks/`](benchmarks/) — one design doc per feature we want to improve (minor ones combined). Each
  says: hypothesis · baseline · metric · harness · pass rule · what integrating the winner looks like.

## Doc disposition — where the content of each benchmark-dir doc now lives
So the scattered set collapses into the cohesive narrative without deleting the evidence. **KEEP** = stays
as benchmark evidence; **CAPTURED** = its concept is folded into the dss doc named.

| Source doc(s) | Disposition |
|---|---|
| `semantic_broker/VISION.md`, `NOTES.md` | CAPTURED → `HISTORY.md` P1-4 + `ARCHITECTURE.md`; functions-vs-cards stays an open Q → `benchmarks/retrieval-onboarding.md` |
| `semantic_broker/SKILL_ALGEBRA.md` | authoritative for §3 algebra buckets + verify lens (linked from `ARCHITECTURE.md`) — KEEP |
| `semantic_broker/LIMITATIONS.md` (L1–L6) | CAPTURED as gaps → `ARCHITECTURE.md` status table + `benchmarks/correctness-routing.md` — KEEP as evidence |
| `algebra/TRANSFER_ALGEBRA.md` | authoritative `algebra.md` mirror — KEEP |
| `algebra/NOTES.md`, `research/RESEARCH_AUTOLOOP_PLAN.md` | CAPTURED → `HISTORY.md` P3 + `improvement-loop` machinery; loop code now `dss/loop/` — KEEP |
| `algebra/NEXT_STEPS.md` | CAPTURED → the benchmark specs + task list (checkpoint) |
| `algebra/MASTER_PLAN.md` | the north star + running log — KEEP (updated) |
| `eastern_ghats_run/REPORT.md`, `SMART_SPLIT.md` | CAPTURED (skill-is-moat, planner-buys-nothing, smart-bookends) → `HISTORY.md` P8 + `benchmarks/model-positioning.md` — KEEP |
| `place_memory_run/REPORT.md` | CAPTURED (mechanism>gate, golden gate) → `HISTORY.md` P9 + `REGRESSION_SUITE.md` — KEEP |
| `night_run/*`, `invasive_skill/*`, `experiments/{EBTL_LIVE_MAP,INVASIVE_MAP_BENCHMARK}.md` | KEEP as evidence; concepts indexed in `CONCEPT_MAP.md` (front-end/invasive are out of the current v2 scope) |
| `benchmark1–4/*` (harness shootout) | CAPTURED → `HISTORY.md` P1 + `agents/index.md` — KEEP |

*If a piece isn't captured here or in `CONCEPT_MAP.md`, that's a doc-review miss — add it, don't recreate a
parallel narrative.*
