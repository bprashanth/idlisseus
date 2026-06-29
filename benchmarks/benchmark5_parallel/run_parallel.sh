#!/bin/bash
# Benchmark 5: Parallel ds4 + Seed-OSS-AWQ smoke test.
#
# Phases:
#   1. Smoke: N concurrent LLM requests to each endpoint, measure queuing vs throughput
#   2. Agent: hermes+ds4 vs hermes+seed-oss-awq run the same dashboard task simultaneously
#
# Prerequisites:
#   - ds4 running in SSD streaming mode on 172.17.0.1:8000
#   - hermes-agent-local image built
#   - AWQ weights at ~/models/Seed-OSS-36B-AWQ/
# Seed-OSS is started by this script AFTER ds4 smoke (to avoid OOM during ds4 warmup)
#
# Run: bash benchmark5_parallel/run_parallel.sh

set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
RESULTS="$REPO/benchmark5_parallel/results_$(date +%Y%m%d_%H%M%S)"
DS4_URL="http://172.17.0.1:8000/v1"
SEED_URL="http://172.17.0.1:8001/v1"
MAX_AGENT_SECONDS=1800  # 30 min per agent

DATASET_URL="https://raw.githubusercontent.com/mwaskom/seaborn-data/master/iris.csv"
# Notes on the container environment:
#   - Writable volume is mounted at /opt/data/ (NOT /opt/hermes/ which is read-only)
#   - pandas/plotly/matplotlib are NOT installed; use Python stdlib + Chart.js via CDN
#   - Use terminal (bash) to download files and write scripts; execute_code has no network
AGENT_PROMPT="Your writable working directory is /opt/data/ — save all output files there. \
Download the Iris CSV from ${DATASET_URL} using curl or wget to /opt/data/iris.csv. \
Then, using the terminal tool (bash), write a Python script at /opt/data/gen_dashboard.py \
that reads the CSV with Python stdlib (csv and json modules only — pandas is not installed), \
computes per-species counts and summary stats, and generates a self-contained HTML file at \
/opt/data/dashboard.html. The HTML must include four inline Chart.js visualisations loaded \
from https://cdn.jsdelivr.net/npm/chart.js: (1) species count bar chart, (2) petal length \
vs petal width scatter coloured by species, (3) sepal length histogram, (4) a summary \
statistics table. Run the script with 'python3 /opt/data/gen_dashboard.py' and confirm \
dashboard.html exists. Do NOT use pandas, plotly, or matplotlib — they are not installed."

SEED_WEIGHTS="$HOME/models/Seed-OSS-36B-AWQ"
SEED_DEPLOY="$(dirname "$0")/../deploy/seed-oss-36b-awq/run.sh"

die() { echo "ERROR: $*" >&2; exit 1; }
log() { echo "[$(date '+%H:%M:%S')] $*"; }

mkdir -p "$RESULTS"

# ── Pre-flight ──────────────────────────────────────────────────────────────
log "Pre-flight checks..."
curl -sf "$DS4_URL/models" >/dev/null 2>&1 || die "ds4 not responding at $DS4_URL"
DS4_MODEL=$(curl -sf "$DS4_URL/models" | python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])")
log "  ds4:  $DS4_MODEL @ $DS4_URL"
log "  memory: $(free -h | awk '/^Mem/{print $3"/"$2}')"
docker images hermes-agent-local --format "{{.Tag}}" | grep -q latest \
  || die "hermes-agent-local not built"
[ -f "$SEED_WEIGHTS/config.json" ] || die "AWQ weights not found at $SEED_WEIGHTS"

# ── Phase 1: Smoke — warm ds4 first, THEN start Seed-OSS ────────────────────
# ds4 spikes above its 83 GB steady state while warming (4 concurrent KV caches
# at ctx=65536). Starting Seed-OSS afterwards avoids the combined OOM.
log "=== PHASE 1: SMOKE TEST (concurrent requests) ==="
SMOKE_PROMPT='{"messages":[{"role":"user","content":"List 5 species of birds, one per line, no commentary."}],"max_tokens":100}'

run_smoke() {
  local name=$1 url=$2 model=$3 n=${4:-4}
  local req="{\"model\":\"$model\",${SMOKE_PROMPT:1}"
  log "  $name: firing $n concurrent requests..."
  local start=$(date +%s%3N)
  local pids=()
  for i in $(seq 1 $n); do
    curl -sf -X POST -H "Content-Type: application/json" -d "$req" \
      "$url/chat/completions" \
      -o "$RESULTS/smoke_${name}_r${i}.json" &
    pids+=($!)
  done
  for pid in "${pids[@]}"; do wait "$pid" || true; done
  local end=$(date +%s%3N)
  local elapsed=$(( end - start ))
  local ok=$(ls "$RESULTS/smoke_${name}_r"*.json 2>/dev/null | wc -l)
  log "  $name: $ok/$n completed in ${elapsed}ms"
  echo "${name}_smoke_ms=${elapsed}" >> "$RESULTS/metrics.txt"
  echo "${name}_smoke_ok=${ok}" >> "$RESULTS/metrics.txt"
}

run_smoke "ds4"  "$DS4_URL"  "$DS4_MODEL"  4

log "Memory after ds4 smoke: $(free -h | awk '/^Mem/{print $3"/"$2}')"

# ds4 is now warm (~83 GB). Start Seed-OSS — stop any stale container first.
log "Starting Seed-OSS AWQ container (ds4 now warm)..."
docker stop seed-oss-awq-vllm 2>/dev/null || true
docker rm   seed-oss-awq-vllm 2>/dev/null || true
bash "$SEED_DEPLOY"

log "Waiting for Seed-OSS to be ready..."
for i in $(seq 1 60); do
  curl -sf "$SEED_URL/models" >/dev/null 2>&1 && break
  [ "$i" -eq 60 ] && die "Seed-OSS not ready after 300s"
  sleep 5
done
SEED_MODEL=$(curl -sf "$SEED_URL/models" | python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])")
log "  seed: $SEED_MODEL @ $SEED_URL"
log "Memory after Seed-OSS start: $(free -h | awk '/^Mem/{print $3"/"$2}')"

run_smoke "seed" "$SEED_URL" "$SEED_MODEL" 4

log "Memory after all smoke: $(free -h | awk '/^Mem/{print $3"/"$2}')"

# ── Phase 2: Agent — parallel dashboard tasks ────────────────────────────────
log "=== PHASE 2: AGENT TASK (parallel hermes instances) ==="

# Create isolated Hermes home dirs
DS4_HOME="$HOME/.hermes-bench-ds4"
SEED_HOME="$HOME/.hermes-bench-seed"

setup_hermes_home() {
  local src="$HOME/.hermes" dst=$1 model=$2 base_url=$3
  sudo rm -rf "$dst"
  sudo cp -r "$src" "$dst" 2>/dev/null || true
  sudo chown -R 10000:10000 "$dst"
  sudo chmod -R u+rwX "$dst"
  # Point at target model, blank environment_hint (run as root since dir owned by 10000)
  sudo python3 - "$dst/config.yaml" "$model" "$base_url" <<'PYEOF'
import sys, yaml
path, model, base_url = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path) as f:
    cfg = yaml.safe_load(f)
cfg['model']['default'] = model
cfg['model']['provider'] = 'custom'
cfg['model']['base_url'] = base_url
cfg.setdefault('agent', {})['environment_hint'] = ''
for k, v in cfg.get('auxiliary', {}).items():
    if isinstance(v, dict):
        v['provider'] = 'custom'
        v['model'] = model
        v['base_url'] = base_url
with open(path, 'w') as f:
    yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
PYEOF
}

log "Setting up isolated Hermes home dirs..."
setup_hermes_home "$DS4_HOME"  "$DS4_MODEL"  "$DS4_URL"
setup_hermes_home "$SEED_HOME" "$SEED_MODEL" "$SEED_URL"

# Ensure clean working dirs
sudo rm -rf "$DS4_HOME/iris_dashboard"  "$SEED_HOME/iris_dashboard" 2>/dev/null || true

log "Launching both agents simultaneously..."
START_AGENT=$(date +%s)

timeout "$MAX_AGENT_SECONDS" docker run --rm \
  -v "$DS4_HOME:/opt/data" \
  --network host \
  --name hermes-bench-ds4 \
  hermes-agent-local chat -q "$AGENT_PROMPT" \
  > "$RESULTS/transcript_ds4.log" 2>&1 &
PID_DS4=$!

timeout "$MAX_AGENT_SECONDS" docker run --rm \
  -v "$SEED_HOME:/opt/data" \
  --network host \
  --name hermes-bench-seed \
  hermes-agent-local chat -q "$AGENT_PROMPT" \
  > "$RESULTS/transcript_seed.log" 2>&1 &
PID_SEED=$!

log "  ds4  agent PID: $PID_DS4"
log "  seed agent PID: $PID_SEED"

# Monitor memory every 30s while agents run
log "Monitoring memory (every 30s)..."
(
  while kill -0 $PID_DS4 2>/dev/null || kill -0 $PID_SEED 2>/dev/null; do
    echo "$(date +%H:%M:%S) mem=$(free -h | awk '/^Mem/{print $3"/"$2}')" \
      >> "$RESULTS/memory_log.txt"
    sleep 30
  done
) &
MEM_PID=$!

wait $PID_DS4 || true
DS4_EXIT=$?
DS4_ELAPSED=$(( $(date +%s) - START_AGENT ))

wait $PID_SEED || true
SEED_EXIT=$?
SEED_ELAPSED=$(( $(date +%s) - START_AGENT ))

kill $MEM_PID 2>/dev/null || true

log "ds4 agent done: exit=$DS4_EXIT, ${DS4_ELAPSED}s"
log "seed agent done: exit=$SEED_EXIT, ${SEED_ELAPSED}s"

# Collect outputs — agent writes to /opt/data/ which is mounted from DS4_HOME/SEED_HOME
mkdir -p "$RESULTS/ds4_output" "$RESULTS/seed_output"
sudo cp "$DS4_HOME/dashboard.html"        "$RESULTS/ds4_output/"  2>/dev/null || true
sudo cp "$DS4_HOME/gen_dashboard.py"      "$RESULTS/ds4_output/"  2>/dev/null || true
sudo cp "$DS4_HOME/iris.csv"              "$RESULTS/ds4_output/"  2>/dev/null || true
sudo cp "$SEED_HOME/dashboard.html"       "$RESULTS/seed_output/" 2>/dev/null || true
sudo cp "$SEED_HOME/gen_dashboard.py"     "$RESULTS/seed_output/" 2>/dev/null || true
sudo cp "$SEED_HOME/iris.csv"             "$RESULTS/seed_output/" 2>/dev/null || true
sudo chown -R beeps:beeps "$RESULTS/"

echo "ds4_agent_seconds=${DS4_ELAPSED}"  >> "$RESULTS/metrics.txt"
echo "seed_agent_seconds=${SEED_ELAPSED}" >> "$RESULTS/metrics.txt"

DS4_DASH=$(find "$RESULTS/ds4_output"  -name "*.html" 2>/dev/null | head -1)
SEED_DASH=$(find "$RESULTS/seed_output" -name "*.html" 2>/dev/null | head -1)
DS4_DASH_STATUS=$([ -n "$DS4_DASH"  ] && echo "YES ($DS4_DASH)"  || echo "NO")
SEED_DASH_STATUS=$([ -n "$SEED_DASH" ] && echo "YES ($SEED_DASH)" || echo "NO")

echo ""
echo "=== RESULTS ==="
echo "  Model         Time    Dashboard"
echo "  ds4-flash     ${DS4_ELAPSED}s   $DS4_DASH_STATUS"
echo "  seed-oss-awq  ${SEED_ELAPSED}s   $SEED_DASH_STATUS"
echo ""
echo "Peak memory log: $RESULTS/memory_log.txt"
echo "Transcripts:     $RESULTS/transcript_ds4.log"
echo "                 $RESULTS/transcript_seed.log"
log "Done. Results: $RESULTS/"
