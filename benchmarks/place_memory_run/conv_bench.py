#!/usr/bin/env python3
"""Multi-turn place-memory benchmark — constitution adherence + expected-tool spread across configs.

Configs (all MULTI-TURN via a user-simulator with a hidden goal; qwen122b is the cheap local runner):
  qwen      : plain hermes/qwen122b (baseline).
  capnudge  : qwen + a terse system nudge + a hard tool cap (HERMES_MAXTURNS) — mechanism only, no smart model.
  bookends  : clarify-gate (smart) → qwen → synthesizer (smart)  [uses assembled.turn].

Scores each scenario vs its expected outcome (syllabus.json): clarified-when-expected · short · hit the
expected connectors · flagged modelled when it transferred · papers-first when literature · resolved the
name · not-empty. Golden subset = hard regression asserts (green cat snake → Boiga cyanea + flag; short).

  python3 conv_bench.py run --config qwen [--n 13] [--max-turns 4]
  python3 conv_bench.py report
  python3 conv_bench.py golden      # hard pass/fail regression gate
"""
import argparse, json, os, re, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "eastern_ghats_run"))   # reuse the harness modules
import eg_bench, mt_bench, assembled

SYL = json.load(open(os.path.join(HERE, "syllabus.json")))
CHAT = eg_bench.CHAT
OUT = lambda c: os.path.join(HERE, f"results_{c}.jsonl")
TERSE = ("Be concise for a busy field officer: lead with the finding in 2-4 sentences + real numbers, "
         "say clearly what is observed vs MODELLED (and 'backed by N records'), then end with 1-3 short "
         "follow-up options. Do not write an essay. ALWAYS end the turn with a final text answer — if "
         "you've run a few tools, STOP and answer from what you have; never end on a tool call. If the "
         "request is vague/broad ('tell me about X', 'what's here'), FIRST ask ONE short clarifying "
         "question (which one? what do you want to understand?) and run NO tools that turn. Question: ")


def _hermes(msg, source, resume, maxturns):
    env = dict(os.environ, AUTO_APPROVE="1")
    if source: env["HERMES_SOURCE"] = source
    if resume: env["HERMES_RESUME"] = resume
    if maxturns: env["HERMES_MAXTURNS"] = str(maxturns)
    try:
        subprocess.run([CHAT, "--model", "qwen122b", msg], capture_output=True, text=True, timeout=600, env=env)
    except subprocess.TimeoutExpired:
        pass


def qwen_turn(msg, st, terse=False, maxturns=None):
    prev = (eg_bench.mine(st["sid"])["n_tool"] or 0) if st["sid"] else 0
    src = None if st["sid"] else f"cb_{int(time.time()*1000)}"
    _hermes((TERSE + msg) if terse else msg, src, st["sid"], maxturns)
    if not st["sid"]:
        st["sid"] = eg_bench.find_session(src)
    m = eg_bench.mine(st["sid"])
    return m["answer"], "PROCEED", {"cheap_tools": (m["n_tool"] or 0) - prev}


def run_scenario(sc, config, max_turns):
    st = {"sid": None, "transcript": ""}
    turns = []
    for t in range(max_turns):
        umsg = sc["open"] if t == 0 else mt_bench.usersim(sc["goal"], st["transcript"])
        if umsg.strip().upper().startswith("DONE"):
            break
        if config == "bookends":
            reply, kind, meta = assembled.turn(umsg, st, "glm5.2", "qwen122b")
        elif config == "capnudge":
            reply, kind, meta = qwen_turn(umsg, st, terse=True, maxturns=14)
        else:
            reply, kind, meta = qwen_turn(umsg, st)
        st["transcript"] += f"\nUSER: {umsg}\nASSISTANT: {reply[:900]}\n"
        turns.append({"user": umsg, "kind": kind, "reply": reply, "len": len(reply), **meta})
        print(f"  [{sc['id']}/{config} t{t}] {kind} tools={meta.get('cheap_tools',0)} len={len(reply)}", flush=True)
    return turns, st["sid"]


def score(sc, turns, sid):
    m = eg_bench.mine(sid) if sid else {"connectors": [], "resolved": False, "papers": False, "answer": ""}
    conns = set(m["connectors"]); alltext = " ".join(t["reply"].lower() for t in turns)
    exp = set(sc["expect_connectors"])
    hit = len(exp & conns) / len(exp) if exp else 1.0
    clar1 = turns and (turns[0]["kind"] == "ASK" or ("?" in turns[0]["reply"] and turns[0]["len"] < 700))
    r = {
        "clarified_ok": (clar1 == sc["expect_clarify"]) or (clar1 and not sc["expect_clarify"]) is False and (bool(clar1) == sc["expect_clarify"]),
        "clarified": bool(clar1),
        "short": all(t["len"] < 1100 for t in turns) if turns else False,
        "conn_hit": round(hit, 2),
        "transfer_flag_ok": (not sc["expect_transfer_flag"]) or bool(re.search(r"model|transpose|estimate|backed by|record", alltext)),
        "papers_ok": (not sc["papers_first"]) or m["papers"],
        "resolved_ok": (not sc.get("must_resolve")) or (sc["must_resolve"].lower() in alltext or m["resolved"]),
        "not_empty": bool(turns) and turns[-1]["len"] > 120,
        "n_turns": len(turns), "max_tools": max((t.get("cheap_tools", 0) for t in turns), default=0),
        "connectors": sorted(conns),
    }
    r["clarified_ok"] = bool(clar1) == bool(sc["expect_clarify"])
    return r


def run(config, n, max_turns):
    done = {json.loads(l)["id"] for l in open(OUT(config))} if os.path.exists(OUT(config)) else set()
    for sc in SYL[:n]:
        if sc["id"] in done:
            continue
        print(f"=== {sc['id']} [{config}] ===", flush=True)
        turns, sid = run_scenario(sc, config, max_turns)
        rec = {"id": sc["id"], "category": sc["category"], "config": config, "session": sid,
               "regression": sc.get("regression", False), **score(sc, turns, sid),
               "turns": [{"u": t["user"], "r": t["reply"][:1500], "len": t["len"]} for t in turns]}
        open(OUT(config), "a").write(json.dumps(rec, ensure_ascii=False) + "\n")


SIGNALS = ["clarified_ok", "short", "conn_hit", "transfer_flag_ok", "papers_ok", "resolved_ok", "not_empty"]


def report():
    print(f"{'config':10} {'n':>3} {'turns':>5} {'tools':>5} | " + " ".join(f"{s[:8]:>8}" for s in SIGNALS))
    for c in ["qwen", "capnudge", "bookends"]:
        if not os.path.exists(OUT(c)):
            continue
        rs = [json.loads(l) for l in open(OUT(c))]
        if not rs:
            continue
        av = lambda k: sum(r[k] for r in rs) / len(rs)
        print(f"{c:10} {len(rs):>3} {av('n_turns'):>5.1f} {av('max_tools'):>5.1f} | "
              + " ".join(f"{av(s):>8.2f}" for s in SIGNALS))


def golden():
    """Hard regression gate. Returns nonzero if any golden assertion fails."""
    fails = []
    for c in ["qwen", "capnudge", "bookends"]:
        if not os.path.exists(OUT(c)):
            continue
        for r in (json.loads(l) for l in open(OUT(c))):
            if r["id"] == "green_cat_snake":
                if not r["resolved_ok"]: fails.append(f"{c}:green_cat_snake did NOT resolve to Boiga cyanea")
                if not r["transfer_flag_ok"]: fails.append(f"{c}:green_cat_snake did NOT flag modelled")
            if not r["short"]: fails.append(f"{c}:{r['id']} not short")
            if not r["not_empty"]: fails.append(f"{c}:{r['id']} empty")
    if fails:
        print("GOLDEN FAIL:"); [print("  -", f) for f in fails]; return 1
    print("GOLDEN PASS"); return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    r = sub.add_parser("run"); r.add_argument("--config", required=True, choices=["qwen", "capnudge", "bookends"])
    r.add_argument("--n", type=int, default=len(SYL)); r.add_argument("--max-turns", type=int, default=4)
    sub.add_parser("report"); sub.add_parser("golden")
    a = ap.parse_args()
    if a.cmd == "run": run(a.config, a.n, a.max_turns)
    elif a.cmd == "golden": raise SystemExit(golden())
    else: report()
