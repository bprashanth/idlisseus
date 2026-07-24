# The regression suite + the fixed baseline

The discipline (from `HISTORY.md` P9): **benchmarks surface areas to improve; the regression suite protects
discipline while you implement them.** A code change is only allowed to ship if the golden-trace suite still
passes. This doc defines (a) the fixed **baseline** every feature benchmark measures against, and (b) the
**golden traces** — canonical questions with behavioral assertions that must hold after every change.

## The baseline (freeze this — every `docs/benchmarks/*` measures against it)
- **Backend:** `chat.sh --model deepseekv4` (batches tool calls; the everyday model per `MODEL_OPTIONS.md`).
- **Stack:** current `dss/connectors/PLAYBOOK.md` constitution + `recipes/` + the `discipline` plugin
  (`_CAP=12`, model-conditional parallelism) + `discovery` wired + neutral `SOUL.md`.
- **Site:** EBTL (`SITE_EBTL.json`). Fresh session per scenario (`HERMES_SOURCE`), `AUTO_APPROVE=1`.
- Record backend + git SHA in every result file so a number is always attributable.

A feature "wins" and may be integrated only if: **(1)** it beats this baseline on its benchmark's metric,
**AND (2)** the golden suite below still passes. Both, or it doesn't ship.

### Baseline snapshot (2026-07-12, `golden --run --model deepseekv4`, 5 golden scenarios)
**Green on all correctness dimensions** — clarify (asked on `invasives_vague`, did NOT over-clarify the
answerable `forest_recovery`), name-resolve (`green_cat_snake` → *Boiga cyanea*), observed-vs-modelled flag,
papers-first — across all 5. **One standing flag:** `uropeltis_tax` (a taxonomy answer at 1857 chars > the
1600 "short" bar). The **"short" bar = 1600 chars** (a lead finding + numbers + a small table + follow-ups
runs to ~1550; beyond is an essay). The gate rule going forward: a change ships if it introduces **no NEW**
golden failure vs this baseline; the standing `uropeltis_tax` length gets retired by the brevity/discipline
work, not treated as a fresh regression.

## Golden traces — behavioral assertions (not answer text)
Behavioral, because scoring only *content* misses the regressions that actually hurt (stopped asking,
started writing essays, stopped transferring). Signals are mined from the `state.db` trace.

| # | Canonical question | Must-hold assertions |
|---|---|---|
| G1 | "tell me about the invasives / snakes here" (vague) | **asked** which one / what goal — did NOT assume · short |
| G2 | "where can I find the green cat snake near here?" | resolved name → **Boiga cyanea** (not free-association) · produced a **transfer/map** (not one point) · flagged **modelled** |
| G3 | "tell me about EBTL" | **site-known** (no re-derivation / no search-for-what-EBTL-is) · short · offered 1–3 follow-ups |
| G4 | "is Lantana spreading here?" (records mostly outside AOI) | did the **transfer**, said **modelled**, pushed for field data · respected a gate REFUSE if the analog fails |
| G5 | "what data exists on X" (literature) | called **`discovery`** FIRST (semantic), not keyword-fumbling · pulled **points from datasets**, not just titles |
| G6 | "which birds tell me the forest is healthy?" (change/health) | used a proxy + **bioindicator survey ask** · did NOT force a distribution model |
| G7 | every scenario | **not empty** (retried smaller then answered) · **short** (no thesis) · **observed-vs-modelled labelled** |
| G8 | **multi-turn** (3 turns): vague ask → user gives direction → "is that reliable / where exactly?" | invariants **hold across ALL turns, not just turn 1**: site-known every turn (no re-derivation mid-conversation) · **clarified ONCE** (turn 1) then proceeded — no re-clarify loop · short every turn · observed-vs-modelled label **persists** on turns 2–3 · did not drift into an essay as the thread grew |

G2 + G7 are already asserted by `benchmarks/place_memory_run/conv_bench.py golden` (green_cat_snake
resolves + flags modelled; short; not_empty). This suite **extends** that to G1/G3–G6, and **G8 is the
cross-turn invariant guard** — the most common decay mode is the constitution holding on turn 1 then
eroding (re-deriving the site, dropping the "modelled" label, writing essays) as the conversation
continues. G8 runs the multi-turn harness (`conv_bench.py`, user-simulator) and asserts the invariants on
**every** turn's trace, not just the first.

## How it runs (two-tier, new-vs-old)
Harness = `benchmarks/place_memory_run/conv_bench.py` (multi-turn, user-simulator). `golden --run --model M`
RE-RUNS the golden subset fresh (the real guard) and compares to a saved reference
(`results_base.ref.jsonl` = the "old" baseline). Two tiers, because they behave differently run-to-run:
- **HARD (must not regress vs ref) — correctness:** resolved-name, observed-vs-modelled flag, clarify-
  appropriately (ask the vague, don't over-clarify the answerable), papers-first, **not-empty/not-crashed**.
  These are STABLE across runs; a new failure here is a real bug and **blocks** the change.
- **SOFT (reported, not a hard block) — brevity:** deepseek answer length swings ~800 chars run-to-run
  (proven: `lakes` 872 vs 1760 chars on *identical* code), so a single-sample hard 1600 bar FLAPS. Per-
  scenario length is reported as a warning; only a **SYSTEMATIC** bloat (suite mean max-length up >25% vs
  ref) hard-fails. This catches real verbosity regressions without flapping on variance.
- **Update the ref** (`cp results_base.jsonl results_base.ref.jsonl`) after a change lands green, so the
  next feature compares against the new floor. Standing `uropeltis_tax` length is a soft warning, not a block.
- **Cadence/cost:** run `golden --run` before and after every feature integration; ≈13 min on deepseekv4.

## The miner side (human-gated)
After each benchmark, mine the interesting sessions (signal-gated: user pushback, repeated question,
empty/short turn, an entity never verified, a "where" that produced no map — see
`agents/hermes/TRACE_INTROSPECTION.md`), cluster recurring failures, and **propose** a layered edit
(constitution rule / recipe / connector guard / skill) to a review file. **Propose, don't auto-apply** —
auto-curation has persisted wrong facts before. Approve → apply → re-run the offending G-scenarios → confirm
the metric moved. Automating this trigger is itself a v2 job (`docs/benchmarks/improvement-loop.md`).
