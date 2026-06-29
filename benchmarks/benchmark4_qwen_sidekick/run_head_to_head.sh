#!/bin/bash
# Head-to-head benchmark: ds4-flash vs Qwen3-Next-80B-A3B-FP8 via Hermes Agent.
#
# Both models run the identical wildfire research task with a fresh workspace
# (no pre-downloaded files, no B2 corpus, no stale wildfire dirs visible).
# ds4 runs first (already on-machine, no download), then Qwen3-Next-80B.
#
# Results land in:
#   benchmark4_qwen_sidekick/head_to_head_ds4/
#   benchmark4_qwen_sidekick/head_to_head_qwen/
#
# Requires:
#   - ds4 running (sudo systemctl status ds4)
#   - qwen-big-vllm container image and weights at ~/models/Qwen3-Next-80B-FP8/
#   - hermes-token-proxy service installed (see docs/hermes-token-proxy.md)
#
# Hard time limit per run: 90 minutes.  Both models are let run to completion or
# until the limit, whichever comes first.

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
RESULTS_DS4="$REPO/benchmark4_qwen_sidekick/head_to_head_ds4"
RESULTS_QWEN="$REPO/benchmark4_qwen_sidekick/head_to_head_qwen"
PROXY_URL="http://172.17.0.1:8001/v1"
VLLM_URL="http://172.17.0.1:8000/v1"
MAX_SECONDS=5400    # 90 min hard kill per run

WILDFIRE_PROMPT="Research wildfire risk interventions for the Nilgiris and Himalayan region. \
Find and download roughly 10 relevant papers and a few reports (a few reliable starting points: \
Zenodo, and NGO publications on wildfire/forest-fire management in this region — but don't limit \
yourself to those). Save everything you download to a stable local directory. Then answer: what \
interventions are supported by evidence? What disagreements exist in the literature? What would \
you recommend measuring? Support your claims with a dashboard. Include citations."

die() { echo "ERROR: $*" >&2; exit 1; }
log() { echo "[$(date '+%H:%M:%S')] $*"; }

# ─── pre-flight ───────────────────────────────────────────────────────────────

log "Pre-flight checks..."

# ds4 must be up
curl -sf "$VLLM_URL/models" | python3 -c "
import sys, json; d=json.load(sys.stdin)
ids = [m['id'] for m in d['data']]
assert any('deepseek' in i for i in ids), f'ds4 not serving, got: {ids}'
print('  ds4 OK:', ids)
" || die "ds4 not running or not serving deepseek — run: sudo systemctl start ds4"

# proxy must be up
curl -sf "http://172.17.0.1:8001/v1/models" >/dev/null 2>&1 \
  || die "Token proxy not running on :8001 — run: sudo systemctl start hermes-token-proxy"
log "  proxy OK"

# Qwen weights must be present
[ -f "$HOME/models/Qwen3-Next-80B-FP8/config.json" ] \
  || die "Qwen3-Next-80B weights not found at ~/models/Qwen3-Next-80B-FP8/"
log "  Qwen weights OK"

# ─── isolate workspace ─────────────────────────────────────────────────────────
# Move any existing wildfire dirs so the model starts completely fresh.
# The model must not see B2's pre-downloaded corpus or any prior run's files.

log "Archiving stale wildfire dirs in ~/.hermes/ ..."
ARCHIVE_TS=$(date +%Y%m%d_%H%M%S)
for d in wildfire_research wildfire_bk4_nemotron_nsp wildfire_bk5_qwen_nxt_v3 \
          wildfire_research_bk2_nemotron wildfire_research_bk3_qwen_nxt wildfire_research_ds4_run; do
  if sudo test -e "/home/beeps/.hermes/$d"; then
    sudo mv "/home/beeps/.hermes/$d" "/home/beeps/.hermes/archived_${ARCHIVE_TS}_$d"
    log "  archived $d"
  fi
done

# Take a pre-benchmark security snapshot
log "Taking pre-benchmark security snapshot..."
mkdir -p "$RESULTS_DS4" "$RESULTS_QWEN"
dpkg --get-selections | sort > "$RESULTS_DS4/../pre_benchmark_dpkg.txt"
sudo find /home/beeps/.hermes/skills /home/beeps/.hermes/hooks 2>/dev/null | sort \
  > "$RESULTS_DS4/../pre_benchmark_hermes_files.txt"
touch "$RESULTS_DS4/../pre_benchmark_marker"
log "  snapshot saved"

# ─── RUN 1: ds4-flash ──────────────────────────────────────────────────────────

log "=== RUN 1: ds4-flash ==="
log "Pointing Hermes at ds4 via proxy..."
sudo python3 "$REPO/deploy/hermes/point_at_model.py" deepseek-v4-flash "$PROXY_URL"
curl -sf "http://172.17.0.1:8001/v1/models" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('  Hermes will use:', d['data'][0]['id'])"

DS4_START=$(date +%s)
log "Launching Hermes wildfire task for ds4 (limit: ${MAX_SECONDS}s)..."

timeout "$MAX_SECONDS" docker run --rm \
  -v /home/beeps/.hermes:/opt/data \
  --network host \
  --name hermes-head-to-head \
  nousresearch/hermes-agent chat -q "$WILDFIRE_PROMPT" \
  > "$RESULTS_DS4/transcript.log" 2>&1 || true

DS4_END=$(date +%s)
DS4_ELAPSED=$(( DS4_END - DS4_START ))
log "ds4 run ended after ${DS4_ELAPSED}s (limit: ${MAX_SECONDS}s)"

# Collect results
sudo cp -r /home/beeps/.hermes/wildfire_research "$RESULTS_DS4/wildfire_research" 2>/dev/null || true
sudo chown -R beeps:beeps "$RESULTS_DS4/wildfire_research" 2>/dev/null || true
echo "$DS4_ELAPSED" > "$RESULTS_DS4/elapsed_seconds.txt"

log "ds4 files downloaded:"
find "$RESULTS_DS4/wildfire_research" -type f 2>/dev/null | wc -l || echo "  0"
find "$RESULTS_DS4/wildfire_research" -type f 2>/dev/null | xargs ls -lh 2>/dev/null | awk '{print "  "$5, $9}' || true

# Archive wildfire dir before qwen run
log "Archiving ds4 wildfire dir before Qwen run..."
sudo mv /home/beeps/.hermes/wildfire_research \
        "/home/beeps/.hermes/h2h_ds4_${ARCHIVE_TS}" 2>/dev/null || true

# ─── RUN 2: Qwen3-Next-80B ─────────────────────────────────────────────────────

log "=== RUN 2: Qwen3-Next-80B ==="
log "Stopping ds4..."
sudo systemctl stop ds4
sleep 5

log "Starting qwen-big-vllm container..."
bash "$REPO/deploy/qwen3-next-80b/run.sh"

log "Waiting for vLLM to be ready (model load ~9 min)..."
for i in $(seq 1 60); do
  if curl -sf "$VLLM_URL/models" | python3 -c \
      "import sys,json; d=json.load(sys.stdin); assert any('qwen' in m['id'] for m in d['data'])" \
      2>/dev/null; then
    log "  vLLM ready after ~$((i*15))s"
    break
  fi
  sleep 15
done
curl -sf "$VLLM_URL/models" | python3 -c "import sys,json; d=json.load(sys.stdin); print('  serving:', d['data'][0]['id'])"

log "Pointing Hermes at qwen3-next-80b via proxy..."
sudo python3 "$REPO/deploy/hermes/point_at_model.py" qwen3-next-80b "$PROXY_URL"

QWEN_START=$(date +%s)
log "Launching Hermes wildfire task for Qwen3-Next-80B (limit: ${MAX_SECONDS}s)..."

timeout "$MAX_SECONDS" docker run --rm \
  -v /home/beeps/.hermes:/opt/data \
  --network host \
  --name hermes-head-to-head \
  nousresearch/hermes-agent chat -q "$WILDFIRE_PROMPT" \
  > "$RESULTS_QWEN/transcript.log" 2>&1 || true

QWEN_END=$(date +%s)
QWEN_ELAPSED=$(( QWEN_END - QWEN_START ))
log "Qwen run ended after ${QWEN_ELAPSED}s (limit: ${MAX_SECONDS}s)"

# Collect results
sudo cp -r /home/beeps/.hermes/wildfire_research "$RESULTS_QWEN/wildfire_research" 2>/dev/null || true
sudo chown -R beeps:beeps "$RESULTS_QWEN/wildfire_research" 2>/dev/null || true
echo "$QWEN_ELAPSED" > "$RESULTS_QWEN/elapsed_seconds.txt"

log "Qwen files downloaded:"
find "$RESULTS_QWEN/wildfire_research" -type f 2>/dev/null | wc -l || echo "  0"
find "$RESULTS_QWEN/wildfire_research" -type f 2>/dev/null | xargs ls -lh 2>/dev/null | awk '{print "  "$5, $9}' || true

# ─── restore machine ───────────────────────────────────────────────────────────

log "Restoring machine to steady state..."
docker stop qwen-big-vllm 2>/dev/null || true
sleep 3
sudo systemctl start ds4
sudo python3 "$REPO/deploy/hermes/point_at_model.py" deepseek-v4-flash "$PROXY_URL"
sudo systemctl stop hermes-token-proxy
log "  ds4 restored, proxy stopped"

# ─── security audit ────────────────────────────────────────────────────────────

log "Running post-benchmark security audit..."
bash "$REPO/benchmark4_qwen_sidekick/post_benchmark_audit.sh" \
  "$RESULTS_DS4/../pre_benchmark_dpkg.txt" \
  "$RESULTS_DS4/../pre_benchmark_hermes_files.txt" \
  "$RESULTS_DS4/../pre_benchmark_marker" \
  "$REPO/benchmark4_qwen_sidekick/security_audit_${ARCHIVE_TS}.txt"

# ─── summary ───────────────────────────────────────────────────────────────────

log "=== HEAD-TO-HEAD RESULTS ==="
DS4_FILES=$(find "$RESULTS_DS4/wildfire_research" -type f 2>/dev/null | wc -l || echo 0)
QWEN_FILES=$(find "$RESULTS_QWEN/wildfire_research" -type f 2>/dev/null | wc -l || echo 0)
DS4_MIN=$(( DS4_ELAPSED / 60 ))
QWEN_MIN=$(( QWEN_ELAPSED / 60 ))
DS4_DASH=$([ -f "$RESULTS_DS4/wildfire_research/wildfire_dashboard.html" ] && echo "YES" || echo "NO")
QWEN_DASH=$([ -f "$RESULTS_QWEN/wildfire_research/wildfire_dashboard.html" ] && echo "YES" || echo "NO")
DS4_LIMIT=$([ "$DS4_ELAPSED" -ge "$MAX_SECONDS" ] && echo " (HIT LIMIT)" || echo "")
QWEN_LIMIT=$([ "$QWEN_ELAPSED" -ge "$MAX_SECONDS" ] && echo " (HIT LIMIT)" || echo "")

echo ""
echo "  Model              Time         Files  Dashboard"
echo "  ds4-flash          ${DS4_MIN}min${DS4_LIMIT}    ${DS4_FILES}      ${DS4_DASH}"
echo "  qwen3-next-80b     ${QWEN_MIN}min${QWEN_LIMIT}    ${QWEN_FILES}      ${QWEN_DASH}"
echo ""
echo "  Transcripts:  $RESULTS_DS4/transcript.log"
echo "                $RESULTS_QWEN/transcript.log"
echo "  Audit:        $REPO/benchmark4_qwen_sidekick/security_audit_${ARCHIVE_TS}.txt"
log "Done."
