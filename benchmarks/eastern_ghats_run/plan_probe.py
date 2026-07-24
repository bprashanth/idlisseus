#!/usr/bin/env python3
"""Planning-layer probes: does each model make the RIGHT tool-call decisions at the forks — without
running anything? Same router context for both. Three probes:
  1. cold transfer plan  — clear question, do they produce resolve→points→gate→model→verify (right order)?
  2. gate FAILS          — injected: donor mismatch + gate REFUSE. Do they refuse the transfer honestly?
  3. points IN the AOI   — injected: 60 local records. Do they just report (STATE), or needlessly model?
"""
import json, os, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
CREDS = os.path.expanduser("~/.config/idlisseus/openrouter.json")
ROUTER = open(os.path.join(REPO, "benchmarks/semantic_broker/connectors/PLAYBOOK.md")).read()

SYS = ("You are the PLANNING step of a data assistant bound to the 'Elephants by the Lake' (EBTL) site "
       "(Eastern Ghats; site bbox ~78.170,12.721,78.197,12.747). Below is your router/playbook. Output "
       "ONLY your tool-call plan / next steps as a short numbered list (connector + key args + <=6-word "
       "reason). Do NOT run anything and do NOT write a final prose answer.\n\n=== ROUTER ===\n" + ROUTER)

PROBES = [
    ("1. COLD transfer plan (clear question)",
     "The user asks: 'Map where Russell's viper (Daboia russelii) is likely across our EBTL site.' Scope is "
     "clear (the ~2.9 km EBTL site); no clarification needed. Give your full tool-call plan."),
    ("2. GATE FAILS (injected refuse)",
     "Question: 'Map where the Malabar pit viper is likely at EBTL.' You ALREADY ran points.get and got 45 "
     "donor records — all from wet Western-Ghats rainforest. The gate returned: looks-alike analog=0.05 "
     "(FAIL), climate MESS=out-of-envelope (FAIL) => REFUSE. What is your next step / plan from here?"),
    ("3. POINTS INSIDE THE AOI (injected local data)",
     "Question: 'Where are the cobras on our EBTL site?' You ALREADY ran points.get and it returned 60 "
     "verified iNaturalist+GBIF cobra records INSIDE the EBTL site bbox. What is your next step / plan from here?"),
]


def glm(msg):
    key = json.load(open(CREDS))["api_key"]
    body = {"model": "z-ai/glm-5.2", "max_tokens": 500, "temperature": 0.2, "reasoning": {"enabled": False},
            "messages": [{"role": "system", "content": SYS}, {"role": "user", "content": msg}]}
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    return (json.load(urllib.request.urlopen(req, timeout=120))["choices"][0]["message"].get("content") or "").strip()


def qwen(msg):
    body = {"model": "qwen", "max_tokens": 700, "temperature": 0.2,
            "chat_template_kwargs": {"enable_thinking": False},
            "messages": [{"role": "system", "content": SYS}, {"role": "user", "content": msg}]}
    req = urllib.request.Request("http://172.17.0.1:8001/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return (json.load(urllib.request.urlopen(req, timeout=120))["choices"][0]["message"].get("content") or "").strip()


if __name__ == "__main__":
    out = []
    for name, msg in PROBES:
        print("\n" + "#" * 92 + f"\n# PROBE {name}\n" + "#" * 92)
        try: g = glm(msg)
        except Exception as e: g = f"[glm err: {e}]"
        try: w = qwen(msg)
        except Exception as e: w = f"[qwen err: {e}]"
        print("\n--- glm-5.2 ---\n" + g + "\n\n--- hermes/qwen122b ---\n" + w)
        out.append({"probe": name, "glm": g, "qwen": w})
    json.dump(out, open(os.path.join(HERE, "plan_probe_results.json"), "w"), indent=1, ensure_ascii=False)
