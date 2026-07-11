# Benchmark: correctness — name-verify, resolver discipline, where→transfer routing, transfer perf

**Feature (CONCEPT_MAP Blocks E + F, `semantic_broker/LIMITATIONS.md` L1/L2/L4).** The correctness cluster —
combined because they share a harness and all gate on the same golden traces:
- **L1** (⚠ highest): the agent resolves a common → scientific name by **free association**, not
  verification (answers confidently about the wrong species).
- **L4:** it sometimes calls `occurrence`/`inaturalist` directly, bypassing the `points` resolver.
- **L2:** a spatial "where can I find X" does **not** reliably route into the transfer/map pipeline
  (returns a point or a list, not a modelled map).
- **Perf:** `predict` retrains the RF **every call** in Earth Engine — no covariate cache / sklearn
  fast-path, so transfer answers are slow.

- **Hypotheses:** (1) a resolver-side **verify step** (one cheap `occurrence.search` or an authority check,
  label unverified otherwise) removes L1 wrong-species answers; (2) a `pre_tool_call` **guard** that blocks
  direct `occurrence`/`inaturalist`-by-name and redirects to `points.get` fixes L4; (3) a router/recipe
  tweak makes "where" → `spatial-where` → transfer/map (fixes L2); (4) a **covariate cache + sklearn
  local path** cuts transfer latency with no accuracy loss.
- **Baseline:** `docs/REGRESSION_SUITE.md` baseline (which currently exhibits L1/L2/L4 on the LIMITATIONS
  trace).
- **Harness:** a small labelled set of common-name → correct-species pairs (incl. the green-cat-snake trap)
  for L1; the golden G2/G4 traces for L2; trace inspection for L4; wall-clock for perf.
- **Metrics:** name-resolution accuracy (%correct or correctly-flagged-unverified); L4 bypass count (→ 0);
  where→map rate (G2/G4); transfer latency (s) at equal RF accuracy.
- **Pass rule:** L1 accuracy up with **zero** confident-wrong on the trap set; L4 bypasses = 0; where→map
  rate up; latency down with ΔAUC ≈ 0. Golden suite green throughout.
- **Integrate-if-wins:** verify-step into `points.py` + the verify-species rule already in PLAYBOOK; L4
  guard into the `discipline` plugin; L2 fix into `PLAYBOOK`/`recipes/spatial-where.md`; perf path into
  `predict.py` (cache dir under `/opt/data/work`). Independent commits (one per limitation).
