#!/bin/bash
# Benchmark 7: Qwen3.5-122B-A10B-AR-INT4 — quality, speed, concurrency, thinking impact
#
# Phases:
#   1. Conversational  — same 3-turn ecology prompt as B6 (direct comparison)
#   2. Document tasks  — same tasks 1-4 as B3 (summary / cross-paper / causal / dashboard)
#   3. Thinking toggle — task 4 (dashboard) with thinking ON vs OFF: quality + latency
#   4. Concurrency     — 2 / 5 / 10 simultaneous Turn-1 requests; wall time + per-user latency
#   5. Agentic loop    — model uses web_search / fetch_url tools to find papers, then writes dashboard
#
# Compare conversational numbers against B6 (80B: 8s avg / ds4: 121s avg).
# Compare document task numbers against B3 (ds4 results in ds4_results/).
#
# Usage: bash run_bench7.sh [phase]   — phase: 1 2 3 4 5 or 'all' (default)
#        THINKING=off bash run_bench7.sh 2    — force thinking off for all phases

set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
B3_PAPERS="$REPO/benchmarks/benchmark3_seed_oss/papers"
RESULTS="$(dirname "$0")/results_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS"

URL="http://172.17.0.1:8001/v1"
MODEL="qwen"
MAX_TOKENS=2048
THINKING="${THINKING:-on}"   # set THINKING=off to suppress <think> blocks

die()  { echo "ERROR: $*" >&2; exit 1; }
log()  { echo "[$(date '+%H:%M:%S')] $*"; }
sep()  { echo ""; echo "── $* ────────────────────────────────────────────────────"; }
mem()  { echo "  RAM: $(free -h | awk '/^Mem/{print $3"/"$2}')  KV-cache: $(curl -sf http://172.17.0.1:8001/metrics | grep 'kv_cache_usage_perc' | awk '{print $NF*100 "%"}')"; }

# Model must already be running
curl -sf "$URL/models" >/dev/null 2>&1 || die "vllm-qwen35 not reachable at $URL"
log "Model: $MODEL  Thinking: $THINKING"
mem

# ── Low-level chat call (non-streaming) ──────────────────────────────────────
chat() {
  local url=$1 model=$2 sys=$3 msgs_json=$4 max=$5 enable_thinking=$6 out=$7
  python3 - "$url" "$model" "$sys" "$msgs_json" "$max" "$enable_thinking" "$out" << 'PYEOF'
import sys, json, time, urllib.request
url, model, system, msgs_json, max_tok, enable_thinking, out = sys.argv[1:8]
msgs = [{"role": "system", "content": system}] + json.loads(msgs_json)
payload = {
    "model": model,
    "messages": msgs,
    "max_tokens": int(max_tok),
    "temperature": 0.7,
    "stream": False,
}
if enable_thinking == "off":
    payload["chat_template_kwargs"] = {"enable_thinking": False}
data = json.dumps(payload).encode()
req = urllib.request.Request(url + "/chat/completions", data=data,
                             headers={"Content-Type": "application/json"})
t0 = time.time()
with urllib.request.urlopen(req, timeout=600) as r:
    d = json.load(r)
elapsed = time.time() - t0
msg = d["choices"][0]["message"]
content = msg.get("content") or ""
reasoning = msg.get("reasoning") or msg.get("reasoning_content") or ""
usage = d.get("usage", {})
result = {
    "elapsed_s": round(elapsed, 1),
    "content": content,
    "reasoning_tokens": len(reasoning.split()),
    "prompt_tokens": usage.get("prompt_tokens", "?"),
    "completion_tokens": usage.get("completion_tokens", "?"),
}
with open(out, "w") as f:
    json.dump(result, f, indent=2)
print(f"  {round(elapsed,1)}s | p={usage.get('prompt_tokens','?')} c={usage.get('completion_tokens','?')} reason={len(reasoning.split())}w")
PYEOF
}

# ── 3-turn conversation helper ────────────────────────────────────────────────
SYSTEM_CHAT="You are an ecologist specialising in habitat restoration and invasive species management. Be concise but substantive — 3-5 sentences per answer."
TURN1="What makes invasive plants so difficult to eradicate once they establish in a new habitat?"
TURN2="Which restoration approaches have shown lasting success after invasive plant removal, and what made them work?"
TURN3="A land trust has one season and a small volunteer crew to begin restoring a meadow overrun by Japanese knotweed. What would you prioritise and why?"

run_conversation() {
  local label=$1 out=$2 thinking=$3
  log "3-turn conversation ($label, thinking=$thinking)"
  python3 - "$URL" "$MODEL" "$SYSTEM_CHAT" "$out" "$MAX_TOKENS" "$thinking" \
    "$TURN1" "$TURN2" "$TURN3" << 'PYEOF'
import sys, json, time, urllib.request, textwrap
url, model, system, out, max_tok, thinking = sys.argv[1:7]
turns = list(sys.argv[7:])
history = []
records = []
for i, q in enumerate(turns, 1):
    msgs = [{"role":"system","content":system}] + history + [{"role":"user","content":q}]
    payload = {"model":model,"messages":msgs,"max_tokens":int(max_tok),"temperature":0.7}
    if thinking == "off":
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url+"/chat/completions", data=data,
                                 headers={"Content-Type":"application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=600) as r:
        d = json.load(r)
    elapsed = time.time() - t0
    msg = d["choices"][0]["message"]
    content = msg.get("content") or ""
    reasoning = msg.get("reasoning") or msg.get("reasoning_content") or ""
    usage = d.get("usage", {})
    history += [{"role":"user","content":q},{"role":"assistant","content":content}]
    print(f"  Turn {i}: {elapsed:.0f}s | p={usage.get('prompt_tokens','?')} c={usage.get('completion_tokens','?')} reason_words={len(reasoning.split())}")
    print(textwrap.fill(content[:200]+"...", 76, initial_indent="    → ", subsequent_indent="      "))
    records.append({"turn":i,"question":q,"answer":content,"reasoning":reasoning,
                    "elapsed_s":round(elapsed,1),"prompt_tokens":usage.get("prompt_tokens"),
                    "completion_tokens":usage.get("completion_tokens")})
total = sum(r["elapsed_s"] for r in records)
print(f"  Total: {total:.0f}s ({total/len(records):.0f}s avg)")
with open(out, "w") as f:
    json.dump({"label":"conversation","thinking":thinking,"turns":records,"total_s":total}, f, indent=2)
PYEOF
}

# ── Concurrency helper ─────────────────────────────────────────────────────
run_concurrency() {
  local n=$1 out=$2 thinking=$3
  log "Concurrency: $n simultaneous users (thinking=$thinking)"
  python3 - "$URL" "$MODEL" "$SYSTEM_CHAT" "$TURN1" "$MAX_TOKENS" "$n" "$thinking" "$out" << 'PYEOF'
import sys, json, time, urllib.request
from threading import Thread
url, model, system, question, max_tok, n_str, thinking, out = sys.argv[1:9]
n = int(n_str)
results = {}
def fire(i):
    msgs = [{"role":"system","content":system},{"role":"user","content":question}]
    payload = {"model":model,"messages":msgs,"max_tokens":int(max_tok),"temperature":0.7}
    if thinking == "off":
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url+"/chat/completions", data=data,
                                 headers={"Content-Type":"application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            d = json.load(r)
        elapsed = time.time() - t0
        ctok = d.get("usage",{}).get("completion_tokens","?")
        results[i] = {"elapsed_s":round(elapsed,1),"completion_tokens":ctok,"ok":True}
    except Exception as e:
        results[i] = {"elapsed_s":round(time.time()-t0,1),"error":str(e),"ok":False}

t_start = time.time()
threads = [Thread(target=fire, args=(i,)) for i in range(n)]
for t in threads: t.start()
for t in threads: t.join()
wall = time.time() - t_start
times = [results[i]["elapsed_s"] for i in range(n) if results[i].get("ok")]
avg = sum(times)/len(times) if times else 0
slowest = max(times) if times else 0
print(f"  {n} users: wall={wall:.0f}s  avg={avg:.0f}s  slowest={slowest:.0f}s  ok={sum(1 for r in results.values() if r.get('ok'))}/{n}")
with open(out, "w") as f:
    json.dump({"n_users":n,"wall_s":round(wall,1),"results":results,
               "avg_s":round(avg,1),"slowest_s":round(slowest,1)}, f, indent=2)
PYEOF
}

# ── B3 document tasks ─────────────────────────────────────────────────────
read_paper() { cat "$B3_PAPERS/$1.txt"; }

run_doc_task() {
  local task=$1 out=$2 thinking=$3
  log "Document task $task (thinking=$thinking)"
  python3 - "$URL" "$MODEL" "$task" "$B3_PAPERS" "$out" "$MAX_TOKENS" "$thinking" << 'PYEOF'
import sys, json, time, urllib.request, os
url, model, task, papers_dir, out, max_tok, thinking = sys.argv[1:8]

def read(name):
    with open(f"{papers_dir}/{name}.txt") as f: return f.read()

prompts = {
    "1": ("Summarize the following paper in about 3 paragraphs.\n\n"
          f"=== 03_Forest_Fire_Himalayan_Regions ===\n{read('03_Forest_Fire_Himalayan_Regions')}"),
    "2": ("Below are 5 papers on forest fire management. Identify: (a) what they agree on, "
          "(b) real disagreements (be specific about which paper says what), "
          "(c) each paper's main contribution. Cite by document name.\n\n" +
          "\n\n".join(f"=== {d} ===\n{read(d)}" for d in [
              "01_Models_Forest_Fire_Management_India","03_Forest_Fire_Himalayan_Regions",
              "09_Wildfire_Burn_Severity_Uttarakhand","11_Cloud_Based_Fire_Alert_IoT",
              "16_Madhuca_Longifolia_Fire_Cause"])),
    "3": ("Based ONLY on these two papers: what do they say about causes of forest fires, "
          "and do they agree or disagree on the relative importance of any specific cause? "
          "If something is not stated in either paper, say so explicitly.\n\n" +
          "\n\n".join(f"=== {d} ===\n{read(d)}" for d in [
              "01_Models_Forest_Fire_Management_India","16_Madhuca_Longifolia_Fire_Cause"])),
    "4": ("Below are 5 papers on forest fire management. Produce a single, complete, "
          "self-contained dashboard.html (inline CSS/JS, no external dependencies) that "
          "visually summarizes: key themes, any disagreements, and a chart of paper topics. "
          "Output ONLY the HTML file content, nothing else.\n\n" +
          "\n\n".join(f"=== {d} ===\n{read(d)}" for d in [
              "01_Models_Forest_Fire_Management_India","03_Forest_Fire_Himalayan_Regions",
              "09_Wildfire_Burn_Severity_Uttarakhand","11_Cloud_Based_Fire_Alert_IoT",
              "16_Madhuca_Longifolia_Fire_Cause"])),
}
prompt = prompts[task]
msgs = [{"role": "user", "content": prompt}]
payload = {"model": model, "messages": msgs, "max_tokens": int(max_tok), "temperature": 0.3}
if thinking == "off":
    payload["chat_template_kwargs"] = {"enable_thinking": False}
data = json.dumps(payload).encode()
req = urllib.request.Request(url+"/chat/completions", data=data,
                             headers={"Content-Type":"application/json"})
t0 = time.time()
with urllib.request.urlopen(req, timeout=600) as r:
    d = json.load(r)
elapsed = time.time() - t0
msg = d["choices"][0]["message"]
content = msg.get("content") or ""
reasoning = msg.get("reasoning") or msg.get("reasoning_content") or ""
usage = d.get("usage", {})
print(f"  Task {task}: {elapsed:.0f}s | p={usage.get('prompt_tokens','?')} c={usage.get('completion_tokens','?')} reason_words={len(reasoning.split())}")
if task == "4" and content.strip().startswith("<!"):
    out_html = out.replace(".json", ".html")
    with open(out_html, "w") as f: f.write(content)
    print(f"  → HTML saved: {out_html}")
with open(out, "w") as f:
    json.dump({"task":task,"thinking":thinking,"elapsed_s":round(elapsed,1),
               "content":content,"reasoning_words":len(reasoning.split()),
               "prompt_tokens":usage.get("prompt_tokens"),
               "completion_tokens":usage.get("completion_tokens")}, f, indent=2)
PYEOF
}

# ── Phase 5: Agentic loop ─────────────────────────────────────────────────
run_agentic() {
  local out=$1
  log "Agentic loop: model searches for papers on forest fire management"
  python3 - "$URL" "$MODEL" "$out" << 'PYEOF'
import sys, json, time, urllib.request, re, os
url, model, out = sys.argv[1:4]

SYSTEM = """You are a research assistant. Use the tools available to find papers and build a report.
Available tools:
- web_search(query): search the web for information
- fetch_url(url): fetch and read the content of a URL

When you want to use a tool, output EXACTLY this format (on its own line, nothing else before or after):
TOOL_CALL: tool_name
ARGS: {"key": "value"}

Wait — the harness will send you the result as a new message. Then continue.
Do NOT use markdown code blocks around TOOL_CALL lines."""

# No OpenAI tools API — using text-format tool loop (vLLM not launched with --enable-auto-tool-choice)
tools = []

PAPERS_DIR = os.path.expanduser(
    "~/src/github.com/bprashanth/idlisseus/benchmarks/benchmark3_seed_oss/papers"
)

# Fixture search results — realistic snippets from actual papers already on disk.
# Tests full agentic loop (plan queries, select, fetch, synthesize) without live web access.
SEARCH_FIXTURES = {
    "DEFAULT": """[1] link.springer.com/article/models-forest-fire-management-india
    Models for Forest Fire Management in India — reviews risk models, satellite fire detection, and
    fuel load estimation across diverse Indian forest types. Published in Forest Policy and Economics.
[2] mdpi.com/2571-6255/himalayan-fire-regions
    Forest Fire in Himalayan Regions — analyses seasonal fire patterns, anthropogenic ignition sources,
    and elevation-dependent spread in Uttarakhand and Himachal Pradesh.
[3] sciencedirect.com/wildfire-burn-severity-uttarakhand
    Wildfire Burn Severity Assessment in Uttarakhand — uses remote sensing and field data to classify
    burn severity and post-fire vegetation recovery across pine-dominated forests.
[4] ieeexplore.ieee.org/cloud-iot-fire-alert
    Cloud-Based Fire Alert System using IoT Sensors — proposes low-cost sensor networks combined with
    cloud analytics for early detection of forest fires in remote areas.
[5] journals.plos.org/madhuca-longifolia-fire
    Madhuca longifolia and Human-Caused Forest Fires — documents how collection of mahua flowers
    drives deliberate understory burning in central India."""
}

def web_search(query):
    """Return fixture search results (live web blocked; tests model's tool-use planning)."""
    return SEARCH_FIXTURES["DEFAULT"]

def fetch_url(url):
    """Map known URLs to local paper text; fall back to a short description."""
    url_to_paper = {
        "models-forest-fire-management-india": "01_Models_Forest_Fire_Management_India",
        "himalayan-fire-regions":              "03_Forest_Fire_Himalayan_Regions",
        "wildfire-burn-severity-uttarakhand":  "09_Wildfire_Burn_Severity_Uttarakhand",
        "cloud-iot-fire-alert":                "11_Cloud_Based_Fire_Alert_IoT",
        "madhuca-longifolia-fire":             "16_Madhuca_Longifolia_Fire_Cause",
    }
    for key, filename in url_to_paper.items():
        if key in url:
            path = os.path.join(PAPERS_DIR, filename + ".txt")
            try:
                with open(path) as f:
                    return f.read()[:4000]
            except Exception as e:
                return f"File error: {e}"
    return f"URL not in fixture set: {url} — try one of the URLs from web_search results."

TASK = """Find 3-5 recent papers or reports on forest fire management in India or the Himalayas.
For each one: title, authors (if available), year, and a 2-sentence summary.
Then write a brief synthesis: what do they collectively say about the main causes and solutions?
Finally, produce a short HTML summary table (inline CSS) with: Paper | Year | Key Finding.
Output the HTML table at the very end."""

messages = [{"role": "user", "content": TASK}]
tool_calls_log = []
total_wall = 0
MAX_TURNS = 8

print(f"  Task: {TASK[:80]}...")
t_start = time.time()

for turn in range(MAX_TURNS):
    payload = {
        "model": model,
        "messages": [{"role":"system","content":SYSTEM}] + messages,
        "max_tokens": 1024,
        "temperature": 0.3,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url+"/chat/completions", data=data,
                                 headers={"Content-Type":"application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.load(r)
    elapsed = time.time() - t0
    total_wall += elapsed

    choice = d["choices"][0]
    msg = choice["message"]
    finish = choice.get("finish_reason", "")
    content = msg.get("content") or ""

    # Parse text-format tool calls: TOOL_CALL: name\nARGS: {...}
    tc_matches = re.findall(r'TOOL_CALL:\s*(\w+)\nARGS:\s*(\{[^\n]+\})', content)

    print(f"  Turn {turn+1}: {elapsed:.0f}s | finish={finish} | text_tool_calls={len(tc_matches)} | content={len(content)}c")
    messages.append({"role": "assistant", "content": content})

    if not tc_matches:
        print(f"  Model finished (no more tool calls).")
        break

    for name, args_str in tc_matches:
        try:
            args = json.loads(args_str)
        except Exception:
            args = {}
        print(f"    → tool: {name}({json.dumps(args)[:60]})")
        if name == "web_search":
            result = web_search(args.get("query", ""))
        elif name == "fetch_url":
            result = fetch_url(args.get("url", ""))
        else:
            result = f"Unknown tool: {name}"
        tool_calls_log.append({"turn": turn+1, "tool": name, "args": args, "result_len": len(result)})
        messages.append({"role": "user", "content": f"TOOL_RESULT for {name}:\n{result}"})
        print(f"       result: {len(result)} chars")

wall = time.time() - t_start
final_content = next((m["content"] for m in reversed(messages) if m.get("role")=="assistant" and m.get("content")), "")
print(f"\n  Total wall: {wall:.0f}s | turns: {turn+1} | tool_calls: {len(tool_calls_log)}")
print(f"  Final answer: {len(final_content)} chars")
if "<table" in final_content.lower():
    html_match = re.search(r'(<table.*?</table>)', final_content, re.DOTALL | re.IGNORECASE)
    if html_match:
        out_html = out.replace(".json", "_table.html")
        with open(out_html, "w") as f: f.write(f"<html><body>{html_match.group(1)}</body></html>")
        print(f"  → Table HTML: {out_html}")
with open(out, "w") as f:
    json.dump({"task":"agentic","wall_s":round(wall,1),"turns":turn+1,
               "tool_calls":tool_calls_log,"final_answer":final_content}, f, indent=2)
PYEOF
}

PHASE=${1:-all}

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 1 — Conversational (same prompts as B6 for direct comparison)
# ══════════════════════════════════════════════════════════════════════════════
if [[ "$PHASE" == "1" || "$PHASE" == "all" ]]; then
  sep "PHASE 1: Conversational quality (B6 comparison)"
  run_conversation "qwen35-thinking-${THINKING}" "$RESULTS/p1_conversation.json" "$THINKING"
  mem
fi

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — Document tasks (B3 comparison)
# ══════════════════════════════════════════════════════════════════════════════
if [[ "$PHASE" == "2" || "$PHASE" == "all" ]]; then
  sep "PHASE 2: Document tasks (B3 comparison)"
  for task in 1 2 3 4; do
    run_doc_task "$task" "$RESULTS/p2_task${task}.json" "$THINKING"
  done
  mem
fi

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 3 — Thinking ON vs OFF (task 4 = dashboard generation)
# ══════════════════════════════════════════════════════════════════════════════
if [[ "$PHASE" == "3" || "$PHASE" == "all" ]]; then
  sep "PHASE 3: Thinking ON vs OFF (dashboard task)"
  log "Running task 4 WITH thinking..."
  run_doc_task "4" "$RESULTS/p3_dashboard_thinking_on.json" "on"
  log "Running task 4 WITHOUT thinking..."
  run_doc_task "4" "$RESULTS/p3_dashboard_thinking_off.json" "off"
  mem
fi

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 4 — Concurrency (2, 5, 10 users)
# ══════════════════════════════════════════════════════════════════════════════
if [[ "$PHASE" == "4" || "$PHASE" == "all" ]]; then
  sep "PHASE 4: Concurrency (2 / 5 / 10 users, thinking=$THINKING)"
  for n in 2 5 10; do
    run_concurrency "$n" "$RESULTS/p4_concurrent_${n}users.json" "$THINKING"
    mem
    sleep 5
  done
fi

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 5 — Agentic loop (model finds papers via web_search)
# ══════════════════════════════════════════════════════════════════════════════
if [[ "$PHASE" == "5" || "$PHASE" == "all" ]]; then
  sep "PHASE 5: Agentic tool-use loop (finding papers)"
  run_agentic "$RESULTS/p5_agentic.json"
  mem
fi

# ── Summary ──────────────────────────────────────────────────────────────────
sep "RESULTS SUMMARY"
echo ""
echo "  B6 reference: ds4=121s avg / 80B=8s avg (3-turn, same prompts, no thinking)"
echo ""
python3 - "$RESULTS" << 'PYEOF'
import sys, json, os, glob
d = sys.argv[1]
for f in sorted(glob.glob(d+"/*.json")):
    try:
        data = json.load(open(f))
        name = os.path.basename(f).replace(".json","")
        if "conversation" in name:
            t = data.get("total_s","?")
            turns = data.get("turns",[])
            ts = " / ".join(f"{r['elapsed_s']}s" for r in turns)
            rw = sum(r.get("reasoning",{}) and 0 or 0 for r in turns)
            print(f"  {name}: total={t}s  turns=[{ts}]")
        elif "concurrent" in name:
            print(f"  {name}: wall={data.get('wall_s','?')}s  avg={data.get('avg_s','?')}s  slowest={data.get('slowest_s','?')}s  n={data.get('n_users','?')}")
        elif "task" in name or "dashboard" in name:
            print(f"  {name}: {data.get('elapsed_s','?')}s  thinking={data.get('thinking','?')}  reason_words={data.get('reasoning_words','?')}")
        elif "agentic" in name:
            print(f"  {name}: wall={data.get('wall_s','?')}s  turns={data.get('turns','?')}  tool_calls={len(data.get('tool_calls',[]))}")
    except Exception as e:
        print(f"  {os.path.basename(f)}: ERROR reading — {e}")
PYEOF

log "All done. Results: $RESULTS/"
log "To view a dashboard HTML: open results_*/p2_task4.json (or .html if model output it)"
