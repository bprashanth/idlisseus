# Models

Four models have been evaluated on this DGX Spark GB10 (121.6 Gi unified memory, 1× GB10 GPU).

## Model inventory

| Model | Weights | RAM | Speed | State |
|-------|---------|-----|-------|-------|
| Qwen3-Next-80B FP8 | `~/models/Qwen3-Next-80B-FP8/` (77 GB) | 110 Gi | 3–20s/turn | **active** (`qwen80b-vllm`, port 8001) |
| DeepSeek V4 Flash | `models/deepseek-v4-flash/*.gguf` (on-disk) | 121 Gi (SSD stream) | 60–190s/turn | stopped (`ds4-ssd.service`) |
| Seed-OSS-36B AWQ | `~/models/Seed-OSS-36B-AWQ/` (21 GB) | ~42 Gi | ~30s/turn | stopped |
| Qwen3.5-2B | `~/.cache/huggingface/...Qwen3.5-2B` (4.6 GB) | ~10 Gi | 4–5s/turn | stopped |

ds4 and 80B cannot coexist: both consume the full 121 Gi pool. Stop one before starting the other.

Seed-OSS-36B was designed to coexist with ds4 in SSD streaming mode (~117 Gi combined), but Benchmark 3 found the combo unreliable. Qwen3.5-2B can coexist with ds4 (it needs only 8% of GPU).

## What we learned

**80B wins for everything we care about.** At 3–20s/turn it is 6–10× faster than ds4 and produces better answers with deeper reasoning and better instruction following. This matches Benchmark 6 results.

**ds4 is a fallback, not a default.** Useful when 80B is unavailable and latency is acceptable (e.g. batch jobs). 670B parameter count gives strong factual breadth but slow streaming makes it painful for interactive use.

**Seed-OSS-36B is retired.** 36B on AWQ is fast but quality is clearly below 80B and the tool-call parser (`seed_oss`) had reliability issues during benchmark runs.

**Qwen3.5-2B (sidekick) is a specialist.** Too small for reasoning tasks alone but valid for: triage queries, classifier prompts, and as a fast check before sending to 80B. The sidekick architecture (ds4 main + 2B filter) adds engineering complexity for marginal gain.

## Starting models

```bash
# Current production (80B)
docker start qwen80b-vllm          # ~9 min cold load; watch: docker logs -f qwen80b-vllm

# ds4 (SSD streaming mode — only systemd service that works reliably)
sudo systemctl start ds4-ssd       # binary in ds4/, kv cache in ds4-kv/
curl http://172.17.0.1:8000/v1/models

# Seed-OSS-36B AWQ (alongside ds4)
bash models/seed-oss-36b/run.sh

# Qwen3.5-2B sidekick (alongside ds4)
bash models/qwen3.5-2b/run.sh
```

## Per-model details

- [`deepseek-v4-flash/`](deepseek-v4-flash/) — ds4 source, systemd service, GGUF weight
- [`qwen3-next-80b/`](qwen3-next-80b/) — vLLM run script, download script, FP8 notes
- [`seed-oss-36b/`](seed-oss-36b/) — AWQ run script, coexistence notes
- [`qwen3.5-2b/`](qwen3.5-2b/) — sidekick run script, memory math
