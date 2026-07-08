# Benchmarks

Seven benchmark rounds on DGX Spark GB10 (121.6 Gi, GB10 GPU). All benchmarks run locally — no cloud API.

## Hypotheses we were testing

1. **Can a 670B quantized model (ds4) replace Cursor for developer tasks?** (B1)
2. **Does a Hermes token proxy unlock agentic tool use from any model?** (B2)
3. **Can Seed-OSS-36B coexist with ds4 for a faster/cheaper combo?** (B3)
4. **Can Qwen3.5-2B as a sidekick filter queries to reduce latency?** (B4/B5)
5. **Which model is best for interactive chatbot use at acceptable latency?** (B6)
6. **Does Qwen3.5-122B MoE (INT4+FP8 hybrid) beat 80B on quality and match it on speed?** (B7)

## Results summary

| Benchmark | Hypothesis | Result |
|-----------|-----------|--------|
| B1 (ds4 vs Cursor) | Can 670B replace Cursor? | Partial. ds4 matches Cursor on structured extraction; weaker on IDE integration and auto-completion speed |
| B2 (Hermes agent) | Does token proxy unlock tool use? | Yes. Hermes proxy works but is brittle; Nemotron-3-Super did better with native Hermes |
| B3 (Seed-OSS-36B) | Does 36B coexist with ds4? | Unstable. OOM under load; quality below ds4 on research tasks |
| B4 (sidekick) | Can 2B sidekick filter queries? | Yes in isolation, marginal gain in practice; adds operational complexity |
| B5 (parallel load) | Throughput under concurrent users? | ds4 SSD streaming degrades under concurrent requests; 80B handles concurrency better |
| B6 (chatbot) | Best model for chatbot UX? | **80B wins**: 8s avg vs 121s (ds4) vs 11s (2B). Quality and speed both better. |
| B7 (qwen35-122b) | Does 122B MoE beat 80B? | **Quality win, speed draw with thinking off.** 27s avg thinking-on vs 80B's 8s; thinking-off narrows gap on long prompts. 10 concurrent users served cleanly (wall=101s, all ok). KV cache <1% at 10 users. Full agentic loop in 6 turns/32s. |

## Key takeaways

Qwen3.5-122B MoE (INT4+FP8 hybrid) is the new primary model. Quality clearly exceeds 80B on
long-context reasoning and research tasks. With thinking off, latency is comparable to 80B for
large-context prompts (prefill dominates). With thinking on, latency is 3-4× higher for short
prompts but adds visible reasoning transparency. 10 concurrent users is comfortably within capacity.
80B remains a reliable fallback; ds4 for latency-insensitive batch work.

## Benchmark details

- [`benchmark1_ds4/`](benchmark1_ds4/) — ds4 vs Cursor: coding, form extraction, literature tasks
- [`benchmark2_hermes/`](benchmark2_hermes/) — Hermes token proxy + Nemotron-3-Super agent runs
- [`benchmark3_seed_oss/`](benchmark3_seed_oss/) — Seed-OSS-36B vs ds4 on research/paper tasks
- [`benchmark4_qwen_sidekick/`](benchmark4_qwen_sidekick/) — Qwen3.5-2B sidekick head-to-head
- [`benchmark5_parallel/`](benchmark5_parallel/) — parallel load/throughput stress test
- [`benchmark6_chatbot/`](benchmark6_chatbot/) — three-way chatbot comparison: ds4, sidekick, 80B
- [`benchmark7_qwen35/`](benchmark7_qwen35/) — Qwen3.5-122B: conversation, doc tasks, thinking toggle, 2/5/10-user concurrency, agentic loop
- [`semantic_broker/`](semantic_broker/) — **(active)** can we go from a conservation question to an insight over an AOI, correlating papers + CSVs + map layers? Runs on **Hermes/122B**, S. India (Nilgiris–Anamalai) AOI. Start with [`VISION.md`](semantic_broker/VISION.md) (the plain-language goal + the functions-vs-datacards split we arrived at).
  - **v-1** ([`EXPERIMENT_v-1.md`](semantic_broker/EXPERIMENT_v-1.md)): raw Hermes *finds* the right data but can't *use* it (wrong legends, unwritable EE reductions).
  - **connectors** ([`CONNECTORS_DESIGN.md`](semantic_broker/CONNECTORS_DESIGN.md), [`connectors/`](semantic_broker/connectors/)): 6 tested connectors (landcover/fire/terrain/WDPA/GBIF/geo) that own layer semantics + operations. Fixed both v-1 failure modes (correct fire ranking + correct land-cover, ~2 min).
  - **algebra loop** ([`algebra/NOTES.md`](algebra/NOTES.md), [`algebra/RESULTS_2h.md`](algebra/RESULTS_2h.md)): a self-improving loop where a frontier model manufactures **validated** connectors from 122B's failures — self-test gates every gold answer. **2h POC passed (2026-07-03):** all 3 gates met; discovered the **TREND** primitive (over-time) and built+validated the `greenness` connector (MOD13Q1 NDVI); a 20-min Hermes hang was caught by the new hard-timeout runner (`run_solver.sh`). Ledger: `algebra/ledger/`.
  - **components + AOI onboarding** ([`algebra/ONBOARDING.md`](algebra/ONBOARDING.md)): the loop is now AOI-portable — the only per-AOI artifact is one `algebra/aois/<name>.json`. Built + tested the three bridge components (**Scout** = gated data discovery w/ provenance + phantom guard; **Controller** = curriculum/bank; **Miner** = logs→playbook rules) and an `ecoregion` connector. Bootstrap dry-run on a 2nd AOI (**Elephants by the Lake, Krishnagiri** — dry Deccan, vs wet Anamalai) works end-to-end: real GBIF/CKAN discovery, questions weighted to the AOI (connectivity/dry-invasives), and it flagged **NETWORK + PATTERN** as the new breaker primitives that AOI demands. See `algebra/aois/elephants_by_the_lake/bootstrap_report.md`.
  - **maps / EBTL demo front-end** ([`experiments/EBTL_LIVE_MAP.md`](semantic_broker/experiments/EBTL_LIVE_MAP.md)): the site-level story map for the EBTL team — landing S2 overview → zoom to the 35 cm Maxar detail per issue, with `/why` provenance panels (sources + DOIs + method), Lantana **Prediction / Drivers / Records** toggle layers, mobile + touch. Self-contained single `index.html` (`issues_app.py`), deployed to a temporary **public S3** bucket. Sits above the connector-level verify lens ([`connectors/groundtruth_lens.md`](semantic_broker/connectors/groundtruth_lens.md)).
  - **known limitations** ([`semantic_broker/LIMITATIONS.md`](semantic_broker/LIMITATIONS.md)): a register of *behavioural* agent failures mined from real session transcripts (`state.db`) — e.g. the "snakes at EBTL" trace where the agent confidently mislabelled a species (common-name→scientific unverified), answered a spatial "where" question with no map/transfer, and persisted the error into a skill file. How to mine traces: [`agents/hermes/TRACE_INTROSPECTION.md`](../agents/hermes/TRACE_INTROSPECTION.md).
  - **next:** wire the bootstrap bank into the solve loop and run the **16h** version (Controller escalation + Miner each tick); dataset cards / retrieval broker (see VISION); build the NETWORK/PATTERN connectors when a run needs them.

## Reproducing

Each benchmark dir has a `REPORT.md` or `CHECKPOINT.md` with the exact run conditions.
`benchmark6_chatbot/run_chatbot_bench.sh` is the most complete script. Note: it references
`$REPO="$(dirname $0)/.."` which now resolves to `benchmarks/` not the repo root — adjust paths
if re-running.
