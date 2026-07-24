#!/usr/bin/env python3
"""Clarify classifier — the DETERMINISTIC route to "clarify only when genuinely vague".

qwen's clarify (via prose steering) is variable; a smart model can decide it reliably. This tests a tiny
tool-less classifier (CLARIFY vs PROCEED) on a labeled set of openers, against glm-5.2 and deepseek-v4.
If it's accurate, it can be wired into the discipline plugin's pre_llm_call (run the classifier; on CLARIFY
inject a hard "ask ONE question now"; on PROCEED inject the normal answer steer).

  python3 clarify_classifier.py            # runs both models, prints accuracy + disagreements
"""
import json, os, urllib.request

CREDS = os.path.expanduser("~/.config/idlisseus/openrouter.json")
MODELS = {"glm5.2": "z-ai/glm-5.2", "deepseekv4": "deepseek/deepseek-v4-flash"}

# opener -> expected label. CLARIFY = subject/scope/goal genuinely too vague; PROCEED = clear subject + a
# reasonable default interpretation (answer, state assumptions).
LABELED = [
    ("tell me about snakes at ebtl", "CLARIFY"),
    ("tell me about the invasives here", "CLARIFY"),
    ("tell me about the spiders here", "CLARIFY"),
    ("what's here?", "CLARIFY"),
    ("what should I plant?", "CLARIFY"),
    ("how's the site doing?", "CLARIFY"),
    ("tell me about the birds", "CLARIFY"),
    ("which venomous snakes are recorded around ebtl?", "PROCEED"),
    ("where are the lakes and ponds on our land?", "PROCEED"),
    ("map where russell's viper is likely across the site", "PROCEED"),
    ("do cobras live around the lantana here?", "PROCEED"),
    ("is the forest coming back over the last 5 years?", "PROCEED"),
    ("how much tree cover do we have?", "PROCEED"),
    ("which native trees are fruiting now for seed collection?", "PROCEED"),
    ("where are the rocky, steep patches to avoid planting?", "PROCEED"),
    ("what's the IUCN status of the indian rock python here?", "PROCEED"),
]

SYS = ("You are a TRIAGE step for a place-based data assistant bound to a restoration site. Given the user's "
       "OPENING message, decide:\n"
       "- CLARIFY: the subject/scope/goal is genuinely too vague to answer well (e.g. 'tell me about X', "
       "'what's here', 'how's it doing') — one short clarifying question would help first.\n"
       "- PROCEED: there is a clear subject AND a reasonable default interpretation — just answer (state "
       "assumptions if needed).\n"
       "Output EXACTLY one word: CLARIFY or PROCEED.")


def classify(model, opener):
    key = json.load(open(CREDS))["api_key"]
    body = {"model": MODELS[model], "max_tokens": 8, "temperature": 0.0, "reasoning": {"enabled": False},
            "messages": [{"role": "system", "content": SYS}, {"role": "user", "content": opener}]}
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    txt = (json.load(urllib.request.urlopen(req, timeout=60))["choices"][0]["message"].get("content") or "").strip().upper()
    return "CLARIFY" if "CLARIF" in txt else ("PROCEED" if "PROCEED" in txt else txt[:10])


if __name__ == "__main__":
    results = {}
    for m in MODELS:
        rows, correct = [], 0
        for opener, exp in LABELED:
            got = classify(m, opener)
            ok = (got == exp)
            correct += ok
            rows.append((opener, exp, got, ok))
        results[m] = (correct / len(LABELED), rows)
        print(f"\n=== {m}: accuracy {correct}/{len(LABELED)} = {correct/len(LABELED):.2f} ===")
        for opener, exp, got, ok in rows:
            if not ok:
                print(f"  MISS  exp={exp:8} got={got:8} :: {opener}")
    json.dump({m: {"acc": r[0], "rows": r[1]} for m, r in results.items()},
              open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "clarify_classifier_results.json"), "w"), indent=1)
    print("\nsummary:", {m: round(r[0], 2) for m, r in results.items()})
