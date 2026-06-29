#!/bin/bash
# Start Seed-OSS-36B-Instruct-AWQ (INT4 AWQ, vLLM) on port 8001.
#
# Memory: ~21 GB weights + KV cache. Designed to coexist with ds4 in SSD
# streaming mode (~83 GB warm). Total at steady state: ~117 GB of 121 GB.
#
# Prerequisites:
#   - ds4 running in SSD streaming mode (deploy/ds4-ssd.service), not normal mode
#   - AWQ weights at ~/models/Seed-OSS-36B-AWQ/
#   - sudo systemctl start ds4-ssd  (or ds4 already running with --ssd-streaming)
#
# Weights: QuantTrio/Seed-OSS-36B-Instruct-AWQ (21 GB download)
# Download: huggingface-cli download QuantTrio/Seed-OSS-36B-Instruct-AWQ \
#           --local-dir ~/models/Seed-OSS-36B-AWQ --local-dir-use-symlinks False

set -euo pipefail

[ -f "$HOME/models/Seed-OSS-36B-AWQ/config.json" ] \
  || { echo "ERROR: AWQ weights not found at ~/models/Seed-OSS-36B-AWQ/"; exit 1; }

docker run --rm -d --gpus all \
  -v "$HOME/models/Seed-OSS-36B-AWQ:/model:ro" \
  -p 172.17.0.1:8001:8000 \
  --name seed-oss-awq-vllm \
  vllm/vllm-openai:cu130-nightly \
    --model /model \
    --served-model-name seed-oss-36b \
    --host 0.0.0.0 \
    --port 8000 \
    --tensor-parallel-size 1 \
    --quantization awq \
    --dtype float16 \
    --gpu-memory-utilization 0.35 \
    --max-model-len 65536 \
    --enable-auto-tool-choice \
    --tool-call-parser seed_oss \
    --reasoning-parser seed_oss

echo "Container 'seed-oss-awq-vllm' starting on 172.17.0.1:8001"
echo "Ready when: curl -s http://172.17.0.1:8001/v1/models"
echo "Logs: docker logs -f seed-oss-awq-vllm"
