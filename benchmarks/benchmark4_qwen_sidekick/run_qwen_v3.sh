#!/bin/bash
# Qwen3-Next-80B wildfire benchmark v3: empty environment_hint.
# Goal: see what strategy the model adopts without any tool/SSL guidance.
# Fixes v2 integrity bug: archives BOTH wildfire dirs before the run.
# Restores environment_hint after the run regardless of outcome.

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
RESULTS="$REPO/benchmark4_qwen_sidekick/head_to_head_qwen_v3"
PROXY_URL="http://172.17.0.1:8001/v1"
VLLM_URL="http://172.17.0.1:8000/v1"
MAX_SECONDS=5400   # 90 min

WILDFIRE_PROMPT="Research wildfire risk interventions for the Nilgiris and Himalayan region. \
Find and download roughly 10 relevant papers and a few reports (a few reliable starting points: \
Zenodo, and NGO publications on wildfire/forest-fire management in this region — but don't limit \
yourself to those). Save everything you download to a stable local directory. Then answer: what \
interventions are supported by evidence? What disagreements exist in the literature? What would \
you recommend measuring? Support your claims with a dashboard. Include citations."

die() { echo "ERROR: $*" >&2; exit 1; }
log() { echo "[$(date '+%H:%M:%S')] $*"; }

mkdir -p "$RESULTS"

log "Pre-flight..."
docker images hermes-agent-local --format "{{.Tag}}" | grep -q latest \
  || die "hermes-agent-local not built — run: bash agents/hermes/build.sh"
[ -f "$HOME/models/Qwen3-Next-80B-FP8/config.json" ] \
  || die "Qwen weights not found at ~/models/Qwen3-Next-80B-FP8/"

log "Saving and clearing environment_hint..."
SAVED_HINT=$(sudo python3 -c "
import yaml
with open('/home/beeps/.hermes/config.yaml') as f:
    cfg = yaml.safe_load(f)
print(cfg.get('agent', {}).get('environment_hint', ''))
")
echo "$SAVED_HINT" > "$RESULTS/saved_environment_hint.txt"

sudo python3 -c "
import yaml
path = '/home/beeps/.hermes/config.yaml'
with open(path) as f:
    cfg = yaml.safe_load(f)
cfg.setdefault('agent', {})['environment_hint'] = ''
with open(path, 'w') as f:
    yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
"
log "  hint cleared"

restore_hint() {
  log "Restoring environment_hint..."
  HINT_CONTENT=$(cat "$RESULTS/saved_environment_hint.txt")
  sudo python3 -c "
import yaml, sys
path = '/home/beeps/.hermes/config.yaml'
with open(path) as f:
    cfg = yaml.safe_load(f)
cfg.setdefault('agent', {})['environment_hint'] = sys.stdin.read()
with open(path, 'w') as f:
    yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
" <<< "$HINT_CONTENT"
  log "  hint restored"
}
trap restore_hint EXIT

log "Starting proxy..."
sudo systemctl start hermes-token-proxy
for i in $(seq 1 10); do
  curl -sf "http://172.17.0.1:8001/v1/models" >/dev/null 2>&1 && break
  [ $i -eq 10 ] && die "Proxy did not respond after 10s"
  sleep 1
done
log "  proxy OK"

log "Archiving existing wildfire dirs (both paths)..."
ARCHIVE_TS=$(date +%Y%m%d_%H%M%S)
sudo test -e /home/beeps/.hermes/wildfire_research \
  && sudo mv /home/beeps/.hermes/wildfire_research \
             "/home/beeps/.hermes/archived_qwenv3_top_${ARCHIVE_TS}" \
  || true
sudo test -e /home/beeps/.hermes/home/wildfire-research \
  && sudo mv /home/beeps/.hermes/home/wildfire-research \
             "/home/beeps/.hermes/archived_qwenv3_home_${ARCHIVE_TS}" \
  || true
log "  archived (ts=$ARCHIVE_TS)"

log "Stopping ds4..."
sudo systemctl stop ds4
sleep 3

log "Starting qwen-big-vllm..."
bash "$REPO/deploy/qwen3-next-80b/run.sh"

log "Waiting for vLLM ready (up to 15 min)..."
for i in $(seq 1 60); do
  if curl -sf "$VLLM_URL/models" 2>/dev/null \
      | python3 -c "import sys,json; d=json.load(sys.stdin); assert any('qwen' in m['id'] for m in d['data'])" 2>/dev/null; then
    log "  ready after ~$((i*15))s"
    break
  fi
  [ $i -eq 60 ] && die "vLLM did not become ready in 15 min"
  sleep 15
done
curl -sf "$VLLM_URL/models" | python3 -c "import sys,json; d=json.load(sys.stdin); print('  serving:', d['data'][0]['id'])"

log "Pointing Hermes at qwen3-next-80b via proxy..."
sudo python3 "$REPO/deploy/hermes/point_at_model.py" qwen3-next-80b "$PROXY_URL"

log "Launching Hermes wildfire task (hermes-agent-local, empty hint, limit: ${MAX_SECONDS}s)..."
START=$(date +%s)

timeout "$MAX_SECONDS" docker run --rm \
  -v /home/beeps/.hermes:/opt/data \
  --network host \
  --name hermes-qwen-v3 \
  hermes-agent-local chat -q "$WILDFIRE_PROMPT" \
  > "$RESULTS/transcript.log" 2>&1 || true

END=$(date +%s)
ELAPSED=$(( END - START ))
echo "$ELAPSED" > "$RESULTS/elapsed_seconds.txt"
log "Run ended after ${ELAPSED}s ($((ELAPSED/60)) min)"

log "Collecting files..."
sudo cp -r /home/beeps/.hermes/wildfire_research "$RESULTS/wildfire_research" 2>/dev/null || true
sudo cp -r /home/beeps/.hermes/home/wildfire-research "$RESULTS/wildfire_research_home" 2>/dev/null || true
sudo chown -R beeps:beeps "$RESULTS/" 2>/dev/null || true

log "Files produced:"
find "$RESULTS" \( -name "*.pdf" -o -name "*.html" -o -name "*.md" -o -name "*.json" \) 2>/dev/null \
  | grep -v transcript | grep -v saved_environment | xargs ls -lh 2>/dev/null \
  | awk '{print "  "$5, $9}' || echo "  (none)"

log "Restoring machine (ds4)..."
docker stop qwen-big-vllm 2>/dev/null || true
sleep 3
sudo systemctl start ds4
sudo python3 "$REPO/deploy/hermes/point_at_model.py" deepseek-v4-flash "$PROXY_URL"
sudo systemctl stop hermes-token-proxy
log "  ds4 restored, proxy stopped"

PDFS=$(find "$RESULTS" -name "*.pdf" 2>/dev/null | wc -l)
DASH=$(find "$RESULTS" -name "*.html" 2>/dev/null | grep -qi dashboard && echo YES || echo NO)
echo ""
echo "=== v3 SUMMARY ==="
echo "  Time:      $((ELAPSED/60))min"
echo "  PDFs:      $PDFS"
echo "  Dashboard: $DASH"
log "Done. Transcript: $RESULTS/transcript.log"
