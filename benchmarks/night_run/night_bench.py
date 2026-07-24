#!/usr/bin/env python3
"""Overnight syllabus run: 36 EBTL questions through the persistent Hermes container on DeepSeek-V4
(fallback to local qwen when OpenRouter spend hits the cap). Captures the answer, the /why ledger, the
connectors used, timing, and stuck/error flags. Resumable, checkpoints after every question.

  python3 night_bench.py run [--cap-usd 10]
  python3 night_bench.py report
"""
import argparse
import json
import os
import re
import subprocess
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SYL = os.path.join(HERE, "syllabus.json")
OUT = os.path.join(HERE, "results.jsonl")
REPORT = os.path.join(HERE, "report.md")
LEDGER = os.path.expanduser("~/.hermes/work/.why_ledger.json")
CREDS = os.path.expanduser("~/.config/idlisseus/openrouter.json")
NAME = "hermes-live"
MFLAGS = {"deepseek": ["-m", "deepseek/deepseek-v4-flash", "--provider", "openrouter"], "qwen": []}
CONN_RE = re.compile(r"connectors/([a-z_]+)\.py")
CONN_WORDS = re.compile(r"\b(landcover|fire|terrain|protected_areas|occurrence|inaturalist|points|greenness|"
                        r"ecoregion|embedding|predict|hyperspectral|paper_data|ebird|phenology|indicators|"
                        r"water|s2|geo|invasive|skyfi|groundtruth_lens)\b")


def or_usage():
    try:
        k = json.load(open(CREDS))["api_key"]
        r = urllib.request.Request("https://openrouter.ai/api/v1/key", headers={"Authorization": f"Bearer {k}"})
        return float(json.load(urllib.request.urlopen(r, timeout=20))["data"]["usage"])
    except Exception:
        return None


def read_why():
    try:
        out = subprocess.run(["sudo", "cat", LEDGER], capture_output=True, text=True, timeout=20).stdout
        return json.loads(out) if out.strip() else []
    except Exception:
        return []


def _clean(t):
    return "\n".join(l for l in t.splitlines()
                     if not re.search(r"s6-|cont-init|Syncing|reconcile|supervise|preinit|applyuidgid|"
                                      r"preparing|package:|📖|💻|┊|╭|╰|─|Initializing|Resume this|Session:|"
                                      r"Duration:|Messages:|Query:", l)).strip()


def run_one(q, model, timeout=900):
    t = time.time(); timed_out = False
    try:
        p = subprocess.run(["docker", "exec", NAME, "hermes", "chat"] + MFLAGS[model] + ["--yolo", "-q", q],
                           capture_output=True, text=True, timeout=timeout)
        log = p.stdout or ""
    except subprocess.TimeoutExpired as e:
        timed_out = True
        log = (e.stdout if isinstance(e.stdout, str) else (e.stdout or b"").decode("utf-8", "ignore")) or ""
    ledger = read_why()
    ans = _clean(log)
    conns = sorted(set(CONN_RE.findall(log)) | set(CONN_WORDS.findall(ans.lower())) |
                   {e.get("connector") for e in ledger if e.get("connector") and not e.get("custom")})
    a_l = ans.lower()
    flags = {
        "grounded": bool(conns),
        "used_paper": "paper_data" in conns or "paper" in a_l,
        "used_points_resolver": "points" in conns,
        "offered_followup": bool(re.search(r"would you like|want me to|shall i|should i|i can .*if you|follow", a_l)),
        "honest": bool(re.search(r"no (local )?(data|records)|not enough|would need|modelled|proxy|collect|missing", a_l)),
        "blocked": bool(re.search(r"BLOCKED|denied|denying command|Timeout —", log)),
        "errored": bool(re.search(r"Traceback \(most recent call last\)", log)),
        "stuck": timed_out or bool(re.findall(r"\.py", log)) and len(re.findall(r"\.py", log)) > 25,
    }
    return {"answer": ans[-6000:], "connectors": conns, "secs": round(time.time() - t),
            "timed_out": timed_out, "flags": flags, "why_ledger": ledger}


def done_qs():
    if not os.path.exists(OUT):
        return set()
    return {json.loads(l)["qi"] for l in open(OUT)}


def run(cap_usd):
    syl = json.load(open(SYL))
    baseline = or_usage()
    print(f"OpenRouter baseline ${baseline}  cap +${cap_usd}")
    done = done_qs()
    model = "deepseek"
    for i, q in enumerate(syl):
        if i in done:
            continue
        if model == "deepseek" and baseline is not None:
            u = or_usage()
            if u is not None and u - baseline >= cap_usd:
                model = "qwen"; print(f"*** spend cap hit (${u-baseline:.2f}) — switching to qwen")
        print(f"\n[{i}/{len(syl)}] ({model}) {q}")
        rec = {"qi": i, "question": q, "model": model, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
        rec.update(run_one(q, model, timeout=420))     # 7 min/question so the full run fits the window
        with open(OUT, "a") as f:
            f.write(json.dumps(rec) + "\n")
        fl = rec["flags"]
        print(f"   {rec['secs']}s conns={rec['connectors']} "
              f"paper={fl['used_paper']} followup={fl['offered_followup']} honest={fl['honest']} "
              f"{'STUCK' if fl['stuck'] else ''}{'ERR' if fl['errored'] else ''}")
        report()
    print(f"\nDONE. spent ${(or_usage() or 0) - (baseline or 0):.3f}")


def report():
    recs = [json.loads(l) for l in open(OUT)] if os.path.exists(OUT) else []
    L = [f"# Night run — {len(recs)} questions\n"]
    agg = {"paper": 0, "followup": 0, "honest": 0, "grounded": 0, "stuck": 0, "err": 0, "secs": 0}
    for r in recs:
        f = r["flags"]
        agg["paper"] += f["used_paper"]; agg["followup"] += f["offered_followup"]; agg["honest"] += f["honest"]
        agg["grounded"] += f["grounded"]; agg["stuck"] += f["stuck"]; agg["err"] += f["errored"]; agg["secs"] += r["secs"]
    n = max(len(recs), 1)
    L.append(f"grounded {agg['grounded']}/{n} · used paper_data {agg['paper']}/{n} · offered follow-up "
             f"{agg['followup']}/{n} · honest {agg['honest']}/{n} · stuck {agg['stuck']} · errored {agg['err']} · "
             f"avg {agg['secs']//n}s\n")
    L.append("## Per question\n")
    for r in sorted(recs, key=lambda r: r["qi"]):
        f = r["flags"]
        tags = " ".join(t for t, v in [("STUCK", f["stuck"]), ("ERR", f["errored"]), ("paper", f["used_paper"]),
                                       ("followup", f["offered_followup"])] if v)
        L.append(f"### Q{r['qi']} [{r['model']} {r['secs']}s] {tags}\n**{r['question']}**\n")
        L.append(f"connectors: {r['connectors']}\n")
        L.append(r["answer"][-900:].strip() + "\n")
    open(REPORT, "w").write("\n".join(L))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    rp = sub.add_parser("run"); rp.add_argument("--cap-usd", type=float, default=10.0)
    sub.add_parser("report")
    a = ap.parse_args()
    report() if a.cmd == "report" else run(a.cap_usd)
