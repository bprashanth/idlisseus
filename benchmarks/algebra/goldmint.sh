#!/usr/bin/env bash
# Run goldmint.py inside the hermes image (venv has ee + connectors mounted).
# Prints gold JSON to stdout. Usage mirrors goldmint.py flags.
#   goldmint.sh --species "Lantana camara" --bbox 77.4,11.9,78.5,12.9 --annotate landcover --group landcover
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SB="$(cd "$HERE/../semantic_broker" && pwd)"
IMAGE="${HERMES_IMAGE:-hermes-agent-local}"
timeout "${GOLD_TIMEOUT:-400}" docker run --rm --network host \
  -v "$HOME/.hermes:/opt/data" \
  -v "$SB/connectors:/opt/data/connectors:ro" \
  -v "$HERE/goldmint.py:/opt/data/goldmint.py:ro" \
  -e HOME=/opt/data -w /opt/data \
  --entrypoint /opt/hermes/.venv/bin/python3 \
  "$IMAGE" /opt/data/goldmint.py "$@"
