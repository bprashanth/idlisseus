#!/usr/bin/env bash
# Connector-assisted run: same Hermes/122B, but with the connector tools +
# PLAYBOOK mounted and the data-finding step pre-staged. Isolates whether the
# connectors let the agent produce a correct insight (contrast with run_v-1.sh).
#
# Usage: run_connectors.sh "<question>" [/opt/data/query_data/<input>.csv]
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
SB="$REPO/benchmarks/semantic_broker"
QUESTION="${1:?usage: run_connectors.sh \"<question>\" [input.csv path in container]}"
INPUT="${2:-}"
IMAGE="${HERMES_IMAGE:-hermes-agent-local}"

INPUT_LINE=""
[ -n "$INPUT" ] && INPUT_LINE="The input data (points) for this question is the CSV at ${INPUT}. "

PROMPT="You have connector tools in /opt/data/connectors/ for live geospatial \
conservation data (land cover, fire, terrain, species occurrence, protected areas, \
spatial joins). READ /opt/data/connectors/PLAYBOOK.md FIRST — it gives the pattern \
and lists the connectors; each has a <name>.md card and a --describe. \
Use these connectors instead of writing Earth Engine code yourself, and NEVER guess \
a class code or band name — run the connector's --describe to get the legend. \
${INPUT_LINE}Question: ${QUESTION} \
Report which connectors you called and show the resulting table."

exec docker run --rm --network host \
  -v "$HOME/.hermes:/opt/data" \
  -v "$SB/connectors:/opt/data/connectors:ro" \
  -v "$SB/queries/data:/opt/data/query_data:ro" \
  -e HOME=/opt/data \
  "$IMAGE" chat -q "$PROMPT"
