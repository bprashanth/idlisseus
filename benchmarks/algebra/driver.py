#!/usr/bin/env python3
"""driver.py — the overnight solve loop (NOTES.md §8), the glue over the pieces
already built. Iterates an AOI's question bank:

  answerable_now + gold-chain -> mint gold (goldmint.sh, tested connectors)
      --live: also run_solver.sh -> detect_struggle -> judge vs gold -> ledger
      --dry-run: gold + ledger only (no LLM; fast, for testing the control flow)
  answerable_now, no chain (fire/greenness need an input point set) -> needs_input queue
  needs_connector / breaker (NETWORK/PATTERN) -> connector_demand queue (frontier writes it)

Every Solver call is timeout-bounded (run_solver.sh), so the loop cannot hang.
Controller escalation + Miner re-mine run as hooks. Stops on --budget-seconds or
--max-questions or an exhausted bank.

  python3 driver.py --aoi aois/elephants_by_the_lake.json --dry-run --max-questions 4
  python3 driver.py --aoi aois/elephants_by_the_lake.json --live --budget-seconds 57600
"""
import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "components"))
import controller, miner  # noqa: E402


def _sh(cmd, timeout):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def mint_gold(chain, bbox, timeout=420):
    rc, out, err = _sh(["bash", os.path.join(HERE, "goldmint.sh"),
                        "--species", chain["species"], "--bbox", ",".join(map(str, bbox)),
                        "--annotate", chain["annotate"], "--group", chain["group"]], timeout)
    try:
        return json.loads(out[out.index("{"):out.rindex("}") + 1])
    except (ValueError, json.JSONDecodeError):
        return {"error": "goldmint failed", "rc": rc, "stderr": err[-300:]}


def solve_and_judge(question, gold, run_id, timeout=1300):
    """Live mode: run the Solver, detect struggle, judge against gold (heuristic)."""
    env = {**os.environ, "RUN_ID": run_id, "SOLVER_TIMEOUT": str(timeout - 60)}
    p = subprocess.run(["bash", os.path.join(HERE, "run_solver.sh"), question],
                       capture_output=True, text=True, timeout=timeout, env=env)
    verdict = p.stdout.rsplit("STRUGGLED=", 1)[-1].split()[0] if "STRUGGLED=" in p.stdout else "unknown"
    log = os.path.join(HERE, "runs", f"{run_id}.log")
    text = open(log, errors="ignore").read().lower() if os.path.exists(log) else p.stdout.lower()
    res = gold.get("result", {})
    plan_match = all(c in text for c in ("occurrence", gold.get("annotate", "")))
    keys = [str(k).lower() for k in (res.keys() if isinstance(res, dict) else [])]
    hit = sum(1 for k in keys if k and k in text)
    number_match = bool(keys) and hit / len(keys) >= 0.5
    return {"struggled": verdict, "plan_match": plan_match, "number_match": number_match,
            "solver_evidence_hits": f"{hit}/{len(keys)}"}


def drive(aoi_path, mode, budget_s, max_q, mine_every=3):
    aoi = json.load(open(aoi_path))
    bbox = [float(x) for x in aoi["bbox"]]
    outdir = os.path.join(HERE, "aois", aoi["name"])
    bank = controller.load_bank(os.path.join(outdir, "questions.jsonl"))
    ledger_path = os.path.join(HERE, "ledger", f"{aoi['name']}_ledger.jsonl")
    solved_bank, queues = [], {"needs_input": [], "connector_demand": []}

    order = sorted(bank, key=lambda q: 0 if q.get("status") == "answerable_now" else 1)
    start, done = time.time(), 0
    for q in order:
        if time.time() - start > budget_s or done >= max_q:
            break
        if q.get("status") == "needs_connector" or q.get("is_breaker"):
            queues["connector_demand"].append(q); continue
        if not q.get("chain"):
            queues["needs_input"].append(q); continue

        gold = mint_gold(q["chain"], bbox)
        entry = {"id": f"{aoi['name']}-{done:03d}", "question": q["question"],
                 "bucket": q["bucket"], "primitive_shape": q["primitive_shape"],
                 "chain": q["chain"], "gold": gold, "mode": mode,
                 "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
        if gold.get("n_points", 0) == 0:
            entry["status"] = "unanswerable_no_data"
        elif mode == "live":
            entry.update(solve_and_judge(q["question"], gold, f"{aoi['name']}_{done:03d}"))
            entry["plan_match"] = entry.get("plan_match"); entry["number_match"] = entry.get("number_match")
        else:
            entry["status"] = "gold_minted (dry-run, no solve)"
        controller.append_bank(ledger_path, [entry])
        solved_bank.append(entry); done += 1

        if controller.should_escalate(solved_bank):
            entry["escalation_signal"] = "pass-rate>=0.80 -> Proposer should emit a harder batch"
        if done % mine_every == 0:
            miner.mine(os.path.join(HERE, "runs", "*.log"),
                       statedb=os.path.expanduser("~/.hermes/state.db"))

    _report(aoi, mode, solved_bank, queues, budget_s,
            os.path.join(outdir, "driver_report.md"))
    return {"aoi": aoi["name"], "mode": mode, "solved": len(solved_bank),
            "needs_input": len(queues["needs_input"]),
            "connector_demand": len(queues["connector_demand"]), "ledger": ledger_path}


def _report(aoi, mode, solved, queues, budget_s, path):
    L = [f"# Driver run — {aoi['label']} ({mode})\n",
         f"budget {budget_s}s · solved {len(solved)} · needs_input "
         f"{len(queues['needs_input'])} · connector_demand {len(queues['connector_demand'])}\n",
         "## Solved (gold minted from tested connectors)\n"]
    for e in solved:
        g = e["gold"].get("result", e["gold"])
        L.append(f"- **{e['question']}**")
        L.append(f"    - {e['primitive_shape']} | {e['chain']['produce']}.search -> "
                 f"{e['chain']['annotate']} -> {e['chain']['group']}")
        L.append(f"    - gold (n={e['gold'].get('n_points','?')}): `{json.dumps(g)[:200]}`")
        if mode == "live":
            L.append(f"    - solver: struggled={e.get('struggled')} plan_match={e.get('plan_match')} "
                     f"number_match={e.get('number_match')} ({e.get('solver_evidence_hits')})")
    L.append("\n## needs_input (answerable once a point set is supplied)\n")
    for q in queues["needs_input"]:
        L.append(f"- {q['question']} — {q['primitive_shape']} (supply sites/grid points)")
    L.append("\n## connector_demand (frontier writes these — NEW PRIMITIVES this AOI needs)\n")
    for q in queues["connector_demand"]:
        L.append(f"- {q['question']} — {q['primitive_shape']}")
    open(path, "w").write("\n".join(L) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--aoi", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--budget-seconds", type=int, default=57600)   # 16h
    ap.add_argument("--max-questions", type=int, default=1000)
    a = ap.parse_args()
    mode = "live" if a.live else "dry-run"
    r = drive(a.aoi, mode, a.budget_seconds, a.max_questions)
    print(json.dumps(r, indent=2))
