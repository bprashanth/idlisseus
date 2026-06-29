# Seed-OSS-36B AWQ

**Model:** Seed-OSS-36B-Instruct, INT4 AWQ quantization
**Weights:** `~/models/Seed-OSS-36B-AWQ/` (21 GB)
**Source:** `QuantTrio/Seed-OSS-36B-Instruct-AWQ` on HuggingFace
**Inference engine:** vLLM (`vllm/vllm-openai:cu130-nightly`)
**Port:** `172.17.0.1:8001`
**Status:** retired (use Qwen3-Next-80B instead)

## Start alongside ds4

```bash
# ds4 must already be running in SSD streaming mode
sudo systemctl status ds4-ssd

bash models/seed-oss-36b/run.sh
# ready when: curl -s http://172.17.0.1:8001/v1/models
```

## Memory

~21 GB weights + KV cache ≈ 42 Gi total. Combined with ds4 SSD streaming ≈ 117 Gi / 121 Gi.
Technically fits but benchmark runs were unstable — OOMs under load.

## Why retired

Benchmark 3 showed Seed-OSS-36B answers below ds4 quality on research tasks and below
Qwen3-Next-80B on everything. The `seed_oss` reasoning parser had reliability issues.
With 80B available, there is no use case for Seed-OSS-36B on this hardware.
