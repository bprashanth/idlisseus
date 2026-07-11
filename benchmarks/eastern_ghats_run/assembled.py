#!/usr/bin/env python3
"""Assembled loop — "smart bookends, cheap middle" for place-based chat.

Per user message:
  control-IN   (smart) : clarify-gate → ASK a short question (turn ends) OR PROCEED with a tight directive.
  MIDDLE       (cheap) : the directive → hermes runner (qwen) runs connectors, resumed across turns.
  reasoning-OUT(smart) : the runner's raw output + constitution → SHORT answer + 1-3 follow-ups.

Smart calls are tiny, tool-less OpenRouter calls; the expensive tool grind stays on the cheap local model.
If smart == cheap (both qwen122b), the bookends run on qwen too (the split just collapses).

  python3 assembled.py bench [--n 2] [--smart glm5.2] [--cheap qwen122b]   # user-sim multi-turn experiment
  python3 assembled.py repl  [--smart glm5.2] [--cheap qwen122b]           # interactive (used by chat.sh)
  python3 assembled.py -q "question" [--smart ...] [--cheap ...]          # one message through the loop
"""
import argparse, json, os, re, subprocess, sys, time, urllib.request
import eg_bench, mt_bench

HERE = os.path.dirname(os.path.abspath(__file__))
CHAT = eg_bench.CHAT
CREDS = os.path.expanduser("~/.config/idlisseus/openrouter.json")
SLUG = {"glm5.2": "z-ai/glm-5.2", "deepseekv4": "deepseek/deepseek-v4-flash", "qwen122b": "qwen"}

GATE_SYS = ("You are the front desk of a data assistant bound to the 'Elephants by the Lake' restoration "
            "site (Eastern Ghats). A user sends a message. Using the conversation so far, decide in ONE "
            "line: if the entity/scope/goal is unclear, output 'ASK: <one short question that also asks "
            "what they're trying to understand>'. If it's clear enough to act, output 'PROCEED: <one-line "
            "directive naming exactly what to run, kept tight — no extra layers>'. Output ONLY that one line.")
SYNTH_SYS = ("A junior analyst gathered this for a BUSY field researcher who wants a ~1-minute answer. Write "
             "a SHORT chat reply: 2-4 sentences with the key real numbers; flag anything modelled as "
             "modelled (never as observed); then END with 1-3 concrete follow-up options they can pick. Add "
             "NO facts not in the analysis. No headings, no essay.")


def smart(model, system, user, max_tokens=500):
    key = json.load(open(CREDS))["api_key"]
    body = {"model": SLUG.get(model, model), "max_tokens": max_tokens, "temperature": 0.3,
            "reasoning": {"enabled": False},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=120))
    return (d["choices"][0]["message"].get("content") or "").strip(), d.get("usage", {}).get("total_tokens", 0)


def _cheap_is_local(cheap):
    return cheap in ("qwen122b", "qwen", "", None)


def run_cheap(cheap, directive, sid):
    """The directive → hermes runner. New session if sid is None, else --resume. Returns (raw_answer, sid, tools_delta)."""
    src = None
    env_prev_tools = 0
    if sid:
        m0 = eg_bench.mine(sid); env_prev_tools = m0["n_tool"] or 0
    else:
        src = f"asm_{int(time.time()*1000)}"
    dt = mt_bench.agent_turn(cheap, directive, source=src, resume=sid, timeout=600)
    if not sid:
        sid = eg_bench.find_session(src)
    m = eg_bench.mine(sid)
    return m["answer"], sid, (m["n_tool"] or 0) - env_prev_tools, dt


def turn(user_msg, st, smart_m, cheap_m):
    """One user message through the loop. st = {sid, transcript}. Returns (reply, kind, meta)."""
    convo = st["transcript"] or "(new conversation)"
    g, gtok = smart(smart_m, GATE_SYS, f"Conversation so far:\n{convo}\n\nNew user message: {user_msg}", 200)
    if g.upper().startswith("ASK") or (g.strip().endswith("?") and not g.upper().startswith("PROCEED")):
        q = re.sub(r"^ASK:\s*", "", g).strip()
        st["transcript"] += f"\nUSER: {user_msg}\nASSISTANT: {q}\n"
        return q, "ASK", {"gate_tok": gtok, "cheap_tools": 0, "synth_tok": 0}
    directive = re.sub(r"^PROCEED:\s*", "", g).strip() or user_msg
    raw, sid, tools, dt = run_cheap(cheap_m, directive, st["sid"]); st["sid"] = sid
    s, stok = smart(smart_m, SYNTH_SYS, raw[:3500], 500)
    reply = s or raw[:1000]
    st["transcript"] += f"\nUSER: {user_msg}\nASSISTANT: {reply}\n"
    return reply, "PROCEED", {"gate_tok": gtok, "cheap_tools": tools, "synth_tok": stok, "directive": directive, "sec": round(dt)}


def bench(n, smart_m, cheap_m, max_turns=4):
    out = os.path.join(HERE, "assembled_results.jsonl"); open(out, "w").close()
    for si, sc in enumerate(mt_bench.SCENARIOS[:n]):
        st = {"sid": None, "transcript": ""}
        turns = []
        for t in range(max_turns):
            umsg = sc["open"] if t == 0 else mt_bench.usersim(sc["goal"], st["transcript"])
            if umsg.strip().upper().startswith("DONE"):
                break
            reply, kind, meta = turn(umsg, st, smart_m, cheap_m)
            turns.append({"user": umsg, "kind": kind, "reply": reply, "len": len(reply), **meta})
            print(f"[S{si} t{t}] {kind} | cheap_tools={meta['cheap_tools']} len={len(reply)}", flush=True)
        rec = {"scenario": si, "open": sc["open"], "goal": sc["goal"], "n_turns": len(turns),
               "clarified_t1": turns and turns[0]["kind"] == "ASK",
               "short": all(x["len"] < 1100 for x in turns),
               "max_cheap_tools": max((x["cheap_tools"] for x in turns), default=0),
               "smart_tok": sum(x["gate_tok"] + x["synth_tok"] for x in turns), "turns": turns}
        open(out, "a").write(json.dumps(rec, ensure_ascii=False) + "\n")
    # summary
    rs = [json.loads(l) for l in open(out)]
    print(f"\nassembled ({smart_m} smart / {cheap_m} cheap), n={len(rs)}:")
    print(f"  clarified-turn1 {sum(r['clarified_t1'] for r in rs)}/{len(rs)} | "
          f"short {sum(r['short'] for r in rs)}/{len(rs)} | "
          f"mean turns {sum(r['n_turns'] for r in rs)/len(rs):.1f} | "
          f"mean max-cheap-tools {sum(r['max_cheap_tools'] for r in rs)/len(rs):.1f} | "
          f"mean smart-tok/convo {sum(r['smart_tok'] for r in rs)//len(rs)}")


def repl(smart_m, cheap_m):
    st = {"sid": None, "transcript": ""}
    print(f"[assembled] smart={smart_m} cheap={cheap_m} — type your message (Ctrl-D to exit)", file=sys.stderr)
    while True:
        try:
            u = input("you> ").strip()
        except EOFError:
            break
        if not u:
            continue
        reply, kind, meta = turn(u, st, smart_m, cheap_m)
        tag = "?" if kind == "ASK" else f"({meta['cheap_tools']} tools)"
        print(f"\nassistant {tag}: {reply}\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-q", "--query"); ap.add_argument("--smart", default="qwen122b"); ap.add_argument("--cheap", default="qwen122b")
    ap.add_argument("--n", type=int, default=2); ap.add_argument("cmd", nargs="?", default="repl")
    a = ap.parse_args()
    if a.query:
        st = {"sid": None, "transcript": ""}
        r, kind, meta = turn(a.query, st, a.smart, a.cheap); print(r)
    elif a.cmd == "bench":
        bench(a.n, a.smart, a.cheap)
    else:
        repl(a.smart, a.cheap)
