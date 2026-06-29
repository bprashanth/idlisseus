# Qwen3-Next-80B FP8 — current production model

**Model:** Qwen3-Next-80B-A3B-Instruct, FP8 checkpoint
**Weights:** `~/models/Qwen3-Next-80B-FP8/` (77 GB, 8 shards)
**Inference engine:** vLLM (`vllm/vllm-openai:cu130-nightly`)
**Port:** `172.17.0.1:8001` (Docker bridge only)
**Container:** `qwen80b-vllm` (persistent, created manually)

## Start / stop

```bash
# Start (already-created persistent container — ~9 min cold load from EXT4)
docker start qwen80b-vllm
docker logs -f qwen80b-vllm          # ready when you see "Application startup complete"

# Stop
docker stop qwen80b-vllm

# Check
curl -s http://172.17.0.1:8001/v1/models | python3 -m json.tool
```

The `run.sh` here creates a NEW container named `qwen-big-vllm` on port 8000 (an older script).
The production container `qwen80b-vllm` was created manually on port 8001. Use `docker start` to
resume the existing container; re-run `run.sh` only if the container was removed.

## Key vLLM flags

```
--moe-backend marlin          # required: flashinfer-cutlass fails on GB10 FP8 block-quant
--enable-auto-tool-choice
--tool-call-parser hermes     # Hermes tool-call format supported natively
--max-model-len 262144        # 256K context
--enable-prefix-caching
```

## Memory profile

- Weights: ~77 GB (FP8, 8 shards)
- Total at steady state: ~110 Gi unified memory
- Cannot coexist with ds4 (both need full 121 Gi pool)

## Speed

Benchmark 6 (3-question chatbot test):
- Average: 8s/turn
- Range: 3–20s (longer for tool-call reasoning chains)

## Notes

- MoE backend: must use `--moe-backend marlin`. FLASHINFER_CUTLASS fails immediately with
  "FP8 MoE backend does not support this deployment configuration". Discovered in Benchmark 4.
- Speculative decoding (MTP): deliberately disabled. Benchmark 2 showed MTP collapses under
  long agentic sessions on this hardware.
- 80B supports Hermes tool-call format natively — no proxy needed for Idlisseus agent mode.
