#!/usr/bin/env python3
"""Miner — read model_skill_results.jsonl, score each answer against the SYLLABUS rubric, and surface
the SKILL GAPS to harden the PLAYBOOK. Runs after (or during) the model×skill matrix.

For each question we encode the skill a good answer MUST show (which connector/behaviour). We then
report, per (model, skill) and overall, where answers missed the intended skill — those misses are the
PLAYBOOK-hardening candidates (e.g. "Q1 colocation answered without geo.cooccur → tighten the rule").

  python3 bench/mine_skill_gaps.py            # -> prints gap report + writes skill_gaps.md
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "model_skill_results.jsonl")
OUT = os.path.join(HERE, "skill_gaps.md")

# per-question expectation: (label, required connectors [any-of], required flags [all]).
# flag keys map to run_cell flags; 'verify' = verify_language, 'site' = mentions_site, etc.
EXPECT = {
    0:  ("lantana takeover / s2",        ["occurrence", "s2", "predict"], ["used_s2", "mentions_site", "honest_caveat"]),
    1:  ("what grows near lantana / coloc", ["geo", "occurrence", "paper_data"], ["used_colocation", "honest_caveat"]),
    2:  ("where is lantana / MAP",        ["s2", "embedding"], ["used_s2", "honest_caveat"]),
    3:  ("healthy-forest birds",          ["ebird", "indicators"], ["honest_caveat"]),
    4:  ("birds+trees overlap / coloc",   ["ebird", "geo", "occurrence"], ["used_colocation"]),
    5:  ("elephants eat / verify",        ["occurrence", "paper_data"], ["verify_language", "honest_caveat"]),
    6:  ("elephants+birds overlap / coloc", ["geo", "ebird", "occurrence"], ["used_colocation", "mentions_site"]),
    7:  ("inventory + canopy / s2",       ["s2", "landcover", "occurrence"], ["used_s2", "mentions_site"]),
    8:  ("seeds + trees near / phenology", ["phenology", "occurrence"], ["verify_language"]),
    9:  ("ponds dry first / water",       ["water", "greenness"], []),
    10: ("forest coming back",            ["greenness", "s2", "landcover"], ["honest_caveat"]),
    11: ("what data are we missing",      [], ["honest_caveat"]),
}


def load():
    return [json.loads(l) for l in open(RES)] if os.path.exists(RES) else []


def cell_gaps(r):
    """Return list of missed expectations for one cell."""
    label, conns_any, flags_all = EXPECT.get(r["qi"], ("?", [], []))
    used = set(r["connectors"])
    miss = []
    if conns_any and not (used & set(conns_any)):
        miss.append(f"no {'/'.join(conns_any)} connector (used {sorted(used) or 'none'})")
    for fk in flags_all:
        if not r["flags"].get(fk):
            miss.append(f"missing {fk}")
    if r["flags"].get("named_species", 0) >= 1 and not r["flags"].get("verify_language") and r["qi"] in (1, 5, 8):
        miss.append("named species WITHOUT verify-language")
    if r["flags"].get("mentions_corridor") and not r["flags"].get("mentions_site") and r["qi"] in (0, 2, 6, 7):
        miss.append("corridor-scale, not site-scale")
    if r.get("timed_out"):
        miss.append("TIMED OUT")
    if r["flags"].get("refused"):
        miss.append("REFUSED")
    return label, miss


def main():
    recs = load()
    if not recs:
        print("no results yet"); return
    L = ["# Skill gaps (miner over model×skill runs)\n", f"{len(recs)} cells.\n"]
    # aggregate misses by type
    by_type, by_cell = {}, []
    for r in recs:
        label, miss = cell_gaps(r)
        for m in miss:
            key = m.split(" (")[0]
            by_type[key] = by_type.get(key, 0) + 1
        by_cell.append((r, label, miss))
    L.append("## Most common gaps (harden these in PLAYBOOK)\n")
    for k, c in sorted(by_type.items(), key=lambda x: -x[1]):
        L.append(f"- **{c}×** {k}")
    # skilled vs naked adherence
    L.append("\n## Skilled vs naked (does the PLAYBOOK help?)\n")
    for sk in ("skilled", "naked"):
        sub = [(r, m) for (r, _, m) in by_cell if r["skill"] == sk]
        if sub:
            clean = sum(1 for _, m in sub if not m)
            L.append(f"- **{sk}**: {clean}/{len(sub)} cells hit every intended skill "
                     f"({100*clean//len(sub)}%)")
    # per model
    L.append("\n## Adherence by model (skilled only)\n")
    for mdl in ("122b", "glm", "deepseek"):
        sub = [(r, m) for (r, _, m) in by_cell if r["model"] == mdl and r["skill"] == "skilled"]
        if sub:
            clean = sum(1 for _, m in sub if not m)
            L.append(f"- **{mdl}**: {clean}/{len(sub)} clean")
    L.append("\n## Every cell's misses\n")
    for r, label, miss in sorted(by_cell, key=lambda x: (x[0]["qi"], x[0]["model"], x[0]["skill"])):
        tag = "✓ clean" if not miss else "· " + "; ".join(miss)
        L.append(f"- Q{r['qi']} [{r['model']}/{r['skill']}] {label} — {tag}")
    open(OUT, "w").write("\n".join(L) + "\n")
    print("\n".join(L[:40]))
    print(f"\n... full report -> {OUT}")


if __name__ == "__main__":
    main()
