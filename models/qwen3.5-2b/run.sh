#!/bin/bash
# Start Qwen3.5-2B (BF16) as a lightweight sidekick on port 8001, ALONGSIDE ds4 on port 8000.
#
# Memory note: ds4 uses ~111GB of the 121.6GB unified CUDA pool, leaving ~10.6GB free.
# Qwen3.5-2B is 4.23GB BF16 (4,548,221,488 bytes actual). With --gpu-memory-utilization 0.08
# (8% of 121.63GB = ~9.73GB total budget), vLLM gets 9.73GB which fits in the 10.6GB gap.
# 9% (10.95GB) fails at startup: "Free memory 10.58/121.63 GiB < desired 10.95 GiB" — the
# margin is 37MB; use 8% to stay safely under. Monitor with `free -h` after launch.
#
# --max-model-len 8192 keeps the per-token KV cache footprint small -- more than enough for
# the light-prompt battery this sidekick is intended for (short queries, summaries, arithmetic).
# Increase max-model-len only if you have more headroom (e.g. after stopping ds4 and
# re-running via a different config).

set -euo pipefail

docker run --rm -d --gpus all \
  -v "$HOME/.cache/huggingface:/root/.cache/huggingface" \
  -e HF_HUB_ENABLE_HF_TRANSFER=0 \
  -p 172.17.0.1:8001:8001 \
  --name qwen-sidekick-vllm \
  vllm/vllm-openai:cu130-nightly \
    --model Qwen/Qwen3.5-2B \
    --served-model-name qwen3.5-2b \
    --host 0.0.0.0 \
    --port 8001 \
    --tensor-parallel-size 1 \
    --gpu-memory-utilization 0.08 \
    --max-model-len 8192 \
    --max-num-seqs 4

echo "Container 'qwen-sidekick-vllm' starting. First run downloads ~4.6GB to ~/.cache/huggingface."
echo "  du -sh ~/.cache/huggingface/hub/models--Qwen--Qwen3.5-2B"
echo "  docker logs -f qwen-sidekick-vllm"
echo "Ready when this responds: curl -s http://172.17.0.1:8001/v1/models"
