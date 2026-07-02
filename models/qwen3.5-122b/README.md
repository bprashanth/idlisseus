# Qwen3.5-122B-A10B (INT4+FP8 hybrid) — current primary

The primary serving model on this DGX Spark GB10. MoE model quantized and tuned
for the GB10 by the **albond** DGX Spark optimization work:
<https://github.com/albond/DGX_Spark_Qwen3.5-122B-A10B-AR-INT4>

This is the "122B" referred to across the benchmarks (see
[`benchmarks/benchmark7_qwen35/`](../../benchmarks/benchmark7_qwen35/)) and the
model driving the Hermes agent runs. It replaces Qwen3-Next-80B as the default;
80B is now the fallback.

## What it is

- **Base:** Qwen3.5-122B-A10B (Alibaba) — Mixture-of-Experts, 256 experts + a
  shared expert layer, **~10B active** params per token (hence "A10B"), 122B total.
- **Attention:** DeltaNet hybrid attention with recurrent state management —
  **incompatible with standard prefix caching** (do not assume prefix-cache
  reuse in benchmarks; this affects multi-turn latency accounting).
- **Quantization (hybrid, AutoRound INT4 + FP8):**
  - MoE expert weights → INT4 (Marlin kernel)
  - shared-expert MLP weights → FP8
  - selective, not uniform — preserves quality in the critical shared layers.
- **Weights:** ~71 GB for the hybrid checkpoint.

## Memory

- Single user @ 256K context: ~128 GB unified memory (at the edge of the 121.6 Gi
  pool — this is why it cannot coexist with ds4 or 80B).
- A TurboQuant variant with 4× KV-cache compression enables ~5 concurrent users
  @ 256K (matches B7's clean 10-user run at shorter context).

## Running it (actual deployment on this box)

The live service is container **`vllm-qwen35`** (image `vllm-qwen35-v2`), serving
`~/models/qwen35-122b-hybrid-int4fp8` on **`172.17.0.1:8001`** (it reuses the URL
80B previously had; albond's reference command uses port 8000).

```bash
# Start / stop
docker start vllm-qwen35
docker stop  vllm-qwen35
curl http://172.17.0.1:8001/v1/models     # served model name: "qwen"

# Fallback to 80B
docker start qwen80b-vllm                 # weights at ~/models/Qwen3-Next-80B-FP8
```

Serving config: `--served-model-name qwen`, `--attention-backend FLASHINFER`,
MTP-2 speculative decoding, `--reasoning-parser qwen3`. Odysseus endpoint id
`qwen35-122b`.

Download (if rebuilding): `hf download Intel/Qwen3.5-122B-A10B-int4-AutoRound`.

Bind to the Docker bridge `172.17.0.1`, **not** `0.0.0.0` — Cloudflare Access is
the security boundary (see repo `CLAUDE.md`).

## GB10 / SM121 specifics (why the albond build exists)

- **No native FP4 on SM121** — GB10 lacks the datacenter-only tensor
  instructions, so FP4 paths don't apply; INT4-Marlin + FP8 is the workable mix.
- **Memory-bandwidth bound** — 273 GB/s LPDDR5x is the ceiling; optimization
  targets bandwidth, not compute.
- **vLLM must be compiled from source** — prebuilt PyPI wheels lack SM121
  support (~30–60 min build). Standard `pip install vllm` will not work.
- FLASHINFER backend gives ~16% over the default; MTP-2 speculative decoding on
  by default.

## Performance (per albond + B7)

- ~52 tok/s typical, ~54.9 tok/s peak on long-context (a +82% improvement over
  the naive baseline through the combined optimizations).
- B7: 27s avg with thinking on, comparable to 80B (~8s) with thinking off on
  long prompts (prefill dominates); 10 concurrent users served cleanly.

## Coexistence

Cannot coexist with ds4 (670B) or 80B — all three need the full unified-memory
pool. Stop one before starting another (see `models/index.md`).
