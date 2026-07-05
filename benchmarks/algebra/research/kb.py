"""kb.py — the knowledge base: an append-only index of everything the research
loop learns (indicator, question, the paper it came from, the real reading or the
gap, and full provenance). This is what makes an open user question answerable
later, with sources."""
import json
import os
import re

KB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kb.jsonl")


def append(record):
    with open(KB, "a") as f:
        f.write(json.dumps(record) + "\n")


def load():
    if not os.path.exists(KB):
        return []
    return [json.loads(l) for l in open(KB) if l.strip()]


def _text(rec):
    ind = rec.get("indicator", {})
    return " ".join(str(x) for x in [
        rec.get("theme"), ind.get("indicator"), ind.get("question"),
        rec.get("result", {}).get("species_used"),
        (rec.get("paper") or {}).get("title")]).lower()


def retrieve(query, k=6):
    """Keyword overlap retrieval over the KB."""
    q = set(re.findall(r"[a-z]{3,}", query.lower()))
    scored = []
    for rec in load():
        t = set(re.findall(r"[a-z]{3,}", _text(rec)))
        s = len(q & t)
        if s:
            scored.append((s, rec))
    scored.sort(key=lambda x: -x[0])
    return [r for _, r in scored[:k]]
