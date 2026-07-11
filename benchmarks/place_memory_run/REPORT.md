# Place-memory conversational bench — report

**Question:** across a connector-spanning, **multi-turn** syllabus, which smart/cheap integration best holds
the **constitution** (know the place · ask-when-unsure · short + follow-ups · observe-vs-modelled+N ·
transfer-and-flag) with **short** answers — and can a **self-improving loop** (mine traces → fix
instructions → golden gate) fix regressions without breaking things?

Setup: `syllabus.json` (13 scenarios spanning name-resolution, papers/litscout, landscape EE
water/landcover/terrain/greenness/s2, colocation/geo, distribution/transfer/invasive, phenology, ebird,
indicators, human-use). `conv_bench.py` runs each **multi-turn** (a user-sim with a hidden goal) through a
config, mines `state.db`, scores constitution adherence + expected-connector hits, and enforces a **golden
regression gate** (green-cat-snake → *Boiga cyanea* + flag-modelled + short + non-empty).

## Config comparison (6-scenario spread)
| config | short | conn_hit | clarified_ok | resolved | papers | delivers real answers? |
|---|---|---|---|---|---|---|
| **qwen** (baseline) | 0.17 | 0.33 | 0.67 | 0.83 | 0.83 | yes, but **theses** (~1800 ch) + mis-routes |
| **bookends** (smart gate+synth) | 1.00 | **0.00** | 0.33 | 0.83 | 1.00 | **often stalls** at the clarify |
| **capnudge v1** (mechanism) | 1.00 | 0.69 | 0.67 | 0.83 | 0.83 | yes — short + routed |
| **capnudge v2** (mechanism, tuned) | 0.67* | 0.45 | 0.83 | **1.00** | **1.00** | yes + golden PASS |

\* the two "not short" v2 answers are 1154 & 1343 ch — good data-backed answers, **not** theses; a
threshold artifact (baseline theses were 1800+).

## Findings
1. **The cheap MECHANISM beats the SMART GATE end-to-end.** `capnudge` (qwen122b + a terse system nudge +
   a hard tool cap — *no smart model*) delivers short, well-routed, real answers. `bookends` (a smart
   clarify-gate + synth) looked great in *isolation* (4/4 clarify) but **end-to-end it over-clarifies**
   (asks even on clear questions) and the multi-turn conversation **stalls at the clarify** (conn_hit 0.00,
   qwen barely runs). Lesson: **don't front the cheap model with a smart gate — nudge it with mechanisms.**
   (Caveat: part of the stall is a user-sim that says DONE instead of answering a clarify; but the
   over-clarification is real and would annoy a user.)
2. **Brevity is a mechanism, not a model.** A terse nudge + tool cap took `short` 0.17 → 1.00 with no smart
   model. The cap's tension: too low truncates (green-cat-snake came back empty at cap 8); high enough to
   finish makes content-rich answers slightly long. **The clean fix is an "answer-now" HOOK** (a
   `pre_tool_call` block-with-message at the budget — lets the model finish a final answer instead of a hard
   `--max-turns` stop). That's the next build.
3. **The self-improving loop worked.** Baseline mining exposed: theses, mis-routing (occurrence not points;
   ebird not paper_data), and the **green-cat-snake regression** (raw inaturalist → never resolved).
   Constitution edits (records-only-via-`points.get`; papers-first for taxonomy; compute-fresh-not-cache;
   observe-vs-modelled+N; respect gate-refuse) → v2 fixed the **golden regression** (resolves to *Boiga
   cyanea*, honest 0-records answer), **papers-first** (uropeltis now uses `paper_data`), and pushed
   resolved/papers/transfer/not_empty to **1.00**.
4. **`conn_hit` is over-strict.** It matches exact connector names; green-cat-snake answered correctly
   (resolved + honest) via occurrence/inaturalist without `points.get`, scoring conn_hit 0 despite the right
   *outcome*. Outcome-level scoring (right answer + right sources) matters more than exact-tool-match.

## Full-13 connector spread (capnudge, the winner)
`clarified_ok 0.69 · short 0.85 · conn_hit 0.38 · transfer_flag 1.00 · papers 1.00 · resolved 1.00 ·
not_empty 1.00` (mean 1.4 turns, 5.7 tools). Confirms: **constitution BEHAVIORS are strong** (short,
honest observed-vs-modelled framing, resolve, papers-first, never-empty all 0.85–1.00), **but tool
EXECUTION is weak (conn_hit 0.38).** The tell: `nursery`, `soil_indicators`, `grazing` ran **zero
connectors** (`conn=[]`) — short, honest-sounding answers produced from skill/memory/cache WITHOUT fresh
data; `russell_viper` ran only `points` (no `predict`/lens). So the mechanism buys brevity + honest
framing cheaply, but the cap can push qwen to **shortcut the actual computation** to answer fast. The
"compute-fresh, run the connector" rule is not enforced — a real gap.

## Recommendation / next
- **conn_hit is the next target, and it's partly the cap's fault.** The answer-now hook must not just cap
  tools — it must ensure the *right* connector actually ran for a data question before a final answer is
  allowed (or the router must route to the exact connector call per question type more prescriptively).
  Brevity without fresh computation is a trap.
- **Ship the mechanism config** (terse nudge + cap) as the default discipline; it's cheap and holds the
  constitution far better than baseline.
- **Build the "answer-now" hook** (`pre_tool_call`) to resolve the cap tension — the one thing `--max-turns`
  can't do — and (optionally) a **calibrated** clarify: only clarify on genuinely-vague openers, since the
  smart gate over-clarified. A cheap classifier or a tightened nudge, not a full smart gate.
- **Golden gate** guards green-cat-snake going forward. Keep expanding the syllabus + golden asserts.
