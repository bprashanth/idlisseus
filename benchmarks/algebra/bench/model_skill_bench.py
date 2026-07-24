#!/usr/bin/env python3
"""Model × skill benchmark — the overnight ROI experiment.

Runs the SYLLABUS questions through each model (local 122B, GLM-5.2, DeepSeek-V4-Flash) via
agents/hermes/chat.sh, under two skill conditions:
  skilled : the full connectors/PLAYBOOK.md (all the reasoning skills)
  naked   : PLAYBOOK_naked.md overlay (connectors exist, but none of the skills)

The question the matrix answers: does a stronger model still need the PLAYBOOK crutches?
  - GLM-naked ≈ 122B-skilled  -> the SKILL is the moat, low hardware ROI.
  - GLM-naked ≫ 122B-skilled  -> raw model capability wins, hardware ROI is real.

Safe for the single 122B: runs SEQUENTIALLY (never two agent-loops at once). Resumable (skips cells
already in results.jsonl). Hard OpenRouter spend cap. Each answer is scored /why-style (which connectors,
site-scale, grounded, honest) + an optional local-122B rubric score (free).

  python3 bench/model_skill_bench.py run [--cap-usd 12] [--score] [--only 122b,glm] [--skills skilled]
  python3 bench/model_skill_bench.py report
"""
import argparse
import json
import os
import re
import subprocess
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ALGEBRA = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(ALGEBRA))
CHAT = os.path.join(REPO, "agents", "hermes", "chat.sh")
SB = os.path.join(REPO, "benchmarks", "semantic_broker")
NAKED = os.path.join(SB, "connectors", "PLAYBOOK_naked.md")
OUT = os.path.join(HERE, "model_skill_results.jsonl")
REPORT = os.path.join(HERE, "model_skill_report.md")
CREDS = os.path.expanduser("~/.config/idlisseus/openrouter.json")

# model key -> chat.sh --model value ('' = local 122B default)
MODELS = {"122b": "", "glm": "z-ai/glm-5.2", "deepseek": "deepseek/deepseek-v4-flash"}
REMOTE = {"glm", "deepseek"}

# The 12 syllabus questions (SYLLABUS.md has the rubric for each).
QUESTIONS = [
    "is lantana taking over our forest?",
    "what always grows near lantana?",
    "show me where the lantana is on our land",
    "which birds tell me our forest is getting healthier?",
    "where do the birds and the fruiting trees overlap?",
    "what do the elephants here eat?",
    "where do elephants and birds overlap, and what grows there?",
    "what trees do we have and how thick is the canopy across our land?",
    "which native seeds should I collect now, and do those trees grow near us?",
    "which of our ponds dries up first, and what's around it?",
    "is our forest actually coming back?",
    "what data are we missing to answer all this well?",
]
# subset used for the naked ablation (the s2 / colocation / elephant / inventory core)
ABLATION = {0, 1, 2, 5, 7}

CONN_RE = re.compile(r"connectors/([a-z_]+)\.py")
CONN_WORDS = re.compile(r"\b(greenness|landcover|fire|occurrence|terrain|ecoregion|embedding|predict|"
                        r"hyperspectral|protected_areas|geo|ebird|phenology|indicators|water|s2|paper_data)\b")
SPECIES_RE = re.compile(r"\b([A-Z][a-z]+ [a-z]{3,})\b")   # rough Genus species


def _clean(text):
    return "\n".join(l for l in text.splitlines()
                     if not re.search(r"s6-|cont-init|stage2|Syncing|reconcile|supervise|preinit|"
                                      r"applyuidgid|preparing terminal|preparing execute|package:|"
                                      r"\[chat\]", l)).strip()


def or_usage():
    """Current total USD spent on the OpenRouter key (None if unreadable)."""
    try:
        key = json.load(open(CREDS))["api_key"]
        req = urllib.request.Request("https://openrouter.ai/api/v1/key",
                                     headers={"Authorization": f"Bearer {key}"})
        d = json.load(urllib.request.urlopen(req, timeout=20))["data"]
        return float(d.get("usage", 0.0))
    except Exception as e:
        print(f"  [warn] cannot read OpenRouter usage: {e}")
        return None


WHY_LEDGER = os.path.expanduser("~/.hermes/work/.why_ledger.json")


def _read_why():
    """The /why ledger the plugin persisted for the run that just finished (resets per user turn).
    The work dir is uid-10000 → read via sudo."""
    try:
        out = subprocess.run(["sudo", "cat", WHY_LEDGER], capture_output=True, text=True, timeout=20).stdout
        return json.loads(out) if out.strip() else []
    except Exception:
        return []


def run_cell(model_key, q, skill, timeout=1500):
    """One agent run (auto-approved --yolo). Returns the scored record + full transcript + /why ledger."""
    env = dict(os.environ)
    env["MODEL"] = MODELS[model_key]
    env["AUTO_APPROVE"] = "1"                       # --yolo: no manual approval gate (else non-interactive deny)
    if skill == "naked":
        env["PLAYBOOK_OVERRIDE"] = NAKED
    t = time.time(); timed_out = False
    try:
        p = subprocess.run(["bash", CHAT, q], capture_output=True, text=True, timeout=timeout, env=env)
        log = p.stdout or ""
    except subprocess.TimeoutExpired as e:
        timed_out = True
        log = (e.stdout if isinstance(e.stdout, str) else (e.stdout or b"").decode("utf-8", "ignore")) or ""
        log += f"\n[TIMED OUT after {timeout}s]"
    finally:
        subprocess.run("docker ps -q --filter ancestor=hermes-agent-local | xargs -r docker rm -f",
                       shell=True, capture_output=True)
    why_ledger = _read_why()
    ans = _clean(log)
    conns = sorted(set(CONN_RE.findall(log)) | set(CONN_WORDS.findall(ans.lower())))
    a_l = ans.lower()
    flags = {
        "grounded": bool(conns),
        "used_s2": "s2" in conns or bool(re.search(r"ndvi|canopy density|stay.?green|sentinel", a_l)),
        "used_colocation": "geo" in conns or bool(re.search(r"cooccur|co-occur|within .*km|nearest", a_l)),
        "mentions_site": bool(re.search(r"\bsite\b|ebtl|70.?acre|2\.9 ?km|your land|restoration site", a_l)),
        "mentions_corridor": "corridor" in a_l,
        "named_species": len(set(SPECIES_RE.findall(ans))),
        "verify_language": bool(re.search(r"recorded (here|locally|at|near)|confirmed|not verified|"
                                          r"from (my )?knowledge|would you like me to check", a_l)),
        "honest_caveat": bool(re.search(r"modelled|proxy|not observed|would need|data gap|send me|"
                                        r"collect|no baseline|likelihood|not a species id", a_l)),
        "refused": bool(re.search(r"^(i can'?t|i cannot|unable to|i don'?t have)", a_l)) and not conns,
        "blocked": bool(re.search(r"BLOCKED|User denied|denying command|Timeout —", log)),
        "errored": bool(re.search(r"Traceback \(most recent call last\)", log)),
    }
    return {"answer": ans[-16000:], "connectors": conns, "secs": round(time.time() - t),
            "timed_out": timed_out, "flags": flags, "why_ledger": why_ledger}


def score_llm(q, ans):
    """Optional free rubric score via local 122B (0-3 each). Best-effort JSON."""
    prompt = (f"Score this answer to a field conservation worker's question, 0-3 each. "
              f"Q: {q}\nANSWER: {ans[:2500]}\n"
              "Output ONLY JSON: {\"grounded\":0-3,\"site_specific\":0-3,\"honest\":0-3,"
              "\"actionable\":0-3,\"why\":\"...\"}. grounded=uses real named data not memory; "
              "site_specific=about the ~70-acre site not a vague region; honest=labels proxies/"
              "modelled, no fabricated specifics; actionable=Varun can act on it.")
    try:
        body = json.dumps({"model": "qwen", "messages": [{"role": "user", "content": prompt}],
                           "max_tokens": 400, "temperature": 0,
                           "chat_template_kwargs": {"enable_thinking": False}}).encode()
        req = urllib.request.Request("http://172.17.0.1:8001/v1/chat/completions", body,
                                     {"Content-Type": "application/json"})
        txt = json.loads(urllib.request.urlopen(req, timeout=120).read())["choices"][0]["message"]["content"]
        m = re.search(r"\{.*\}", txt, re.DOTALL)
        return json.loads(m.group(0)) if m else {}
    except Exception as e:
        return {"error": str(e)[:80]}


def done_cells():
    if not os.path.exists(OUT):
        return set()
    return {(r["model"], r["skill"], r["qi"]) for r in (json.loads(l) for l in open(OUT))}


def run(cap_usd, do_score, only, skills):
    models = [m for m in MODELS if (not only or m in only)]
    start_usage = or_usage()
    print(f"OpenRouter usage at start: ${start_usage}  cap +${cap_usd}")
    done = done_cells()
    plan = []
    for skill in skills:
        qis = range(len(QUESTIONS)) if skill == "skilled" else sorted(ABLATION)
        for qi in qis:
            for m in models:
                if (m, skill, qi) not in done:
                    plan.append((m, skill, qi))
    # order: local 122b first each round is fine since sequential; keep remote spend visible
    print(f"{len(plan)} cells to run (resuming; {len(done)} already done)")
    for m, skill, qi in plan:
        if m in REMOTE and start_usage is not None:
            now = or_usage()
            if now is not None and now - start_usage >= cap_usd:
                print(f"*** SPEND CAP HIT (${now - start_usage:.2f} >= ${cap_usd}) — stopping remote runs.")
                if all(x in REMOTE for x, _, _ in plan[plan.index((m, skill, qi)):]):
                    break
                continue
        q = QUESTIONS[qi]
        print(f"\n== [{m}/{skill}] Q{qi}: {q}")
        rec = {"model": m, "model_id": MODELS[m], "skill": skill, "qi": qi, "question": q,
               "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
        rec.update(run_cell(m, q, skill))
        if do_score:
            rec["score"] = score_llm(q, rec["answer"])
        rec["usage_after"] = or_usage() if m in REMOTE else None
        with open(OUT, "a") as f:
            f.write(json.dumps(rec) + "\n")
        s = rec.get("score", {})
        print(f"   {rec['secs']}s conns={rec['connectors']} flags="
              f"{{s2:{rec['flags']['used_s2']},coloc:{rec['flags']['used_colocation']},"
              f"site:{rec['flags']['mentions_site']},honest:{rec['flags']['honest_caveat']}}} "
              f"score={ {k: s.get(k) for k in ('grounded','site_specific','honest','actionable')} if s else '-'}")
        report()
    print(f"\nDONE. OpenRouter total spent this run: "
          f"${(or_usage() or 0) - (start_usage or 0):.3f}")


def report():
    recs = [json.loads(l) for l in open(OUT)] if os.path.exists(OUT) else []
    L = ["# Model × skill benchmark\n", f"{len(recs)} cells run.\n",
         "Scores are local-122B rubric (0-3). Flags from `/why`-style answer mining.\n"]
    # aggregate per (model, skill)
    agg = {}
    for r in recs:
        k = (r["model"], r["skill"])
        a = agg.setdefault(k, {"n": 0, "secs": 0, "s2": 0, "coloc": 0, "site": 0, "honest": 0,
                               "grounded": 0, "timeout": 0, "sc": {"grounded": 0, "site_specific": 0,
                                                                    "honest": 0, "actionable": 0}, "nsc": 0})
        a["n"] += 1; a["secs"] += r["secs"]; a["timeout"] += int(r.get("timed_out", False))
        f = r["flags"]
        a["s2"] += f["used_s2"]; a["coloc"] += f["used_colocation"]; a["site"] += f["mentions_site"]
        a["honest"] += f["honest_caveat"]; a["grounded"] += f["grounded"]
        s = r.get("score") or {}
        if all(isinstance(s.get(x), (int, float)) for x in ("grounded", "site_specific", "honest", "actionable")):
            a["nsc"] += 1
            for x in a["sc"]:
                a["sc"][x] += s[x]
    L.append("| model | skill | n | avg s | grounded | s2 | coloc | site | honest | timeout | rubric g/s/h/a |")
    L.append("|---|---|--:|--:|--:|--:|--:|--:|--:|--:|---|")
    for (m, sk), a in sorted(agg.items()):
        n = a["n"]; sc = a["sc"]; ns = a["nsc"] or 1
        L.append(f"| {m} | {sk} | {n} | {a['secs']//n} | {a['grounded']}/{n} | {a['s2']}/{n} | "
                 f"{a['coloc']}/{n} | {a['site']}/{n} | {a['honest']}/{n} | {a['timeout']} | "
                 f"{sc['grounded']/ns:.1f}/{sc['site_specific']/ns:.1f}/{sc['honest']/ns:.1f}/{sc['actionable']/ns:.1f} |")
    L.append("\n## Per-question answers\n")
    for r in sorted(recs, key=lambda r: (r["qi"], r["skill"], r["model"])):
        s = r.get("score") or {}
        L.append(f"### Q{r['qi']} [{r['model']}/{r['skill']}] — {r['question']}")
        L.append(f"*{r['secs']}s · connectors: {r['connectors']} · "
                 f"score g/s/h/a: {s.get('grounded','-')}/{s.get('site_specific','-')}/"
                 f"{s.get('honest','-')}/{s.get('actionable','-')} · {s.get('why','')[:120]}*")
        L.append(f"\n{r['answer'][:900].strip()}\n")
    open(REPORT, "w").write("\n".join(L) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--cap-usd", type=float, default=12.0)
    r.add_argument("--score", action="store_true")
    r.add_argument("--only", default="", help="comma list of model keys: 122b,glm,deepseek")
    r.add_argument("--skills", default="skilled,naked", help="comma list: skilled,naked")
    sub.add_parser("report")
    a = ap.parse_args()
    if a.cmd == "report":
        report()
    else:
        run(a.cap_usd, a.score, [x for x in a.only.split(",") if x], a.skills.split(","))
