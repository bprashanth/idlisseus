#!/bin/bash
# Benchmark 6: Chatbot quality + speed comparison.
#
# Phases:
#   1. ds4 alone        (deepseek-v4-flash, SSD streaming, port 8000)
#   2. ds4 + sidekick   (ds4 on 8000, Qwen3.5-2B on 8001 via vLLM)
#   3. 80B alone        (Qwen3-Next-80B FP8, port 8001, ds4 stopped)
#
# Each phase runs:
#   a) 3-turn conversation (invasive plants / restoration)
#   b) 2 concurrent users (same Turn 1, fired simultaneously)
#
# Usage: bash benchmark6_chatbot/run_chatbot_bench.sh [phase]
#   phase: 1, 2, or 3 (default: run all)

set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
RESULTS="$REPO/benchmark6_chatbot/results_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS"

SIDEKICK_WEIGHTS="$HOME/.cache/huggingface/hub/models--Qwen--Qwen3.5-2B/snapshots/15852e8c16360a2fea060d615a32b45270f8a8fc"
QWEN80B_WEIGHTS="$HOME/models/Qwen3-Next-80B-FP8"
DS4_URL="http://172.17.0.1:8000/v1"
PORT2_URL="http://172.17.0.1:8001/v1"

SYSTEM_PROMPT="You are an ecologist specialising in habitat restoration and invasive species management. Be concise but substantive — 3-5 sentences per answer."
TURN1="What makes invasive plants so difficult to eradicate once they establish in a new habitat?"
TURN2="Which restoration approaches have shown lasting success after invasive plant removal, and what made them work?"
TURN3="A land trust has one season and a small volunteer crew to begin restoring a meadow overrun by Japanese knotweed. What would you prioritise and why?"
MAX_TOKENS=512

die()  { echo "ERROR: $*" >&2; exit 1; }
log()  { echo "[$(date '+%H:%M:%S')] $*"; }
sep()  { echo ""; echo "── $* ────────────────────────────────────────"; }

# ── Core benchmark function ─────────────────────────────────────────────────
# run_bench LABEL URL MODEL OUTFILE
run_bench() {
  local label=$1 url=$2 model=$3 out=$4
  log "Starting 3-turn conversation: $label ($model)"

  python3 - "$label" "$url" "$model" "$out" \
    "$SYSTEM_PROMPT" "$TURN1" "$TURN2" "$TURN3" "$MAX_TOKENS" << 'PYEOF'
import sys, json, time, textwrap, urllib.request

label, url, model, out = sys.argv[1:5]
system, t1, t2, t3 = sys.argv[5:9]
max_tok = int(sys.argv[9])
turns  = [t1, t2, t3]
history = []
records = []

def chat(url, model, history, user_msg, max_tokens):
    msgs = [{"role":"system","content":system}] + history + [{"role":"user","content":user_msg}]
    body = json.dumps({"model":model,"messages":msgs,"max_tokens":max_tokens,"temperature":0.7}).encode()
    req  = urllib.request.Request(url+"/chat/completions", data=body,
                                  headers={"Content-Type":"application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.load(r)
    elapsed = time.time() - t0
    msg     = d["choices"][0]["message"]
    content = msg.get("content") or ""
    usage   = d.get("usage", {})
    return content, elapsed, usage

for i, q in enumerate(turns, 1):
    print(f"\n  Turn {i}: {q}")
    content, elapsed, usage = chat(url, model, history, q, max_tok)
    history += [{"role":"user","content":q},{"role":"assistant","content":content}]
    ptok = usage.get("prompt_tokens","?")
    ctok = usage.get("completion_tokens","?")
    print(f"  ⏱  {elapsed:.0f}s | prompt={ptok} completion={ctok}")
    print(textwrap.fill(content, 76, initial_indent="  → ", subsequent_indent="    "))
    records.append({"turn":i,"question":q,"answer":content,"elapsed_s":round(elapsed,1),
                    "prompt_tokens":ptok,"completion_tokens":ctok})

total = sum(r["elapsed_s"] for r in records)
print(f"\n  Total: {total:.0f}s for 3 turns ({total/3:.0f}s avg)")
with open(out, "w") as f:
    json.dump({"label":label,"model":model,"url":url,"turns":records,"total_s":total}, f, indent=2)
PYEOF
}

# ── Concurrency test ────────────────────────────────────────────────────────
# run_concurrency LABEL URL1 MODEL1 URL2 MODEL2 OUTFILE
# Fires Turn1 simultaneously to both endpoints, reports wall times.
run_concurrency() {
  local label=$1 url1=$2 m1=$3 url2=$4 m2=$5 out=$6
  log "Concurrency test: $label — 2 simultaneous users"

  python3 - "$label" "$url1" "$m1" "$url2" "$m2" "$out" \
    "$SYSTEM_PROMPT" "$TURN1" "$MAX_TOKENS" << 'PYEOF'
import sys, json, time, urllib.request
from threading import Thread

label, url1, m1, url2, m2, out = sys.argv[1:7]
system, question, max_tok = sys.argv[7], sys.argv[8], int(sys.argv[9])

results = {}

def fire(key, url, model):
    msgs = [{"role":"system","content":system},{"role":"user","content":question}]
    body = json.dumps({"model":model,"messages":msgs,"max_tokens":max_tok,"temperature":0.7}).encode()
    req  = urllib.request.Request(url+"/chat/completions", data=body,
                                  headers={"Content-Type":"application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            d = json.load(r)
        elapsed = time.time() - t0
        content = d["choices"][0]["message"].get("content") or ""
        ctok    = d.get("usage",{}).get("completion_tokens","?")
        results[key] = {"elapsed_s":round(elapsed,1),"completion_tokens":ctok,"answer":content,"ok":True}
    except Exception as e:
        results[key] = {"elapsed_s":round(time.time()-t0,1),"error":str(e),"ok":False}

t_start = time.time()
threads = [
    Thread(target=fire, args=("user_a", url1, m1)),
    Thread(target=fire, args=("user_b", url2, m2)),
]
for t in threads: t.start()
for t in threads: t.join()
wall = time.time() - t_start

for key, r in results.items():
    tag = "user_a→"+m1 if key=="user_a" else "user_b→"+m2
    if r["ok"]:
        print(f"  {tag}: {r['elapsed_s']}s ({r['completion_tokens']} tokens)")
    else:
        print(f"  {tag}: ERROR — {r['error']}")
print(f"  Wall time (both done): {wall:.0f}s")

with open(out, "w") as f:
    json.dump({"label":label,"wall_s":round(wall,1),"results":results}, f, indent=2)
PYEOF
}

wait_ready() {
  local url=$1 label=$2
  log "Waiting for $label..."
  for i in $(seq 1 72); do
    curl -sf "$url/models" >/dev/null 2>&1 && log "$label ready" && return 0
    sleep 5
  done
  die "$label never became ready"
}

PHASE=${1:-all}

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 1 — ds4 alone
# ══════════════════════════════════════════════════════════════════════════════
if [[ "$PHASE" == "1" || "$PHASE" == "all" ]]; then
  sep "PHASE 1: ds4 alone"
  curl -sf "$DS4_URL/models" >/dev/null 2>&1 || die "ds4 not running at $DS4_URL"
  DS4_MODEL=$(curl -sf "$DS4_URL/models" | python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])")
  log "ds4 model: $DS4_MODEL"
  log "RAM: $(free -h | awk '/^Mem/{print $3"/"$2}')"

  run_bench "ds4-alone" "$DS4_URL" "$DS4_MODEL" "$RESULTS/phase1_conversation.json"

  # Concurrency: 2 users both hitting ds4 (shows queuing)
  run_concurrency "ds4-alone-concurrent" \
    "$DS4_URL" "$DS4_MODEL" "$DS4_URL" "$DS4_MODEL" \
    "$RESULTS/phase1_concurrent.json"

  log "Phase 1 done. RAM: $(free -h | awk '/^Mem/{print $3"/"$2}')"
fi

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — ds4 + sidekick (Qwen3.5-2B)
# ══════════════════════════════════════════════════════════════════════════════
if [[ "$PHASE" == "2" || "$PHASE" == "all" ]]; then
  sep "PHASE 2: ds4 + sidekick (Qwen3.5-2B)"

  docker stop sidekick-vllm 2>/dev/null || true
  docker rm   sidekick-vllm 2>/dev/null || true
  docker stop seed-oss-awq-vllm 2>/dev/null || true

  docker run --rm -d --gpus all \
    -v "$HOME/.cache/huggingface:/root/.cache/huggingface:ro" \
    -p 172.17.0.1:8001:8000 \
    --name sidekick-vllm \
    vllm/vllm-openai:cu130-nightly \
      --model Qwen/Qwen3.5-2B \
      --served-model-name qwen3.5-2b \
      --host 0.0.0.0 --port 8000 \
      --max-model-len 32768 \
      --gpu-memory-utilization 0.10 \
      --dtype bfloat16

  wait_ready "$PORT2_URL" "sidekick (Qwen3.5-2B)"
  SK_MODEL=$(curl -sf "$PORT2_URL/models" | python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])")
  DS4_MODEL=$(curl -sf "$DS4_URL/models" | python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])")
  log "RAM: $(free -h | awk '/^Mem/{print $3"/"$2}')"

  # Sidekick solo conversation (quality test)
  run_bench "sidekick-solo" "$PORT2_URL" "$SK_MODEL" "$RESULTS/phase2_sidekick_conversation.json"

  # Concurrency: user_a → ds4, user_b → sidekick simultaneously (parallel)
  run_concurrency "ds4+sidekick-concurrent" \
    "$DS4_URL" "$DS4_MODEL" "$PORT2_URL" "$SK_MODEL" \
    "$RESULTS/phase2_concurrent.json"

  log "Phase 2 done. RAM: $(free -h | awk '/^Mem/{print $3"/"$2}')"
fi

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 3 — Qwen3-Next-80B alone (ds4 stopped)
# ══════════════════════════════════════════════════════════════════════════════
if [[ "$PHASE" == "3" || "$PHASE" == "all" ]]; then
  sep "PHASE 3: Qwen3-Next-80B FP8 alone"

  log "Stopping ds4 and sidekick..."
  sudo systemctl stop ds4-ssd 2>/dev/null || true
  docker stop sidekick-vllm   2>/dev/null || true
  docker stop seed-oss-awq-vllm 2>/dev/null || true
  sleep 3
  log "RAM after teardown: $(free -h | awk '/^Mem/{print $3"/"$2}')"

  docker stop qwen80b-vllm 2>/dev/null || true
  docker rm   qwen80b-vllm 2>/dev/null || true

  docker run --rm -d --gpus all \
    -v "$QWEN80B_WEIGHTS:/model:ro" \
    -p 172.17.0.1:8001:8000 \
    --name qwen80b-vllm \
    vllm/vllm-openai:cu130-nightly \
      --model /model \
      --served-model-name qwen3-80b \
      --host 0.0.0.0 --port 8000 \
      --max-model-len 32768 \
      --gpu-memory-utilization 0.85 \
      --dtype bfloat16 \
      --enable-auto-tool-choice \
      --tool-call-parser hermes

  wait_ready "$PORT2_URL" "Qwen3-Next-80B"
  Q80_MODEL=$(curl -sf "$PORT2_URL/models" | python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])")
  log "RAM: $(free -h | awk '/^Mem/{print $3"/"$2}')"

  run_bench "qwen80b-alone" "$PORT2_URL" "$Q80_MODEL" "$RESULTS/phase3_conversation.json"

  # Concurrency: 2 users both on 80B (vLLM batches)
  run_concurrency "qwen80b-concurrent" \
    "$PORT2_URL" "$Q80_MODEL" "$PORT2_URL" "$Q80_MODEL" \
    "$RESULTS/phase3_concurrent.json"

  log "Phase 3 done. RAM: $(free -h | awk '/^Mem/{print $3"/"$2}')"
fi

# ── Summary ──────────────────────────────────────────────────────────────────
sep "RESULTS SUMMARY"
python3 - "$RESULTS" << 'PYEOF'
import sys, json, os, glob

d = sys.argv[1]
for f in sorted(glob.glob(d+"/*.json")):
    data = json.load(open(f))
    name = os.path.basename(f).replace(".json","")
    if "concurrent" in name:
        wall = data.get("wall_s","?")
        parts = []
        for k,r in data.get("results",{}).items():
            tag = "user_a" if k=="user_a" else "user_b"
            s = f"{r['elapsed_s']}s" if r.get("ok") else "ERR"
            parts.append(f"{tag}={s}")
        print(f"  {name}: wall={wall}s  [{' | '.join(parts)}]")
    else:
        total = data.get("total_s","?")
        turns = data.get("turns",[])
        times = " / ".join(f"{t['elapsed_s']}s" for t in turns)
        print(f"  {name}: total={total}s  turns=[{times}]")
PYEOF

log "All done. Results: $RESULTS/"
