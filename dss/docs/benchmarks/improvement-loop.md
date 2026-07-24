# Benchmark: closing the self-improvement loop (+ the site ledger)

**Feature (CONCEPT_MAP Blocks H + M, ARCHITECTURE §2 §5).** The expansion loop (scout · proposer ·
controller · miner in `dss/loop/`) runs only as an **offline bootstrap**; the miner→rules and
struggle-detector→write-connector feedback is **manual**. The golden gate **re-checks stored results, it does
not re-run.** And the **LEDGER** (per-site work history, ARCHITECTURE §2) is designed but not built. This is
the highest-value 🔴: make the running agent improve itself without regressing.

- **Hypotheses:**
  1. A `golden --run` mode (execute G1–G7 fresh, then assert) turns "golden pass" into a real guard —
     measured by its ability to **catch a deliberately injected regression** (e.g. revert rule-4) that the
     stored-result check misses.
  2. A **signal-gated miner tick** (auto-select interesting sessions from `state.db`, cluster, propose edits
     to a review file) proposes fixes a human accepts at useful precision (not noise).
  3. A **ledger** (append-only `{ts, question, connectors_run, transfer+gate, points, gaps, artifact}`
     loaded as recent-tail + rolling summary) lets the agent **recall** prior work instead of recomputing —
     measured on a multi-turn scenario that references an earlier turn.
- **Baseline:** current offline loop + `conv_bench.py golden` (stored-result check) + no ledger.
- **Harness:** extend `conv_bench.py` (`golden --run`); `dss/loop/miner.py` over `state.db`; a small ledger
  read/write shim in the control plane.
- **Metrics:** injected-regression catch rate (target: caught); miner proposal precision (accepted/total);
  ledger recall win (turns saved / correct back-reference) on a memory scenario.
- **Pass rule:** ship `golden --run` if it catches the injected regression with no false-block on a clean
  baseline; ship the miner tick if proposal precision clears a human-set bar; ledger ships if it wins the
  recall scenario without lengthening answers (golden G7 stays green).
- **Integrate-if-wins:** `golden --run` into `REGRESSION_SUITE` as the mandatory gate; miner tick as a
  scheduled/after-bench job writing to a review file (human-gated apply); ledger into the site brain +
  `ARCHITECTURE §2`. Independent commits, in that order.
