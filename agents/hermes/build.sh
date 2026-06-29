#!/bin/bash
# Build the local Hermes image with benchmark-ready tooling.
# Run from the repo root:  bash agents/hermes/build.sh
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
docker build -t hermes-agent-local "$REPO/agents/hermes/"
echo "Built: hermes-agent-local"
echo "Use in run scripts: replace 'nousresearch/hermes-agent' with 'hermes-agent-local'"
