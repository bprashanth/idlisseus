#!/bin/bash
# Start Qwen3-Next-80B-A3B-Instruct (FP8, vLLM, single GPU) as a ds4 replacement candidate.
#
# Prerequisites: ds4-server MUST be stopped first -- this and ds4 cannot fit in unified memory
# at the same time (80.5GB weights, ~37GB headroom left for KV cache + concurrent batching).
#
# Deliberately NO --speculative-config / MTP here, unlike NVIDIA's Nemotron-3 example --
# Benchmark 2 found MTP speculative decoding collapses under long, growing-context agentic
# sessions on this hardware. Avoiding it from the start for this model.
#
# Adapted from vLLM's official recipe (https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3-Next.html),
# which only documents a --tensor-parallel-size 4 example -- adapted to 1 for this single GPU.

# KNOWN ISSUE (hit and fixed during Benchmark 4): the env-var-driven FP8 MoE backend
# selection from vLLM's own recipe page (VLLM_USE_FLASHINFER_MOE_FP8 etc.) falls back to a
# CUTLASS kernel on this GPU that does NOT support this checkpoint's FP8 block-quant scheme --
# fails immediately with "ValueError: FP8 MoE backend FLASHINFER_CUTLASS does not support the
# deployment configuration". Fix: force --moe-backend marlin explicitly (same backend that
# worked for Nemotron-3's MoE) instead of the env vars.

set -euo pipefail

# Model weights are pre-downloaded to ~/models/Qwen3-Next-80B-FP8/ via hfd.sh + hf-mirror.com.
# Mount the local dir read-only so vLLM doesn't try to re-download anything.
MODEL_DIR="$HOME/models/Qwen3-Next-80B-FP8"

if [ ! -f "$MODEL_DIR/config.json" ]; then
  echo "ERROR: $MODEL_DIR/config.json not found — download not complete yet." >&2
  echo "  Check progress: du -sh $MODEL_DIR && kill -0 \$(cat ~/models/qwen3-next-80b-download.pid)" >&2
  exit 1
fi

docker run --rm -d --gpus all \
  -v "$MODEL_DIR:/model:ro" \
  -p 172.17.0.1:8000:8000 \
  --name qwen-big-vllm \
  vllm/vllm-openai:cu130-nightly \
    --model /model \
    --served-model-name qwen3-next-80b \
    --host 0.0.0.0 \
    --port 8000 \
    --tensor-parallel-size 1 \
    --enable-prefix-caching \
    --max-model-len 262144 \
    --moe-backend marlin \
    --enable-auto-tool-choice \
    --tool-call-parser hermes

echo "Container 'qwen-big-vllm' starting from local weights at $MODEL_DIR."
echo "  docker logs -f qwen-big-vllm"
echo "Ready when: curl -s http://172.17.0.1:8000/v1/models"
