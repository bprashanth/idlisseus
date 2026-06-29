#!/bin/bash
# Start Nemotron-3-Super-120B (NVFP4, vLLM) on this DGX Spark.
#
# Prerequisites: ds4-server MUST be stopped first (sudo systemctl stop ds4) -- this model
# and ds4 cannot fit in unified memory at the same time. See docs/models.md.
#
# Known issue: the ~76GB model download from Hugging Face has stalled mid-download at least
# once on this network (2 of 16 shards stuck >1hr while others completed around them). If
# `du -sh ~/.cache/huggingface/hub/models--nvidia--NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4`
# stops growing for >10min while the container is still "Up", stop and re-run this script --
# huggingface_hub resumes/retries only the stuck shards, not the whole download.
#
# Known issue: --max-model-len 1000000 exceeds the model's actual trained
# max_position_embeddings (262144) -- vLLM allows it via VLLM_ALLOW_LONG_MAX_MODEL_LEN=1 per
# NVIDIA's own example, but its own startup warning says positions beyond 262144 can produce
# NaN (RoPE) or CUDA out-of-bounds errors. Our benchmark tasks never approached that length.
#
# Known issue: this exact config (NVFP4 + MTP speculative decoding) suffered severe per-token
# throughput collapse under a long, accumulating agentic conversation (Benchmark 2) -- it hit
# Hermes's 60-turn budget without finishing. GPU was confirmed genuinely busy (96% util), not
# hung; root cause was MTP speculative-decoding acceptance-rate collapse at long context. If
# trying this again for agentic work, try dropping --speculative_config first.

set -euo pipefail
cd "$(dirname "$0")"

docker run --rm -d --gpus all \
  -e VLLM_NVFP4_GEMM_BACKEND=marlin \
  -e VLLM_ALLOW_LONG_MAX_MODEL_LEN=1 \
  -e VLLM_FLASHINFER_ALLREDUCE_BACKEND=trtllm \
  -e VLLM_USE_FLASHINFER_MOE_FP4=0 \
  -v "$HOME/.cache/huggingface:/root/.cache/huggingface" \
  -v "$(pwd)/super_v3_reasoning_parser.py:/app/super_v3_reasoning_parser.py" \
  -p 172.17.0.1:8000:8000 \
  --name nemotron-vllm \
  vllm/vllm-openai:cu130-nightly \
    --model nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4 \
    --served-model-name nemotron-3-super \
    --host 0.0.0.0 \
    --port 8000 \
    --tensor-parallel-size 1 \
    --quantization fp4 \
    --kv-cache-dtype fp8 \
    --max-model-len 1000000 \
    --mamba_ssm_cache_dtype float32 \
    --moe-backend marlin \
    --speculative_config '{"method":"mtp","num_speculative_tokens":3,"moe_backend":"triton"}' \
    --reasoning-parser-plugin /app/super_v3_reasoning_parser.py \
    --reasoning-parser super_v3 \
    --enable-auto-tool-choice \
    --tool-call-parser qwen3_coder

echo "Container 'nemotron-vllm' starting. First run downloads ~76GB to ~/.cache/huggingface"
echo "(can take 1-2+ hours on this network). Watch progress with:"
echo "  du -sh ~/.cache/huggingface/hub/models--nvidia--NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4"
echo "  docker logs -f nemotron-vllm"
echo "Ready when this responds: curl -s http://172.17.0.1:8000/v1/models"
