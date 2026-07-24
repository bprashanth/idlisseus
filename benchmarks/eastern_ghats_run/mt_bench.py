#!/usr/bin/env python3
"""Multi-turn benchmark — realistic chat, because users NEVER ask a clean one-shot question.

A cheap USER-SIMULATOR (direct OpenRouter, no tools) role-plays a busy field researcher with a HIDDEN
GOAL: it opens vague, stays terse, reveals detail only when ASKED, and says DONE once the analyst has
actually helped toward the goal. The AGENT (qwen122b, local) is continued across turns via hermes
`--resume`. We score the BEHAVIOR the constitution demands, not just content:
  clarified (turn-1 asked instead of dumping) · asked_goal ("what do you want to understand?") ·
  short (every reply ~<1 min) · not_bloated (peak tools/turn) · transferred+flagged (modelled, corroborate) ·
  turns_to_done.

  python3 mt_bench.py run [--n 2] [--max-turns 5] [--agent qwen122b]
  python3 mt_bench.py show --scenario 0
"""
import argparse, json, os, re, subprocess, time, urllib.request
import eg_bench   # reuse find_session + mine (state.db)

HERE = os.path.dirname(os.path.abspath(__file__))
CHAT = eg_bench.CHAT
CREDS = os.path.expanduser("~/.config/idlisseus/openrouter.json")
OUT = os.path.join(HERE, "mt_results.jsonl")

# realistic vague openers + the researcher's HIDDEN goal (drives what a GOOD agent should clarify toward)
SCENARIOS = [
    {"open": "tell me about the invasives here",
     "goal": "I'm deciding where to focus weeding this season — I mainly want to know if lantana is spreading near my nursery plots and whether I should act now."},
    {"open": "what snakes are around?",
     "goal": "a worker was bitten near the lake last week; I want to know which venomous snakes are likely here and where they'd be, so I can warn the team."},
    {"open": "is the forest actually coming back?",
     "goal": "I need evidence of recovery over the last ~5 years for a donor report, plus any on-the-ground indicators I should start monitoring."},
    {"open": "tell me about the spiders here",
     "goal": "I'm curious whether any rare or cave-dwelling spiders occur near the site that would be worth a targeted survey."},
]

SIM_SYS = (
    "You are role-playing a BUSY FIELD RESEARCHER at the 'Elephants by the Lake' restoration site (Eastern "
    "Ghats, India), chatting with an AI conservation-data analyst. Your HIDDEN GOAL (do not volunteer it "
    "unless the analyst asks what you want): {goal}\n"
    "RULES: reply in ONE short, natural sentence like a real chat — never a paragraph. Reveal detail only "
    "when asked. If the analyst asks what you're trying to understand or which species/scope, answer "
    "briefly and truthfully from your goal. If the analyst has given a genuinely useful, actionable answer "
    "toward your goal (even 'no data but here's a modelled estimate + what to collect'), reply EXACTLY "
    "'DONE'. If the analyst dumped a long thesis without asking what you need, push back in one line.")


def usersim(goal, transcript, model="deepseek/deepseek-v4-flash"):
    key = json.load(open(CREDS))["api_key"]
    body = {"model": model, "max_tokens": 90, "temperature": 0.6,
            "messages": [{"role": "system", "content": SIM_SYS.format(goal=goal)},
                         {"role": "user", "content": "Conversation so far:\n" + transcript +
                          "\n\nYour next message (one short line, or DONE):"}]}
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        d = json.load(urllib.request.urlopen(req, timeout=60))
        return d["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return "DONE  # usersim error: " + str(e)[:50]


def agent_turn(agent, msg, source=None, resume=None, timeout=600):
    env = dict(os.environ, AUTO_APPROVE="1")
    if source:
        env["HERMES_SOURCE"] = source
    if resume:
        env["HERMES_RESUME"] = resume
    t0 = time.time()
    try:
        subprocess.run([CHAT, "--model", agent, msg], capture_output=True, text=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        pass
    return time.time() - t0


def run(n, max_turns, agent):
    done_idx = {json.loads(l)["scenario"] for l in open(OUT)} if os.path.exists(OUT) else set()
    for si, sc in enumerate(SCENARIOS[:n]):
        if si in done_idx:
            continue
        src = f"mt_{si}_{int(time.time())}"
        sid, prev_tools, transcript, turns = None, 0, "", []
        for t in range(max_turns):
            umsg = sc["open"] if t == 0 else usersim(sc["goal"], transcript)
            if umsg.strip().upper().startswith("DONE"):
                break
            dt = agent_turn(agent, umsg, source=src if t == 0 else None, resume=sid if t else None)
            if t == 0:
                sid = eg_bench.find_session(src)
            m = eg_bench.mine(sid)
            reply = m["answer"]
            tools_turn = (m["n_tool"] or 0) - prev_tools
            prev_tools = m["n_tool"] or 0
            transcript += f"\nRESEARCHER: {umsg}\nANALYST: {reply[:1200]}\n"
            turns.append({"user": umsg, "reply": reply, "tools": tools_turn, "sec": round(dt), "len": len(reply),
                          "connectors": m["connectors"]})
        rec = {"scenario": si, "open": sc["open"], "goal": sc["goal"], "session": sid,
               "n_turns": len(turns), "turns": turns, **score(turns)}
        with open(OUT, "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        s = rec
        print(f"[S{si}] turns={s['n_turns']} clarified={s['clarified']} asked_goal={s['asked_goal']} "
              f"short={s['short']} maxtools={s['max_tools']} transfer_flag={s['transfer_flagged']}", flush=True)


def score(turns):
    if not turns:
        return {"clarified": False, "asked_goal": False, "short": False, "max_tools": 0, "transfer_flagged": False}
    first = turns[0]["reply"]
    allreplies = " ".join(t["reply"].lower() for t in turns)
    transferred = any({"predict", "invasive", "s2", "greenness", "groundtruth_lens"} & set(t["connectors"]) for t in turns)
    return {
        "clarified": ("?" in first and len(first) < 900),                       # turn-1 asked, didn't dump
        "asked_goal": bool(re.search(r"what (are|do) you|trying to (understand|find|do)|looking to|"
                                     r"what.s your goal|why do you|help you with|specifically", allreplies)),
        "short": all(t["len"] < 1600 for t in turns),                           # every reply ~<1 min
        "max_tools": max(t["tools"] for t in turns),                            # bloat check (want ≤ ~8)
        "transfer_flagged": (not transferred) or bool(re.search(r"model|transpose|estimate|not observed|"
                             r"corroborate|field data|confirm", allreplies)),
    }


def show(si):
    for l in open(OUT):
        r = json.loads(l)
        if r["scenario"] == si:
            print(f"GOAL: {r['goal']}\n")
            for i, t in enumerate(r["turns"]):
                print(f"── turn {i} · {t['tools']} tools · {t['sec']}s ──")
                print(f"RESEARCHER: {t['user']}")
                print(f"ANALYST: {t['reply'][:1000]}\n")
            return


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    r = sub.add_parser("run"); r.add_argument("--n", type=int, default=len(SCENARIOS))
    r.add_argument("--max-turns", type=int, default=5); r.add_argument("--agent", default="qwen122b")
    sh = sub.add_parser("show"); sh.add_argument("--scenario", type=int, default=0)
    a = ap.parse_args()
    if a.cmd == "run":
        run(a.n, a.max_turns, a.agent)
    elif a.cmd == "show":
        show(a.scenario)
