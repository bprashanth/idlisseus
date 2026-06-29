# Qwen3.5-2B — lightweight sidekick

**Model:** Qwen/Qwen3.5-2B (BF16, 4.6 GB)
**Weights:** `~/.cache/huggingface/hub/models--Qwen--Qwen3.5-2B/`
**Inference engine:** vLLM (`vllm/vllm-openai:cu130-nightly`)
**Port:** `172.17.0.1:8001`
**Status:** stopped (used for benchmarking; not in active rotation)

## Start alongside ds4

```bash
# ds4 must already be running in SSD streaming mode
sudo systemctl status ds4-ssd

bash models/qwen3.5-2b/run.sh
# ready when: curl -s http://172.17.0.1:8001/v1/models
```

## Memory math

ds4 SSD streaming uses ~111 Gi of the 121.6 Gi pool → 10.6 Gi free.
Qwen3.5-2B at `--gpu-memory-utilization 0.08` (8% × 121.63 = 9.73 Gi) fits in the gap.
9% (10.95 Gi) fails: "Free memory 10.58/121.63 GiB < desired 10.95 GiB" — 37 MB margin.

## Use cases

- Fast triage before routing to 80B
- Short summaries, arithmetic, classification
- Benchmark baseline (Benchmark 4/6)

## Not suitable for

- Reasoning chains (too small)
- Tool use (context length capped at 8192 tokens)
- Any session that replaces 80B as the primary model
