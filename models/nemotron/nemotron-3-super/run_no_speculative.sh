#!/bin/bash
# Nemotron-3-Super-120B WITHOUT speculative decoding — Stage 4 retry.
#
# Identical to run.sh EXCEPT:
#   - --speculative_config removed entirely (suspected root cause of Benchmark 2 collapse)
#   - --max-model-len reduced from 1000000 to 131072 (safe within RoPE-trained range of 262144;
#     1000000 was an NVIDIA showcase value, but startup warns NaN/OOM past 262144; our benchmark
#     tasks never need more than ~100K tokens so 131072 is a safe conservative choice)
#
# See run.sh comments for all the other known issues with this model's download / config.
# Model weights should already be cached from Benchmark 2 (~76GB in ~/.cache/huggingface).

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
    --max-model-len 131072 \
    --mamba_ssm_cache_dtype float32 \
    --moe-backend marlin \
    --reasoning-parser-plugin /app/super_v3_reasoning_parser.py \
    --reasoning-parser super_v3 \
    --enable-auto-tool-choice \
    --tool-call-parser qwen3_coder

echo "Container 'nemotron-vllm' starting (no speculative decoding — Stage 4 retry)."
echo "Weights should be cached. Watch: docker logs -f nemotron-vllm"
echo "Ready when: curl -s http://172.17.0.1:8000/v1/models"
