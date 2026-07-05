#!/usr/bin/env python3
"""Head-to-head benchmark: our grounded stack (Hermes + connectors + data) vs a plain
agentic CLI (what an EBTL/ERA/Valparai worker does today — ask a general AI CLI).

Roles (all CLI-configurable; default cursor-agent):
  generator  -> writes realistic practitioner questions.
  System A   -> ../chat.sh  (Hermes + 11 connectors + real Earth-Engine/GBIF data + SOUL).
  System B   -> BASELINE_CLI run in a FRESH tmpdir, no connectors/repo (a plain user).
  judge      -> impartial rubric (helper only; raw answers are saved for human review).

Usage:
  python3 bench/bench.py generate --n 10 [--gen-cli cursor-agent]
  python3 bench/bench.py run [--start 0 --count 1] [--baseline-cli cursor-agent] [--judge]
  # results append to bench/results.jsonl and bench/report.md (resumable, per-question).
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ALGEBRA = os.path.dirname(HERE)
CHAT = os.path.join(ALGEBRA, "chat.sh")
QFILE = os.path.join(HERE, "questions.json")
RESULTS = os.path.join(HERE, "results.jsonl")
REPORT = os.path.join(HERE, "report.md")


def _isolated_home():
    """A fresh HOME with ONLY cursor auth — no ~/.cursor/projects or /chats memory.
    CRUCIAL for a fair baseline: cursor-agent keeps GLOBAL project memory keyed by repo
    path (seeded by every prior in-repo cursor run), and --workspace/cwd do NOT block it.
    A clean HOME is the only thing that gives a truly context-free 'clean machine'."""
    th = tempfile.mkdtemp(prefix="bench_home_")
    os.makedirs(os.path.join(th, ".config", "cursor"), exist_ok=True)
    os.makedirs(os.path.join(th, ".cursor"), exist_ok=True)
    for src, dst in [(os.path.expanduser("~/.config/cursor/auth.json"), ".config/cursor/auth.json"),
                     (os.path.expanduser("~/.cursor/cli-config.json"), ".cursor/cli-config.json"),
                     (os.path.expanduser("~/.cursor/agent-cli-state.json"), ".cursor/agent-cli-state.json")]:
        if os.path.exists(src):
            shutil.copy(src, os.path.join(th, dst))
    return th


def cli_run(cli, prompt, timeout=300, cwd=None, workspace=None, isolate_home=False):
    """Adapter for a configurable agentic CLI. `workspace` scopes an empty dir; `isolate_home`
    additionally gives cursor a fresh memory-less HOME (needed for a fair baseline/judge)."""
    # clean, context-free baseline: the local 122B with ONLY the question — no tools, no repo,
    # no memory. Can't leak our context; isolates what our STACK adds over a plain chatbot.
    if cli in ("raw", "llm", "122b", "raw122b"):
        body = json.dumps({"model": "qwen", "messages": [
            {"role": "system", "content": "You are a helpful assistant advising a field "
             "conservation worker. Answer their question as best you can."},
            {"role": "user", "content": prompt}], "max_tokens": 1200, "temperature": 0.3,
            "chat_template_kwargs": {"enable_thinking": False}}).encode()
        try:
            req = urllib.request.Request("http://172.17.0.1:8001/v1/chat/completions", body,
                                         {"Content-Type": "application/json"})
            txt = json.loads(urllib.request.urlopen(req, timeout=timeout).read())["choices"][0]["message"]["content"]
            return re.sub(r"<think>.*?</think>", "", txt, flags=re.DOTALL).strip()
        except Exception as e:
            return f"[raw-llm error: {e}]"
    env, th = dict(os.environ), None
    if cli in ("cursor-agent", "cursor", "agent"):
        cmd = ["cursor-agent", "-p", "--output-format", "text", "--trust"]
        if workspace:
            cmd += ["--workspace", workspace]
        cmd += [prompt]
        if isolate_home:
            th = _isolated_home(); env["HOME"] = th
    elif cli == "claude":
        cmd = ["claude", "-p", prompt]                       # placeholder for later
    else:
        cmd = [cli, "-p", prompt]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd, env=env)
        return p.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return f"[cli error: {e}]"
    finally:
        if th:
            shutil.rmtree(th, ignore_errors=True)


GEN_PROMPT = (
    "You are Varun, a field worker at a small conservation NGO doing forest restoration in "
    "rural South India — dry scrub-forest near Krishnagiri, plus some Western-Ghats coffee-forest "
    "sites. You are a practical field person, NOT a scientist or GIS/remote-sensing expert. "
    "Write {n} SHORT, plain, informal questions you'd actually type into an AI assistant about "
    "your land and daily work. Use everyday words (our forest, the trees we planted, lantana, "
    "invasives, elephants, the ponds, fire, the birds, the villagers). Do NOT use scientific "
    "names or technical/remote-sensing terms — no 'NDVI', 'MODIS', 'canopy cover %', 'Lantana "
    "camara', 'biomass'. Keep each question under ~15 words, the way a busy field person types. "
    "Mix topics broadly and realistically: is the forest coming back, invasives spreading, water/ponds, "
    "animals/birds/insects, fire, the NURSERY (which native seeds/saplings to grow, when they fruit, "
    "supplying plants to the land), crops/farming nearby and what villagers grow, people/livelihoods, "
    "which creatures signal a healthy forest. Ask what you'd genuinely want to know — do NOT assume any "
    "particular data or tool exists. Output ONLY a JSON array of question strings."
)


def generate(gen_cli, n):
    out = cli_run(gen_cli, GEN_PROMPT.format(n=n), timeout=200)
    m = re.search(r"\[.*\]", out, re.DOTALL)
    qs = json.loads(m.group(0)) if m else []
    qs = [q for q in qs if isinstance(q, str) and len(q) > 10][:n]
    json.dump(qs, open(QFILE, "w"), indent=2)
    print(f"generated {len(qs)} questions -> {QFILE}")
    for i, q in enumerate(qs):
        print(f"  [{i}] {q}")
    return qs


def run_A(q, timeout=1500):
    """Our stack: Hermes + connectors + data (chat.sh). Crash-proof: a timeout is recorded
    as a result (with partial output), not raised. Cleans up any lingering container."""
    t = time.time(); timed_out = False
    try:
        p = subprocess.run(["bash", CHAT, q], capture_output=True, text=True, timeout=timeout)
        log = p.stdout or ""
    except subprocess.TimeoutExpired as e:
        timed_out = True
        log = (e.stdout if isinstance(e.stdout, str) else (e.stdout or b"").decode("utf-8", "ignore")) or ""
        log += f"\n[A TIMED OUT after {timeout}s — did not finish this question]"
    finally:
        # A-runs are serial here, so any hermes container still up is an orphan from this run
        subprocess.run("docker ps -q --filter ancestor=hermes-agent-local | xargs -r docker rm -f",
                       shell=True, capture_output=True)
    names = set(re.findall(r"connectors/([a-z_]+)\.py", log))
    names |= set(re.findall(r"\b(greenness|landcover|fire|occurrence|terrain|ecoregion|"
                            r"embedding|predict|hyperspectral|protected_areas|geo)\b", log))
    conns = sorted(n for n in names if n)
    ans = _clean(log)
    gap = bool(re.search(r"no data|not available|would need|collect it|couldn'?t find|field data",
                         ans, re.I))
    return {"answer": ans[-4000:], "connectors_used": conns, "secs": round(time.time() - t),
            "flagged_gap": gap, "timed_out": timed_out}


def run_B(q, baseline_cli):
    """Plain baseline: the CLI in a fresh EMPTY workspace (no connectors/repo/context) —
    simulates a worker's own clean machine. Flags any leak of our context."""
    t = time.time()
    with tempfile.TemporaryDirectory(prefix="bench_baseline_") as td:
        out = cli_run(baseline_cli, q, timeout=600, cwd=td, workspace=td, isolate_home=True)
    ans = _clean(out)
    # flag GENUINE tells the baseline could get ONLY from our repo/runs. (cursor-agent leaks these
    # via cloud memory even in isolation — hence the raw-122B baseline; kept as a guard.)
    leak = bool(re.search(r"/opt/data|connectors?/[a-z_]+\.py|smileRandomForest|SITE_EBTL|"
                          r"dry.?deccan|donor.?belt|predict\.route|modelled_present_fraction|"
                          r"aoi_in_climate|_sample_cached|the benchmark run|connector stack|"
                          r"78\.1[0-9][0-9]|12\.7[0-9][0-9]|`(occurrence|predict|hyperspectral|greenness|landcover)`",
                          ans, re.I))
    return {"answer": ans[-4000:], "secs": round(time.time() - t), "leaked_our_context": leak}


def _clean(text):
    lines = [l for l in text.splitlines()
             if not re.search(r"s6-|cont-init|stage2|Syncing|reconcile|supervise|preinit|"
                              r"applyuidgid|preparing terminal|preparing execute|package:", l)]
    return "\n".join(lines).strip()


JUDGE_PROMPT = (
    "Two AI systems answered a conservation practitioner's (Varun's) question about his specific "
    "restoration site. Judge impartially. System A can compute real numbers from live data for the "
    "site; System B is a general assistant with no site data.\n"
    "SCORING RULES (important):\n"
    "- A plain REFUSAL ('I can't', 'no data', 'consult an expert') is NOT a win for anyone. The bar "
    "is: did the system TRY to give a site-grounded best answer with honest caveats?\n"
    "- Reward the system that gives the most SITE-SPECIFIC, DATA-GROUNDED, HONEST, ACTIONABLE "
    "answer. Fabricating specific numbers with no data is the worst outcome — penalise it.\n"
    "- A modelled/estimated answer that names its method + uncertainty BEATS both a refusal and a "
    "confident fabrication. Surfacing a concrete 'here's the data that would sharpen this' is a plus.\n"
    "Output ONLY JSON: {{\"winner\":\"A|B|tie\", \"site_specific\":\"A|B|tie\", "
    "\"data_grounded\":\"A|B|tie\", \"honest\":\"A|B|tie\", \"actionable\":\"A|B|tie\", "
    "\"A_attempted_answer\":true|false, \"B_hallucinated_specifics\":true|false, "
    "\"one_line_why\":\"...\"}}.\n\nQUESTION: {q}\n\nSYSTEM A:\n{a}\n\nSYSTEM B:\n{b}"
)


def judge(judge_cli, q, a, b):
    # isolate the judge's HOME too, so its own repo memory can't bias the verdict
    out = cli_run(judge_cli, JUDGE_PROMPT.format(q=q, a=a[:3000], b=b[:3000]), timeout=200,
                  isolate_home=True)
    m = re.search(r"\{.*\}", out, re.DOTALL)
    try:
        return json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        return {}


def run(start, count, baseline_cli, do_judge, judge_cli):
    qs = json.load(open(QFILE))
    for i in range(start, min(start + count, len(qs))):
        q = qs[i]
        print(f"\n===== Q{i}: {q}")
        print("  [A] our stack (Hermes+connectors+data) ...")
        A = run_A(q)
        print(f"      A: {A['secs']}s, connectors={A['connectors_used']}, gap={A['flagged_gap']}")
        print(f"  [B] baseline {baseline_cli} (clean tmpdir) ...")
        B = run_B(q, baseline_cli)
        print(f"      B: {B['secs']}s")
        rec = {"i": i, "question": q, "A": A, "B": B,
               "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
        if do_judge:
            rec["judge"] = judge(judge_cli, q, A["answer"], B["answer"])
            print(f"      JUDGE: {rec['judge'].get('winner')} — {rec['judge'].get('one_line_why','')[:80]}")
        with open(RESULTS, "a") as f:
            f.write(json.dumps(rec) + "\n")
        _write_report()


def _write_report():
    recs = [json.loads(l) for l in open(RESULTS)] if os.path.exists(RESULTS) else []
    L = ["# Head-to-head: our stack (A) vs plain CLI baseline (B)\n",
         f"{len(recs)} questions run.\n"]
    wins = {"A": 0, "B": 0, "tie": 0}
    gaps = []
    for r in recs:
        j = r.get("judge", {})
        wins[j.get("winner", "tie")] = wins.get(j.get("winner", "tie"), 0) + 1
        if r["A"].get("flagged_gap"):
            gaps.append(r["question"])
        L.append(f"## Q{r['i']}: {r['question']}")
        L.append(f"- **A** ({r['A']['secs']}s, connectors: {r['A'].get('connectors_used')}): "
                 f"{r['A']['answer'][:600].strip()}")
        L.append(f"- **B** ({r['B']['secs']}s): {r['B']['answer'][:600].strip()}")
        if j:
            L.append(f"- **judge:** winner={j.get('winner')} · site_specific={j.get('site_specific')} "
                     f"· data_grounded={j.get('data_grounded')} · B_hallucinated={j.get('B_hallucinated_specifics')} "
                     f"· _{j.get('one_line_why','')}_")
        L.append("")
    L.insert(2, f"**Wins:** A={wins.get('A',0)} · B={wins.get('B',0)} · tie={wins.get('tie',0)}\n")
    if gaps:
        L.append("## Candidate new connectors/datasets (A flagged a data gap)\n")
        for g in gaps:
            L.append(f"- {g}")
    open(REPORT, "w").write("\n".join(L) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate"); g.add_argument("--n", type=int, default=10)
    g.add_argument("--gen-cli", default="cursor-agent")
    r = sub.add_parser("run"); r.add_argument("--start", type=int, default=0)
    # baseline = cursor-agent (FRONTIER model — the representative "what Varun uses"). NOTE:
    # cursor is contaminated on this account (cloud memory leaks our context — see ROADBLOCKS.md);
    # run_B flags `leaked_our_context` per question so we know which comparisons are clean.
    # --baseline-cli raw = the context-free 122B control (a floor, not the real baseline).
    r.add_argument("--count", type=int, default=1); r.add_argument("--baseline-cli", default="cursor-agent")
    r.add_argument("--judge", action="store_true"); r.add_argument("--judge-cli", default="cursor-agent")
    a = ap.parse_args()
    if a.cmd == "generate":
        generate(a.gen_cli, a.n)
    else:
        run(a.start, a.count, a.baseline_cli, a.judge, a.judge_cli)
