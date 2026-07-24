#!/usr/bin/env bash
# Run a connector self-test inside the hermes image (its venv python has ee).
# The self-test gate (NOTES.md §0/§3): pass => connector trusted; fail => REJECTED.
#
# Usage: run_selftest.sh <connectors_dir> <test_file.py>
#   <connectors_dir> is mounted at /opt/data/connectors (so `from connectors.X`
#   resolves); pass a CORRUPTED copy here for the §3 meta-check.
set -euo pipefail

CONN="$(cd "${1:?usage: run_selftest.sh <connectors_dir> <test_file>}" && pwd)"
TEST="$(readlink -f "${2:?test file}")"
TDIR="$(dirname "$TEST")"; TBASE="$(basename "$TEST")"
IMAGE="${HERMES_IMAGE:-hermes-agent-local}"

timeout 300 docker run --rm --network host \
  -v "$HOME/.hermes:/opt/data" \
  -v "$CONN:/opt/data/connectors:ro" \
  -v "$TDIR:/opt/data/selftest:ro" \
  -e HOME=/opt/data -w /opt/data \
  --entrypoint /opt/hermes/.venv/bin/python3 \
  "$IMAGE" "/opt/data/selftest/$TBASE"
