#!/usr/bin/env python3
"""Top-3 smart+less-smart positionings — where does a SMART model (glm-5.2) best help the cheap local
runner (qwen122b)? Opposite of the failed smart-planner→dumb-runner: put smart at the EDGES.

The 3 configs, tested against qwen-alone (the mt_bench multi-turn answers):
  1) CLARIFY-GATE (control-in)  — smart makes the ask-vs-proceed decision up front (the thing qwen won't).
  2) SYNTHESIZER (reasoning-out)— qwen gathers; smart writes the SHORT answer + follow-ups from its output.
  3) VERIFIER (control-out)     — qwen answers; smart cheaply checks (short? flagged-modelled? unverified
     species?) and corrects.
Smart steps are single tool-less OpenRouter calls → cheap + fast. Scores the constitution behaviors.

  python3 smart_exp.py run
"""
import json, os, re, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CREDS = os.path.expanduser("~/.config/idlisseus/openrouter.json")
MT = os.path.join(HERE, "mt_results.jsonl")
SMART = "z-ai/glm-5.2"


def smart(system, user, max_tokens=600):
    key = json.load(open(CREDS))["api_key"]
    body = {"model": SMART, "max_tokens": max_tokens, "temperature": 0.3,
            "reasoning": {"enabled": False},               # clarify/synth/verify are simple → no thinking, clean content
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=120))
    m = d["choices"][0]["message"]
    txt = (m.get("content") or "").strip()               # content ONLY — never the reasoning trace
    return txt, d.get("usage", {}).get("total_tokens", 0)


GATE_SYS = ("You are the front desk of a conservation-data assistant for the 'Elephants by the Lake' site "
            "(Eastern Ghats, India). A busy field researcher sends a message. In ONE short line: if scope is "
            "unclear (which species? what do they want to understand?), ask a SHORT clarifying question that "
            "also asks what they're trying to understand. If clear enough to act, output 'PROCEED: <one-line "
            "directive>'. Terse — this is a chat, not a report.")
SYNTH_SYS = ("A junior analyst gathered this raw analysis for a busy field researcher. Rewrite it as a SHORT "
             "chat reply: 2-4 sentences with the key real numbers, then 1-3 concrete follow-ups they can pick. "
             "Flag anything modelled as modelled. Add NO facts not in the analysis. No headings, no thesis.")
VERIFY_SYS = ("Check this assistant answer against 4 rules: (1) SHORT not a thesis, (2) labels modelled vs "
              "observed, (3) states no species as fact without a source, (4) ends with a next step/follow-up. "
              "If it passes all, output 'PASS'. Otherwise output 'FIX:' then a corrected SHORT version.")


def run():
    rows = sorted((json.loads(l) for l in open(MT)), key=lambda r: r["scenario"])
    out = {"clarify_gate": [], "synth": [], "verify": []}
    for r in rows:
        qwen_first = r["turns"][0]["reply"]
        # 1) clarify-gate on the vague opening
        g, gt = smart(GATE_SYS, r["open"], max_tokens=200)
        asked = ("?" in g) and (not g.strip().upper().startswith("PROCEED")) and len(g) < 400
        out["clarify_gate"].append({"s": r["scenario"], "open": r["open"], "gate": g, "asked": asked, "tok": gt})
        # 2) synthesizer over qwen's raw answer
        sy, st = smart(SYNTH_SYS, qwen_first[:3500], max_tokens=400)
        out["synth"].append({"s": r["scenario"], "short": len(sy) < 1100, "has_followup": "?" in sy,
                             "flagged": bool(re.search(r"model|estimate|not observed|corroborate", sy, re.I)),
                             "len": len(sy), "text": sy, "tok": st})
        # 3) verifier over qwen's raw answer
        v, vt = smart(VERIFY_SYS, qwen_first[:3500], max_tokens=400)
        out["verify"].append({"s": r["scenario"], "verdict": "PASS" if v.strip().upper().startswith("PASS") else "FIX",
                             "caught": v.strip().upper().startswith("FIX"), "tok": vt, "text": v[:400]})
    json.dump(out, open(os.path.join(HERE, "smart_exp_results.json"), "w"), indent=1, ensure_ascii=False)
    # summary vs qwen-alone baseline
    base_clar = sum(1 for r in rows if r["clarified"]) / len(rows)
    base_short = sum(1 for r in rows if r["short"]) / len(rows)
    print(f"qwen-alone baseline:  clarified {base_clar:.2f} | short {base_short:.2f}  (n={len(rows)})")
    g = out["clarify_gate"]; s = out["synth"]; v = out["verify"]
    print(f"1) CLARIFY-GATE (glm): asked-when-vague {sum(x['asked'] for x in g)}/{len(g)} | "
          f"~{sum(x['tok'] for x in g)//len(g)} tok/call")
    print(f"2) SYNTHESIZER  (glm): short {sum(x['short'] for x in s)}/{len(s)} | "
          f"followups {sum(x['has_followup'] for x in s)}/{len(s)} | flagged {sum(x['flagged'] for x in s)}/{len(s)} "
          f"| mean {sum(x['len'] for x in s)//len(s)} chars (qwen mean {sum(len(r['turns'][0]['reply']) for r in rows)//len(rows)})")
    print(f"3) VERIFIER     (glm): caught-violation {sum(x['caught'] for x in v)}/{len(v)} "
          f"(qwen answers that need fixing)")


if __name__ == "__main__":
    run()
