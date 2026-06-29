# Benchmarks

Six benchmark rounds on DGX Spark GB10 (121.6 Gi, GB10 GPU). All benchmarks run locally — no cloud API.

## Hypotheses we were testing

1. **Can a 670B quantized model (ds4) replace Cursor for developer tasks?** (B1)
2. **Does a Hermes token proxy unlock agentic tool use from any model?** (B2)
3. **Can Seed-OSS-36B coexist with ds4 for a faster/cheaper combo?** (B3)
4. **Can Qwen3.5-2B as a sidekick filter queries to reduce latency?** (B4/B5)
5. **Which model is best for interactive chatbot use at acceptable latency?** (B6)

## Results summary

| Benchmark | Hypothesis | Result |
|-----------|-----------|--------|
| B1 (ds4 vs Cursor) | Can 670B replace Cursor? | Partial. ds4 matches Cursor on structured extraction; weaker on IDE integration and auto-completion speed |
| B2 (Hermes agent) | Does token proxy unlock tool use? | Yes. Hermes proxy works but is brittle; Nemotron-3-Super did better with native Hermes |
| B3 (Seed-OSS-36B) | Does 36B coexist with ds4? | Unstable. OOM under load; quality below ds4 on research tasks |
| B4 (sidekick) | Can 2B sidekick filter queries? | Yes in isolation, marginal gain in practice; adds operational complexity |
| B5 (parallel load) | Throughput under concurrent users? | ds4 SSD streaming degrades under concurrent requests; 80B handles concurrency better |
| B6 (chatbot) | Best model for chatbot UX? | **80B wins**: 8s avg vs 121s (ds4) vs 11s (2B). Quality and speed both better. |

## Key takeaways

80B Qwen3-Next is the clear winner for interactive use. ds4 remains useful as a fallback for
latency-insensitive batch work. The sidekick architecture is not worth the operational overhead
once 80B is available.

## Benchmark details

- [`benchmark1_ds4/`](benchmark1_ds4/) — ds4 vs Cursor: coding, form extraction, literature tasks
- [`benchmark2_hermes/`](benchmark2_hermes/) — Hermes token proxy + Nemotron-3-Super agent runs
- [`benchmark3_seed_oss/`](benchmark3_seed_oss/) — Seed-OSS-36B vs ds4 on research/paper tasks
- [`benchmark4_qwen_sidekick/`](benchmark4_qwen_sidekick/) — Qwen3.5-2B sidekick head-to-head
- [`benchmark5_parallel/`](benchmark5_parallel/) — parallel load/throughput stress test
- [`benchmark6_chatbot/`](benchmark6_chatbot/) — three-way chatbot comparison: ds4, sidekick, 80B

## Reproducing

Each benchmark dir has a `REPORT.md` or `CHECKPOINT.md` with the exact run conditions.
`benchmark6_chatbot/run_chatbot_bench.sh` is the most complete script. Note: it references
`$REPO="$(dirname $0)/.."` which now resolves to `benchmarks/` not the repo root — adjust paths
if re-running.
