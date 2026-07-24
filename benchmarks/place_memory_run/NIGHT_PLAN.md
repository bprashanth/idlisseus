# Place-memory conversational bench — overnight plan + checkpoint

Started 2026-07-09 (autonomous, Opus 4.8). **Entry point: this file.** Builds on the Eastern Ghats work
(`../eastern_ghats_run/`) and the architecture in `../../dss/ARCHITECTURE.md` / heartwood memory docs.

## Goal
A **multi-turn** benchmark that (a) spans **all connectors/skills**, (b) has **expected best outcomes** +
a **golden regression suite** (incl. the green-cat-snake name-resolution test), (c) lets us try a few
**smart+cheap integration plugs** and pick what best holds **constitution adherence** with **short
answers**, and (d) runs **self-improving**: mine traces → fix skills/instructions → re-run → golden tests
must pass. Guided by place-based-memory goals (know the place · ask-when-unsure · transfer+flag-modelled ·
observe-when-local · short + follow-ups).

## Clarified expected behavior (user, 2026-07-09)
- Modelling **with points inside the AOI is fine** — just label it "modelled, backed by N points". So the
  fork is not "don't model when local data exists"; it's "**always say observed vs modelled + N**".
- Answers must be **short**; achieve via a smart model OR by nudging qwen122b (hooks / --max-turns / prose).
- **Must be multi-turn** or it's not useful.

## Syllabus (`syllabus.json`, 13 scenarios spanning the tool/skill space)
name-resolution+transfer (green cat snake, REGRESSION) · distribution (invasives) · landscape EE
(lakes/water, tree-cover/landcover+s2, terrain) · colocation (cobra↔lantana, geo) · trend (forest
recovery, greenness) · literature/papers (Uropeltis taxonomy, paper_data+litscout) · transfer+verify
(Russell's viper, predict+lens) · phenology (nursery) · bird-bridge (ebird) · indicators · human-use
(grazing proxy). Each carries `expect_connectors`, `expect_clarify`, `expect_transfer_flag`, `papers_first`,
`regression`, `must_resolve`.

## Scoring — constitution adherence + expected-tool hit
Per scenario, mined from state.db: **clarified-when-expected · short (every turn) · hit expected
connectors · flagged modelled when it transferred · papers-first when literature · resolved the name ·
not-empty**. Golden subset = hard assertions (green cat snake → Boiga cyanea + flag; short; clarify-on-vague).

## Integration plugs to try (multi-turn, pick best on adherence+short)
1. **qwen-alone** (baseline).
2. **qwen + cap + terse-nudge** (mechanism only: `--max-turns` + a short-answer system nudge — no smart model).
3. **gate(smart)+qwen+synth(smart)** (assembled bookends).
Later: hook-based (pre_llm_call gate / transform_llm_output synth / pre_tool_call cap) to keep the hermes UI.

## Loop
baseline → mine failures → fix constitution/recipes/connectors → re-run → **golden tests must pass** → try
the plugs → pick best → checkpoint. Keep answers short; keep infra clean.

## STATUS (newest first)
- **[shipped to REAL chat + parallelism + classifier (2026-07-10)]**
  - **`discipline` plugin** (`agents/hermes/plugins/discipline/`, README + install.sh) puts the winning
    behavior into live `./chat.sh` natively (pre_llm_call STEER + pre_tool_call cap). Verified on the exact
    failing "snakes at ebtl" case: was serial-16-tool thesis → now short, honest, capped, multi-turn
    drill-down (turn 1 observed 0 records → turn 2 MODELLED risk zones "backed by 356 records" → where to
    warn staff). Just run `./chat.sh` (NOT --smart-model).
  - **PARALLELISM — ISOLATED + RESOLVED model-conditionally (2026-07-11).** The `Unknown tool ''` /
    "tool name empty" IS the batching, and it's **qwen-SPECIFIC** (proven: same batch-tempting query,
    qwen=2 empty-name calls, **deepseek=0** — deepseek batches perfectly). So parallelism is NOT broken in
    hermes — only in qwen's tool-call formatter. **Fix:** the batch-vs-serial rule is now **model-conditional
    in the discipline plugin** (`pre_llm_call` gets `model`): qwen→serial, deepseek/glm→batch. Removed the
    blanket SOUL rule (it wrongly slowed every model — SOUL is now neutral on tool-count). So deepseek/glm
    get parallelism; qwen stays safe.
  - **CLARIFY CLASSIFIER (deterministic route):** `clarify_classifier.py` (CLARIFY vs PROCEED) tested on
    16 labeled openers — **glm5.2 = 0.94**, deepseekv4 = 0.88. So a tiny glm call makes clarify reliable
    (qwen's prose clarify is a coin-flip). NEXT (optional, has per-turn cost): wire glm classifier into the
    plugin's pre_llm_call → on CLARIFY force "ask one question", on PROCEED normal steer.
  - Honest limits: cap occasionally causes empty-then-retry (mitigated _CAP=12 + strict block); clarify not
    deterministic until the classifier is wired.
- **[capnudge v2 — GOLDEN REGRESSION FIXED; winner = mechanism]** Full write-up: `REPORT.md`.
  - **green_cat_snake now PASSES golden**: resolves to *Boiga cyanea*, honest "0 records, observed vs
    modelled", short, non-empty. v2 (cap 8→14 + "always end with an answer" + clarify nudge) also fixed
    **papers-first** (uropeltis→paper_data) and pushed resolved/papers/transfer/not_empty to **1.00**;
    clarified 0.67→0.83. Cost: short 1.00→0.67 but the 2 "long" are 1154/1343 ch (good answers, not theses
    — threshold artifact). Real fix for the cap tension = an **"answer-now" pre_tool_call hook** (next).
  - **Winner = capnudge (cheap mechanism), NOT bookends (smart gate).** Self-improving loop worked
    (baseline→mine→constitution fix→golden pass). Running capnudge on the full 13 (connector spread) now.
- **[3-way done — MECHANISM beats SMART-GATE end-to-end]** 6 scenarios. short/conn_hit/clarified_ok:
  qwen 0.17/0.33/0.67 · **capnudge 1.00/0.69/0.67** · bookends 1.00/**0.00**/0.33.
  - **capnudge (cheap mechanism = terse nudge + tool cap) WINS** — short + best routing + actually
    delivers answers, no smart model.
  - **bookends (smart gate) UNDERPERFORMS end-to-end**: the gate over-clarifies (asks on the 4 CLEAR Qs
    too) and the multi-turn convo **stalls at the clarify** (conn_hit 0.0 — qwen barely runs). The earlier
    "gate 4/4 clarify" was isolation-only; end-to-end, over-clarify + stall = fewer real answers. (Part of
    the stall is a user-sim artifact — it says DONE instead of answering the clarify — but the over-clarify
    is real.) **So: don't front with a smart gate; nudge the cheap model.**
  - **Golden FAILS all 3** on green_cat_snake: qwen raw-inat (no resolve), capnudge cap-8 truncated→empty,
    bookends stalled. → capnudge **v2** running (cap 8→14, "always end with a final answer", + a clarify
    nudge for vague openers) to (a) pass golden, (b) get clarify from the mechanism too.
  - After v2 golden pass → run winner (capnudge) on the FULL 13 (connector-spread) + report.
- **[capnudge done — big win + 2 fixes queued]** (6-scenario spread; report via `conv_bench.py report`)
  - **qwen baseline:** short **0.17**, conn_hit 0.33, clarified 0.67. Dumps theses; mis-routes (occurrence
    not points; ebird not paper_data); green_cat_snake used raw inaturalist → **didn't resolve** (regression).
  - **capnudge (qwen + terse nudge + cap, NO smart model):** short **1.00**, conn_hit **0.69** — the
    mechanism fixed brevity + the constitution edits fixed routing (cobra→geo, forest→greenness/landcover,
    green_cat_snake→**points/resolve**). Remaining: (a) **green_cat_snake EMPTY** — cap=8 truncated it
    before a final answer (golden fail); (b) **uropeltis papers-first** still mis-routed to points not
    paper_data/litscout; (c) **clarified still 0.67** (mechanism can't add clarify — needs the gate).
  - **Constitution edits applied + live:** get-records-only-via-points.get (never raw inaturalist/
    occurrence); papers-first for taxonomy; compute-fresh-not-cache; observe-vs-modelled+N; respect gate-refuse.
  - **Fixes queued (in conv_bench):** capnudge nudge now "ALWAYS end with a final answer; stop don't
    over-run"; cap 8→14 (headroom so simple Qs finish). Re-run capnudge after bookends.
- **[baseline running]** `conv_bench.py` built (3 configs, multi-turn user-sim, scores constitution +
  expected-connector hits + golden gate). chat.sh got `HERMES_MAXTURNS` passthrough. Harness validated:
  qwen answers "invasives" with an 1808-char thesis, no clarify, shortcuts via read_file/skill_view (0
  fresh connectors) — the exact failures to fix. Running qwen baseline on a 6-scenario spread. NEXT on
  completion: mine → fix constitution (COMPUTE-FRESH not from cache; observe-vs-modelled+N; stronger
  clarify) → run capnudge + bookends → compare → golden gate → iterate.
  Known: prose won't fix qwen's clarify/short (proven) — the mechanism (cap+nudge) and smart gate
  (bookends) are what the config comparison measures; constitution edits fix the data-honesty signals.
- [init] run dir + syllabus (13) written. Building harness + chat.sh --max-turns passthrough next.
