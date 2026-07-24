#!/usr/bin/env python3
"""glm planning vs hermes(qwen) planning — show the tool-call PLAN each proposes, without running tools.

Same context for both (the router + connector list, i.e. what hermes gives its model), same plan-only
instruction. glm via OpenRouter; qwen via the local vLLM (172.17.0.1:8001). Pure planning — no execution.

  python3 plan_compare.py
"""
import json, os, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
CREDS = os.path.expanduser("~/.config/idlisseus/openrouter.json")
ROUTER = open(os.path.join(REPO, "benchmarks/semantic_broker/connectors/PLAYBOOK.md")).read()

QUESTIONS = [
    "do cobras live around lantana?",
    "where can I find the green cat snake at ebtl?",
    "is the forest coming back?",
    "which venomous snakes are here?",
    "map lantana near my nursery plots",
]

SYS = ("You are the PLANNING step of a data assistant bound to the 'Elephants by the Lake' site (Eastern "
       "Ghats). Below is your router/playbook. For the user's question, output ONLY your PLAN: a short "
       "numbered list of the connector tool-calls you would make (name + key args) with a <=6-word reason "
       "each. Do NOT run anything, do NOT write the final answer. If genuinely ambiguous, step 1 may be a "
       "clarifying question. Max 7 steps.\n\n=== ROUTER ===\n" + ROUTER)


def glm(q):
    key = json.load(open(CREDS))["api_key"]
    body = {"model": "z-ai/glm-5.2", "max_tokens": 500, "temperature": 0.2, "reasoning": {"enabled": False},
            "messages": [{"role": "system", "content": SYS}, {"role": "user", "content": q}]}
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=120))
    return (d["choices"][0]["message"].get("content") or "").strip()


def qwen(q):
    body = {"model": "qwen", "max_tokens": 700, "temperature": 0.2,
            "chat_template_kwargs": {"enable_thinking": False},   # qwen is a reasoning model — suppress think block
            "messages": [{"role": "system", "content": SYS}, {"role": "user", "content": q}]}
    req = urllib.request.Request("http://172.17.0.1:8001/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=120))
    return (d["choices"][0]["message"].get("content") or "").strip()


if __name__ == "__main__":
    out = []
    for q in QUESTIONS:
        print("\n" + "=" * 90 + f"\nQ: {q}\n" + "=" * 90)
        try:
            g = glm(q)
        except Exception as e:
            g = f"[glm err: {e}]"
        try:
            w = qwen(q)
        except Exception as e:
            w = f"[qwen err: {e}]"
        print("\n--- glm-5.2 PLAN ---\n" + g)
        print("\n--- hermes/qwen122b PLAN ---\n" + w)
        out.append({"q": q, "glm": g, "qwen": w})
    json.dump(out, open(os.path.join(HERE, "plan_compare_results.json"), "w"), indent=1, ensure_ascii=False)
