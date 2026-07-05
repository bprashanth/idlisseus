"""loop.py — the AOI bootstrap tick (NOTES.md §8, first iteration).

Wires the components for one AOI: Scout discovers + verifies sources, Proposer
emits candidate questions, Controller classifies/dedups them into a bank, Miner
turns past run-logs into playbook rules. Writes the AOI's starter corpus.

This is what the OVERNIGHT run starts from: after bootstrap, the loop iterates the
`answerable_now` + `needs_connector` questions through run_solver.sh (solve ->
detect struggle -> write+gate connector -> mint gold -> judge -> ledger), with the
Controller escalating and the Miner mining each tick. Bootstrap itself makes no
LLM/solve call, so it's fast and safe to run first.

Usage: python3 components/loop.py --aoi aois/elephants_by_the_lake.json
"""
import argparse
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ALGEBRA = os.path.dirname(HERE)
SB_CONNECTORS = os.path.normpath(os.path.join(ALGEBRA, "..", "semantic_broker", "connectors"))
sys.path.insert(0, HERE)
import scout, proposer, controller, miner  # noqa: E402


def library_connectors():
    out = set()
    for f in glob.glob(os.path.join(SB_CONNECTORS, "*.py")):
        n = os.path.splitext(os.path.basename(f))[0]
        if n not in ("_base", "__init__"):
            out.add(n)
    return out


def bootstrap(aoi_path):
    aoi = json.load(open(aoi_path))
    outdir = os.path.join(ALGEBRA, "aois", aoi["name"])
    os.makedirs(outdir, exist_ok=True)
    lib = library_connectors()

    disc = scout.discover(aoi)
    available_species = [s["target"] for s in disc["available"]]
    json.dump(disc, open(os.path.join(outdir, "sources.json"), "w"), indent=2)

    cands = proposer.propose(aoi, n=12)
    bank_path = os.path.join(outdir, "questions.jsonl")
    bank = controller.load_bank(bank_path)
    admitted, data_needs = controller.next_batch(aoi, cands, lib, available_species, bank)
    controller.append_bank(bank_path, admitted)

    mined = miner.mine(os.path.join(ALGEBRA, "runs", "*.log"),
                       statedb=os.path.expanduser("~/.hermes/state.db"))
    miner.write_playbook_rules(mined, os.path.join(outdir, "playbook_rules.md"))

    _report(aoi, lib, disc, admitted, data_needs, mined,
            os.path.join(outdir, "bootstrap_report.md"))
    return {"aoi": aoi["name"], "outdir": outdir, "library": sorted(lib),
            "available": available_species, "phantom": [p["target"] for p in disc["phantom"]],
            "admitted": admitted, "data_needs": data_needs, "mined": mined}


def _report(aoi, lib, disc, admitted, data_needs, mined, path):
    L = []
    L.append(f"# AOI bootstrap — {aoi['label']}\n")
    L.append(f"- **ecoregion:** {aoi.get('ecoregion')} ({aoi.get('biome')})")
    L.append(f"- **landscape:** {aoi.get('landscape')}")
    L.append(f"- **bbox:** {aoi['bbox']}  center {aoi['center']}")
    L.append(f"- **library connectors:** {', '.join(sorted(lib))}\n")

    L.append("## Scout — verified data frontier\n")
    L.append("**Available species (returned rows — usable now):**")
    for s in disc["available"]:
        ibp = s.get("ibp", {}).get("n_records")
        ibp_s = f" + {ibp} via IBP" if ibp else ""
        L.append(f"- {s['target']} — {s.get('n_records', '?')} GBIF records{ibp_s}")
    L.append("\n**Phantom (found but 0 rows — flagged, NOT admitted):**")
    for s in disc["phantom"]:
        L.append(f"- {s['target']} — {s.get('note', s.get('error'))}")
    L.append("\n**Research (Zenodo):**")
    for r in disc.get("research", []):
        L.append(f"- q={r['query']!r}: {r.get('n_total', '?')} records")
        for h in (r.get("sample") or [])[:1]:
            L.append(f"    - {h.get('title')} ({h.get('doi')})")
    L.append("\n**Analog ecoregion sites (tagged analog_ecoregion — same ecoregion, outside AOI):**")
    for a in disc.get("analog", []):
        L.append(f"- {a['site']} — {a.get('gbif_records', '?')} GBIF records, "
                 f"{a.get('research', {}).get('n_total', '?')} Zenodo records")
    L.append("\n**Catalog datasets (CKAN package_search):**")
    for c in disc["catalogs"]:
        tag = "ok" if c.get("verified_queryable") else "0 hits"
        L.append(f"- [{c['bucket']}] {c['ref']} q={c['query']!r}: {c.get('n_total','?')} total ({tag})")
        for h in (c.get("hits") or [])[:1]:
            L.append(f"    - {h['title']} — {h['url']}")

    L.append("\n## Controller — first question batch\n")
    for st in ("answerable_now", "needs_connector"):
        rows = [a for a in admitted if a["status"] == st]
        if rows:
            L.append(f"**{st}:**")
            for a in rows:
                L.append(f"- [{a['bucket']} w{a['weight']}] {a['question']}")
                L.append(f"    - shape: {a['primitive_shape']} | connectors: {a['connectors'] or '—'} | {a['reason']}")
    if data_needs:
        L.append("\n**blocked_no_data (Scout work orders):**")
        for d in data_needs:
            L.append(f"- {d['question']} — {d['reason']}")

    L.append("\n## Miner — playbook rules from past runs\n")
    L.append(f"Scanned {mined['scanned_logs']} log(s); {len(mined['rules'])} recurring pattern(s):")
    for r in mined["rules"]:
        L.append(f"- **{r['pattern']}** (x{r['occurrences']}): {r['rule']}")

    L.append("\n## What the overnight run does next\n")
    needs = [a for a in admitted if a["status"] == "needs_connector"]
    L.append(f"- Solve the {len([a for a in admitted if a['status']=='answerable_now'])} "
             "answerable-now question(s) via run_solver.sh; gold from tested connectors.")
    L.append(f"- The {len(needs)} needs_connector question(s) trigger connector writes — "
             "note the breakers below are NEW PRIMITIVES this AOI demands:")
    for a in needs:
        if a["is_breaker"]:
            L.append(f"    - {a['primitive_shape']} for: {a['question']}")
    L.append("- Controller escalates once pass-rate ≥ 0.80; Miner re-mines each tick.")
    open(path, "w").write("\n".join(L) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--aoi", required=True)
    args = ap.parse_args()
    r = bootstrap(args.aoi)
    print(json.dumps({k: v for k, v in r.items() if k != "mined"}, indent=2)[:2000])
    print(f"\nwrote corpus -> {r['outdir']}/ (sources.json, questions.jsonl, "
          "playbook_rules.md, bootstrap_report.md)")
