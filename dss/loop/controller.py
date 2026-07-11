"""Controller — curriculum + question bank (NOTES.md Add 1).

Tracks 122B's pass-rate, escalates difficulty when it clears threshold, dedups
against the bank, and classifies each proposed question by whether the current
library can answer it. The "needs_connector" bucket is the engine of the loop:
those are the questions just past the toolbox edge that trigger a connector write
(and, for breaker shapes, the discovery of a new primitive).
"""
import json
import os
import re

ESCALATE_AT = 0.80     # pass-rate over last K -> ask for a harder batch
LAST_K = 10


def _words(q):
    return set(re.findall(r"[a-z]+", q.lower()))


def _is_dup(q, existing, thresh=0.8):
    a = _words(q)
    for e in existing:
        b = _words(e)
        if a and b and len(a & b) / len(a | b) >= thresh:
            return True
    return False


def pass_rate(bank, k=LAST_K):
    solved = [b for b in bank if b.get("plan_match") is not None][-k:]
    if not solved:
        return None
    return sum(1 for b in solved if b.get("number_match")) / len(solved)


def should_escalate(bank, k=LAST_K, thresh=ESCALATE_AT):
    pr = pass_rate(bank, k)
    return pr is not None and pr >= thresh


def _needs_species(q):
    ql = q.lower()
    return any(w in ql for w in ("record", "occur", "invad", "spread"))


def classify(candidate, library_connectors, available_species, aoi):
    """answerable_now | needs_connector | blocked_no_data, with the reason."""
    conns_ok = all(c in library_connectors for c in candidate["connectors"])
    # species-dependent questions need the seed species to be scout-verified
    data_ok = True
    if _needs_species(candidate["question"]) and aoi.get("seed_species"):
        data_ok = any(s in available_species for s in aoi["seed_species"])
    if not data_ok:
        return "blocked_no_data", "no scout-verified occurrence data in AOI"
    if candidate["is_breaker"]:
        return "needs_connector", f"breaker primitive: {candidate['primitive_shape']}"
    if not conns_ok:
        missing = [c for c in candidate["connectors"] if c not in library_connectors]
        return "needs_connector", f"missing connector(s): {missing}"
    return "answerable_now", "library covers it"


def next_batch(aoi, candidates, library_connectors, available_species, bank):
    """Admit non-duplicate candidates, tagged with status. Blocked-no-data ones are
    returned separately as data_needs (a work order for the Scout)."""
    existing = [b["question"] for b in bank]
    admitted, data_needs = [], []
    for c in candidates:
        if _is_dup(c["question"], existing):
            continue
        status, reason = classify(c, library_connectors, available_species, aoi)
        rec = {**c, "aoi": aoi["name"], "status": status, "reason": reason,
               "plan_match": None, "number_match": None}
        if status == "blocked_no_data":
            data_needs.append(rec)
        else:
            admitted.append(rec)
            existing.append(c["question"])
    return admitted, data_needs


def load_bank(path):
    if not os.path.exists(path):
        return []
    return [json.loads(l) for l in open(path) if l.strip()]


def append_bank(path, records):
    with open(path, "a") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
