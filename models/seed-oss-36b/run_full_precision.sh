#!/bin/bash
# Start Seed-OSS-36B-Instruct (BF16, vLLM, single GPU) on this DGX Spark.
#
# Prerequisites: ds4-server MUST be stopped first (sudo systemctl stop ds4) -- this model
# and ds4 cannot fit in unified memory at the same time. See docs/models.md.
#
# Adapted from NVIDIA's own example (which uses --tensor-parallel-size 8 for a multi-GPU node)
# down to --tensor-parallel-size 1 for this single-GPU DGX Spark:
# https://docs.vllm.ai/projects/recipes/en/latest/Seed/Seed-OSS-36B.html
#
# Known idiosyncrasy (see docs/model_experiments.md, Benchmark 3): this model defaults to
# extensive visible <seed:think>...</seed:think> reasoning even for trivial prompts, and its
# observed decode rate (~3 tok/s) is roughly 5x slower than ds4's (~15 tok/s) on this hardware
# with this config (no speculative decoding, no quantization). It was NOT faster than ds4 for
# either short interactive queries or long document-synthesis tasks in our testing. Untried:
# the model's "Thinking Budget" feature may be tunable to reduce/disable the reasoning
# overhead -- worth trying before writing the model off for interactive use.

set -euo pipefail

docker run --rm -d --gpus all \
  -v "$HOME/.cache/huggingface:/root/.cache/huggingface" \
  -p 172.17.0.1:8000:8000 \
  --name seed-oss-vllm \
  vllm/vllm-openai:cu130-nightly \
    --model ByteDance-Seed/Seed-OSS-36B-Instruct \
    --served-model-name seed-oss-36b \
    --host 0.0.0.0 \
    --port 8000 \
    --tensor-parallel-size 1 \
    --enable-auto-tool-choice \
    --tool-call-parser seed_oss \
    --max-model-len 65536

echo "Container 'seed-oss-vllm' starting. First run downloads ~72GB to ~/.cache/huggingface"
echo "(can take ~1.5 hours on this network). Watch progress with:"
echo "  du -sh ~/.cache/huggingface/hub/models--ByteDance-Seed--Seed-OSS-36B-Instruct"
echo "  docker logs -f seed-oss-vllm"
echo "Ready when this responds: curl -s http://172.17.0.1:8000/v1/models"
