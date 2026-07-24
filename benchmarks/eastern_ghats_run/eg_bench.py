#!/usr/bin/env python3
"""Eastern Ghats bench — 3 threads, measure what a better PLANNER buys.

Threads (all OpenRouter → can run in parallel; no local GPU contention):
  deepseek : plain deepseek-v4-flash          (cheap planner+runner)
  glm      : plain glm-5.2                     (strong planner+runner)
  hybrid   : glm-5.2 PLANS -> deepseek EXECUTES (strong planner + cheap runner)

Per question we capture the answer + wall-time + session id, then MINE state.db for the trace metrics
(tool count, connectors, name resolved?, recipe read?, papers-first?) and score cheap signal flags.
Resumable (skips done cells), OpenRouter spend-capped. Run one thread per process:

  python3 eg_bench.py run --thread hybrid [--n 16] [--cap-usd 15]
  python3 eg_bench.py report
"""
import argparse, json, os, re, subprocess, sqlite3, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
CHAT = os.path.join(REPO, "agents", "hermes", "chat.sh")
SYLL = json.load(open(os.path.join(HERE, "syllabus.json")))
OUT = lambda th: os.path.join(HERE, f"results_{th}.jsonl")
CREDS = os.path.expanduser("~/.config/idlisseus/openrouter.json")
STATEDB = "/opt/data/state.db"

PLAN_PROMPT = (
    "You are a SENIOR conservation-data analyst. A field researcher at 'Elephants by the Lake' (Eastern "
    "Ghats, Krishnagiri, Tamil Nadu) asks the question below. Do NOT run tools and do NOT answer it — "
    "output only a SHORT numbered PLAN (5-8 steps) of exactly which connectors/recipes to use and in what "
    "order, following the rules: PAPERS FIRST (the user is a researcher — beat their lit review), RESOLVE "
    "the species name before anything, and for a 'where' question produce a MAP not a single point. "
    "Question: ")
EXEC_PROMPT = (
    "A senior analyst gave you this PLAN to answer a field researcher's question. Follow it — run the "
    "connectors, then give the final answer.\n\nPLAN:\n{plan}\n\nQUESTION: {q}")


def spend_usd():
    try:
        key = json.load(open(CREDS))["api_key"]
        req = urllib.request.Request("https://openrouter.ai/api/v1/credits",
                                     headers={"Authorization": f"Bearer {key}"})
        d = json.load(urllib.request.urlopen(req, timeout=15))["data"]
        return float(d.get("total_usage", 0.0))
    except Exception:
        return None


def _dec(x):
    return x.decode("utf-8", "replace") if isinstance(x, (bytes, bytearray)) else (x or "")


def run_chat(model, prompt, source=None, timeout=780):
    env = dict(os.environ, AUTO_APPROVE="1")
    if source:
        env["HERMES_SOURCE"] = source          # unique per-run tag → collision-free session lookup
    t0 = time.time()
    try:
        p = subprocess.run([CHAT, "--model", model, prompt], capture_output=True, text=True,
                           timeout=timeout, env=env)
        out = _dec(p.stdout) + _dec(p.stderr)
    except subprocess.TimeoutExpired as e:
        out = _dec(e.stdout) + _dec(e.stderr) + "\n[TIMEOUT]"
    return out, (t0, time.time() - t0)


_FIND_SCRIPT = r'''
import sqlite3, sys
c = sqlite3.connect("file:/opt/data/state.db?mode=ro", uri=True)
r = c.execute("SELECT id FROM sessions WHERE source=? ORDER BY started_at DESC LIMIT 1", (sys.argv[1],)).fetchone()
print(r[0] if r else "")
'''


def find_session(source):
    """Look up the session by its unique --source tag (bulletproof; no cross-thread collision)."""
    try:
        p = subprocess.run(["sudo", "docker", "exec", "-i", "hermes-live", "python3", "-c",
                            _FIND_SCRIPT, source], capture_output=True, text=True, timeout=30)
        return p.stdout.strip().splitlines()[-1].strip() or None
    except Exception:
        return None


_MINE_SCRIPT = r'''
import sqlite3, re, json, sys
sid = sys.argv[1]
c = sqlite3.connect("file:/opt/data/state.db?mode=ro", uri=True)
rows = list(c.execute("SELECT role,content,tool_calls FROM messages WHERE session_id=? ORDER BY rowid", (sid,)))
blob, ans, ntool = [], "", 0
for role, content, tc in rows:
    if role == "tool": ntool += 1
    if tc: blob.append(tc)
    if role == "assistant" and content and content.strip() and not tc: ans = content
txt = "\n".join(blob)
s = c.execute("SELECT tool_call_count,api_call_count,estimated_cost_usd FROM sessions WHERE id=?", (sid,)).fetchone() or (None, None, None)
KNOWN = {"landcover","fire","terrain","protected_areas","occurrence","inaturalist","points","greenness",
         "ecoregion","embedding","predict","hyperspectral","paper_data","ebird","phenology","indicators",
         "water","s2","geo","invasive","skyfi","groundtruth_lens"}
print(json.dumps({"n_tool": s[0] if s[0] is not None else ntool, "api_calls": s[1], "cost_usd": s[2],
    "connectors": sorted(set(m for m in re.findall(r"([a-z_]+)\.py", txt) if m in KNOWN)),
    "resolved": bool(re.search(r"points\.py resolve|resolve --species|resolved", txt)),
    "recipe": "recipes/" in txt, "papers": "paper_data" in txt, "answer": ans}))
'''


def mine(session_id):
    """Trace metrics from the container's state.db (single source of truth) via docker exec (uid-10000 file)."""
    d = {"n_tool": 0, "api_calls": None, "cost_usd": None, "connectors": [], "resolved": False,
         "recipe": False, "papers": False, "answer": ""}
    if not session_id:
        return d
    try:
        p = subprocess.run(["sudo", "docker", "exec", "-i", "hermes-live", "python3", "-c",
                            _MINE_SCRIPT, session_id], capture_output=True, text=True, timeout=30)
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        return d


def score(q, m):
    a = (m["answer"] or "").lower()
    where = bool(re.search(r"\bwhere\b|distribution|find|microhabitat|prioritize|localit", q.lower()))
    return {
        "papers_first": m["papers"],
        "name_resolved": m["resolved"],
        "map_for_where": (not where) or bool({"invasive", "predict", "groundtruth_lens", "s2"} & set(m["connectors"])),
        "honest_limit": bool(re.search(r"not observed|modelled|no record|absent|gap|survey|caveat|limit|"
                                       r"unverified|would fill|data ask|need", a)),
        "grounded": bool(re.search(r"\d", a)) and len(a) > 300,
        "not_empty": len(a) > 200,
    }


def run(thread, idxs, cap):
    done = set()
    if os.path.exists(OUT(thread)):
        done = {json.loads(l)["q_idx"] for l in open(OUT(thread))}
    rawdir = os.path.join(HERE, "raw"); os.makedirs(rawdir, exist_ok=True)
    for i in idxs:
        if i in done:
            continue
        q = SYLL[i]
        s = spend_usd()
        if s is not None and s - RUN_BASE_SPEND[0] > cap:
            print(f"[{thread}] run-spend ${s-RUN_BASE_SPEND[0]:.2f} > cap ${cap} — stopping"); break
        print(f"[{thread}] Q{i}: {q[:60]}...", flush=True)
        src = f"egb_{thread}_q{i}_{int(time.time())}"      # unique per-run session tag
        if thread == "hybrid":
            plan, (p0, dt_p) = run_chat("glm5.2", PLAN_PROMPT + q, source=src + "_plan", timeout=360)
            plan_txt = re.sub(r".*?(?=\d[.)]|Step)", "", plan, count=1, flags=re.DOTALL)[:2500]
            out, (t0, dt_e) = run_chat("deepseekv4", EXEC_PROMPT.format(plan=plan_txt, q=q), source=src)
            dt = dt_p + dt_e
        else:
            model = {"deepseek": "deepseekv4", "glm": "glm5.2"}[thread]
            out, (t0, dt) = run_chat(model, q, source=src)
        open(os.path.join(rawdir, f"{thread}_q{i}.txt"), "w").write(out[-20000:])
        sid = find_session(src)                            # bulletproof: lookup by the unique source tag
        m = mine(sid)
        rec = {"thread": thread, "q_idx": i, "q": q, "session": sid, "source": src, "sec": round(dt, 1),
               "n_tool": m["n_tool"], "api_calls": m["api_calls"], "cost_usd": m["cost_usd"],
               "connectors": m["connectors"], **score(q, m), "answer": m["answer"][:4000]}
        with open(OUT(thread), "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"[{thread}] Q{i} done {dt:.0f}s sid={sid} tools={m['n_tool']} ${m['cost_usd']} "
              f"conn={m['connectors']} resolved={m['resolved']} papers={m['papers']}", flush=True)


def report():
    threads = ["deepseek", "glm", "hybrid"]
    sig = ["papers_first", "name_resolved", "map_for_where", "honest_limit", "grounded", "not_empty"]
    print(f"\n{'thread':10} {'n':>3} {'sec':>6} {'tools':>6} {'cost$':>7}  " + "  ".join(f"{s[:9]:>9}" for s in sig))
    for th in threads:
        if not os.path.exists(OUT(th)):
            continue
        rs = [json.loads(l) for l in open(OUT(th))]
        if not rs:
            continue
        avg = lambda k: sum((r.get(k) or 0) for r in rs) / len(rs)
        rate = lambda k: sum(1 for r in rs if r.get(k)) / len(rs)
        print(f"{th:10} {len(rs):>3} {avg('sec'):>6.0f} {avg('n_tool'):>6.1f} {avg('cost_usd'):>7.3f}  "
              + "  ".join(f"{rate(s):>9.2f}" for s in sig))
    print("\n(rates = fraction of questions passing each signal; sec/tools = mean cost)")


RUN_BASE_SPEND = [0.0]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    r = sub.add_parser("run"); r.add_argument("--thread", required=True, choices=["deepseek", "glm", "hybrid"])
    r.add_argument("--idx", default="", help="comma list of question indices; default = all")
    r.add_argument("--cap-usd", type=float, default=15.0)
    sub.add_parser("report")
    sub.add_parser("remine")     # re-run mine() on every stored record (after a mining-logic fix)
    a = ap.parse_args()
    if a.cmd == "run":
        idxs = [int(x) for x in a.idx.split(",")] if a.idx else list(range(len(SYLL)))
        base = spend_usd(); RUN_BASE_SPEND[0] = base if base is not None else 0.0
        run(a.thread, idxs, a.cap_usd)
    elif a.cmd == "remine":
        for th in ["deepseek", "glm", "hybrid"]:
            if not os.path.exists(OUT(th)):
                continue
            recs = [json.loads(l) for l in open(OUT(th))]
            for r in recs:
                m = mine(r.get("session"))
                r.update(n_tool=m["n_tool"], api_calls=m["api_calls"], cost_usd=m["cost_usd"],
                         connectors=m["connectors"], **score(r["q"], m), answer=m["answer"][:4000])
            with open(OUT(th), "w") as f:
                for r in recs:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"remined {th}: {len(recs)}")
    else:
        report()
