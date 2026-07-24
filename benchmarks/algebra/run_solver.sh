#!/usr/bin/env bash
# Loop Solver: Hermes + 122B with the CURRENT connector library mounted, a hard
# timeout, and a captured trace. This is the runner NOTES.md §2/§6 describes but
# neither run_v-1.sh (no connectors) nor run_connectors.sh (no timeout) is.
#
# Differs from run_connectors.sh on purpose: it PERMITS a raw-EE fallback when no
# connector fits, so a missing capability produces the v-1 struggle (hand-rolled
# NDVI reduction) that fires the detector — instead of an instant refusal.
#
# Usage: run_solver.sh "<question>" [/opt/data/query_data/<input>.csv]
# Env:   RUN_ID (log name), CONN_DIR (connector set to mount), SOLVER_TIMEOUT=1200
# Emits: runs/<RUN_ID>.log (full stdout) and prints a STRUGGLED=yes|no verdict.
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
SB="$REPO/benchmarks/semantic_broker"
QUESTION="${1:?usage: run_solver.sh \"<question>\" [input.csv]}"
INPUT="${2:-}"
IMAGE="${HERMES_IMAGE:-hermes-agent-local}"
CONN_DIR="${CONN_DIR:-$SB/connectors}"
RUN_ID="${RUN_ID:-$(date +%Y%m%d_%H%M%S)}"
TIMEOUT="${SOLVER_TIMEOUT:-1200}"
T_STRUGGLE="${T_STRUGGLE:-480}"      # §5: correct connector runs finished < 3min
LOG="$HERE/runs/${RUN_ID}.log"

INPUT_LINE=""
[ -n "$INPUT" ] && INPUT_LINE="The input points for this question are the CSV at ${INPUT}. "

PROMPT="You have connector tools in /opt/data/connectors/ for live geospatial \
conservation data. READ /opt/data/connectors/PLAYBOOK.md FIRST — it gives the \
pattern (points -> annotate -> group) and lists the connectors; each has a \
<name>.md card and a --describe. Prefer the connectors and NEVER guess a class \
code or band name. If (and only if) no connector covers what the question needs, \
you may write Earth Engine code yourself as a last resort (import ee; \
ee.Initialize(project='plantwars')). ${INPUT_LINE}Question: ${QUESTION} \
Report which connectors you called, and if you wrote any Earth Engine code, show it."

start=$(date +%s)
timeout "$TIMEOUT" docker run --rm --network host \
  -v "$HOME/.hermes:/opt/data" \
  -v "$CONN_DIR:/opt/data/connectors:ro" \
  -v "$SB/queries/data:/opt/data/query_data:ro" \
  -e HOME=/opt/data \
  "$IMAGE" chat -q "$PROMPT" 2>&1 | tee "$LOG"
rc="${PIPESTATUS[0]}"
end=$(date +%s); dur=$((end - start))

# --- struggle detector (NOTES §5) — factored out so it can be re-scored ---
verdict="$("$HERE/detect_struggle.sh" "$LOG" "$rc" "$dur" "$T_STRUGGLE")"

echo
echo "=========================================================="
echo "RUN_ID=$RUN_ID  rc=$rc  wall=${dur}s  log=$LOG"
echo "$verdict"
echo "=========================================================="
