#!/usr/bin/env python3
"""replay — browse the RECORDED answers of an experiment. ZERO tokens, ZERO spend: it only reads the
saved results file, never re-runs a model.

General-purpose over any experiment whose results are a JSONL of rows, each with a QUESTION, one or more
VARIABLE fields (the things compared — e.g. model, skill), an ANSWER, and QUALITY fields (score, which
connectors/data it used, timing). Point it at any such file with --exp.

  python3 bench/replay.py                          # list the questions in the default experiment
  python3 bench/replay.py list                     # same
  python3 bench/replay.py q 1                       # replay question 1: recorded answers for every
                                                    #   model/skill combo, side by side (+ HTML)
  python3 bench/replay.py --exp other/results.jsonl list
  python3 bench/replay.py --exp X --vars model --answer response --question prompt q 3

Defaults target bench/model_skill_results.jsonl (the 122B vs GLM vs DeepSeek × skilled/naked run).
No LLM is ever called. (If a future feature needs generation, it would use the local free 122B — never a
paid model — but replay itself does not.)
"""
import argparse
import html
import json
import os
import re


def clean_answer(t):
    """Display-only: strip Hermes terminal chrome from a recorded answer (no data changed)."""
    lines = []
    for l in str(t).splitlines():
        if re.search(r"Initializing agent|Done: \d+ new|^\s*Query:|preparing (read_file|write_file|"
                     r"run_terminal|execute|terminal)|📖|💻|📝|⚡|┊|╭|╰|─────|✳|Tool call", l):
            continue
        l = re.sub(r"[│╮╯]|─{2,}", "", l).rstrip()
        if l.strip():
            lines.append(l)
    return "\n".join(lines).strip()

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_EXP = os.path.join(HERE, "model_skill_results.jsonl")
Q_FIELDS = ["question", "prompt", "query", "q"]
A_FIELDS = ["answer", "response", "output", "completion"]
KNOWN_VARS = ["model", "skill", "variant", "condition", "system", "arm"]
KNOWN_QUAL = ["score", "connectors", "flags", "secs", "timed_out", "rubric", "judge", "quality"]


def load(path):
    if not os.path.exists(path):
        raise SystemExit(f"no experiment file at {path}")
    return [json.loads(l) for l in open(path) if l.strip()]


def schema(rows, args):
    keys = set().union(*(r.keys() for r in rows))
    qf = args.question or next((f for f in Q_FIELDS if f in keys), None)
    af = args.answer or next((f for f in A_FIELDS if f in keys), None)
    if not qf or not af:
        raise SystemExit(f"could not find question/answer fields in {sorted(keys)}; pass --question/--answer")
    if args.vars:
        varf = [v for v in args.vars.split(",") if v in keys]
    else:
        varf = [v for v in KNOWN_VARS if v in keys]
    qualf = ([q for q in args.qualities.split(",") if q in keys] if args.qualities
             else [q for q in KNOWN_QUAL if q in keys])
    return qf, af, varf, qualf


def questions(rows, qf):
    seen, out = {}, []
    for r in rows:
        q = r.get(qf)
        if q is not None and q not in seen:
            seen[q] = len(out); out.append(q)
    return out


def _combo(r, varf):
    return " / ".join(str(r.get(v, "")) for v in varf) or "(single)"


def _qual_str(r, qualf):
    bits = []
    for q in qualf:
        v = r.get(q)
        if v in (None, "", [], {}):
            continue
        if q == "score" and isinstance(v, dict):
            bits.append("score " + "/".join(str(v.get(k, "-")) for k in ("grounded", "site_specific", "honest", "actionable")))
        elif q == "connectors" and isinstance(v, list):
            bits.append("used: " + (", ".join(v) if v else "none"))
        elif q == "flags" and isinstance(v, dict):
            on = [k for k, val in v.items() if val is True]
            bits.append("flags: " + (", ".join(on) if on else "—"))
        else:
            bits.append(f"{q}={v}")
    return bits


def cmd_list(rows, qf, af, varf, qualf, path):
    qs = questions(rows, qf)
    print(f"experiment: {path}")
    print(f"variables compared: {varf or '(none)'} | qualities: {qualf}")
    print(f"{len(qs)} questions, {len(rows)} recorded answers:\n")
    for i, q in enumerate(qs, 1):
        n = sum(1 for r in rows if r.get(qf) == q)
        print(f"  [{i}] {q}   ({n} answers)")
    print(f"\nreplay one with:  python3 bench/replay.py q <N>   (shows the recorded answers, no re-run)")


def _blocked(ans):
    return bool(re.search(r"BLOCKED|denying command|User denied|Timeout —", str(ans)))


def _why_block(r):
    """Reconstruct a /why from the saved provenance (connectors + flags). The full live /why ledger
    was not saved per cell, so this is the recorded-provenance view, not the rich ANSI /why."""
    src = {"occurrence": "GBIF", "ebird": "eBird", "paper_data": "papers", "s2": "Sentinel-2",
           "invasive": "S2+GBIF modelled", "embedding": "AlphaEarth", "predict": "modelled RF/SDM",
           "landcover": "ESA WorldCover", "greenness": "MODIS/S2", "water": "JRC water",
           "ecoregion": "RESOLVE/WWF", "geo": "spatial join", "phenology": "GBIF phenology",
           "indicators": "GBIF", "terrain": "SRTM", "hyperspectral": "EMIT"}
    conns = r.get("connectors") or []
    lines = [f"• {c} [{src.get(c, c)}]" for c in conns] or ["• (no connectors recorded)"]
    f = r.get("flags") or {}
    on = [k for k, v in f.items() if v is True]
    if on:
        lines.append("• behaviours: " + ", ".join(on))
    return lines


def cmd_q(rows, qf, af, varf, qualf, path, n):
    qs = questions(rows, qf)
    if not (1 <= n <= len(qs)):
        raise SystemExit(f"question {n} out of range (1..{len(qs)})")
    q = qs[n - 1]
    sub = [r for r in rows if r.get(qf) == q]
    print(f"\nQ{n}: {q}\n" + "=" * 70)
    for r in sub:
        warn = "  ⚠ TOOL BLOCKED (approval gate denied a command — see chat)" if _blocked(r.get(af)) else ""
        sc = r.get("score") or {}
        print(f"\n### {_combo(r, varf)}   [{r.get('secs','?')}s]{warn}")
        print("  /why (recorded provenance):")
        for b in _why_block(r):
            print(f"      {b}")
        if sc:
            print(f"      score g/s/h/a: " + "/".join(str(sc.get(k, '-')) for k in ('grounded', 'site_specific', 'honest', 'actionable')))
        print("  chat (saved transcript — last 4000 chars, start may be cut):")
        print("    " + clean_answer(r.get(af, "")).replace("\n", "\n    "))
    out = os.path.join(HERE, f"replay_q{n}.html")
    _html(q, n, sub, varf, qualf, af, out)
    print(f"\n(no tokens spent — recorded answers)   side-by-side -> {out}")


def _why_ledger_html(r):
    """Plain-language /why from the saved live ledger if present, else the recorded connector list."""
    src = {"occurrence": "GBIF species records", "ebird": "eBird", "paper_data": "published papers",
           "s2": "Sentinel-2 satellite", "invasive": "the invasive-map skill (Sentinel-2 + GBIF, modelled)",
           "embedding": "AlphaEarth", "predict": "a model (RF/SDM — estimated, not observed)",
           "landcover": "ESA WorldCover land-cover", "greenness": "greenness trend (MODIS/Sentinel-2)",
           "water": "JRC surface water", "ecoregion": "RESOLVE/WWF ecoregions", "geo": "a spatial join",
           "phenology": "GBIF flowering/fruiting records", "indicators": "GBIF indicator species",
           "terrain": "SRTM elevation", "hyperspectral": "EMIT hyperspectral", "skyfi": "SkyFi/Vantor imagery"}
    led = r.get("why_ledger")
    items = []
    if led:
        for e in led:
            if e.get("custom"):
                items.append("Ran a custom calculation — " + (e.get("summary") or "processed data"))
            else:
                c = e.get("connector", "?")
                what = src.get(c, c)
                extra = e.get("species") or e.get("bbox") or ""
                items.append(f"Pulled {what}" + (f" for {extra}" if extra else "") +
                             (f" ({e.get('sub')})" if e.get("sub") else ""))
    else:
        items = [f"Used {src.get(c, c)}" for c in (r.get("connectors") or [])] or ["No data tools recorded"]
    return "".join(f"<li>{html.escape(x)}</li>" for x in items)


def _badges(r, af):
    b = ""
    if _blocked(r.get(af)):
        b += '<span class="bad">⚠ a command was auto-blocked mid-run</span>'
    if (r.get("flags") or {}).get("errored"):
        b += '<span class="bad">⚠ a script hit an error</span>'
    if r.get("timed_out"):
        b += '<span class="bad">⚠ timed out</span>'
    return b


def _html(q, n, sub, varf, qualf, af, out):
    models, order = {}, []
    for r in sub:
        m = str(r.get("model", "model"))
        if m not in models:
            models[m] = []; order.append(m)
        models[m].append(r)
    radios, labels, panels = "", "", ""
    for ti, m in enumerate(order):
        radios += f'<input type="radio" name="tab" id="t{ti}"{" checked" if ti == 0 else ""}>'
        labels += f'<label for="t{ti}">{html.escape(m)}</label>'
        cards = ""
        for r in models[m]:
            sk = str(r.get("skill", ""))
            sc = r.get("score") or {}
            scline = ("quality (0–3): grounded " + str(sc.get("grounded", "-")) + " · site " +
                      str(sc.get("site_specific", "-")) + " · honest " + str(sc.get("honest", "-")) +
                      " · useful " + str(sc.get("actionable", "-"))) if sc else ""
            cards += (
                f'<div class="card"><div class="ch">{html.escape(sk or "run")} · {r.get("secs","?")}s'
                f' {_badges(r, af)}</div>'
                f'<div class="bubble user">{html.escape(q)}</div>'
                f'<div class="bubble bot">{html.escape(clean_answer(r.get(af, "")))}</div>'
                f'<details class="why"><summary>▸ why — what data &amp; skills it used</summary>'
                f'<ul>{_why_ledger_html(r)}</ul>'
                f'<div class="sc">{html.escape(scline)}</div></details></div>')
        panels += f'<section class="panel">{cards}</section>'
    nth = "".join(f"#t{i}:checked~.panels>.panel:nth-of-type({i+1}){{display:block}}" for i in range(len(order)))
    act = "".join(f"#t{i}:checked~.tabbar label[for=t{i}]{{color:#0969da;border-bottom-color:#fd8c73}}" for i in range(len(order)))
    doc = f"""<style>
body{{font:14px/1.55 system-ui,-apple-system,sans-serif;margin:0;background:#f6f8fa;color:#1f2328}}
h1{{font-size:16px;padding:14px 18px;margin:0;background:#fff;border-bottom:1px solid #d0d7de}}
.tabwrap>input{{display:none}}
.tabbar{{padding:0 12px;background:#fff;border-bottom:1px solid #d0d7de}}
.tabbar label{{display:inline-block;padding:9px 16px;cursor:pointer;font-weight:600;color:#57606a;border-bottom:2px solid transparent}}
.panel{{display:none;padding:14px 18px}}
{nth}
{act}
.card{{max-width:820px;margin:0 auto 22px;background:#fff;border:1px solid #d0d7de;border-radius:10px;overflow:hidden}}
.ch{{background:#f6f8fa;padding:8px 14px;font-weight:700;font-size:13px;border-bottom:1px solid #d0d7de}}
.bubble{{margin:12px 14px;padding:10px 14px;border-radius:12px;white-space:pre-wrap;font-size:13.5px}}
.user{{background:#ddf4ff;border:1px solid #b6e3ff;margin-left:80px}}
.bot{{background:#f6f8fa;border:1px solid #eaeef2;margin-right:40px}}
.why{{margin:0 14px 14px;font-size:13px}} .why summary{{cursor:pointer;color:#0969da;font-weight:600}}
.why ul{{margin:8px 0}} .why .sc{{color:#57606a;font-size:12px;margin-top:6px}}
.bad{{background:#ffebe9;color:#cf222e;border:1px solid #ff818266;border-radius:10px;padding:1px 8px;font-size:11px;font-weight:600;margin-left:8px}}
</style>
<h1>Q{n}: {html.escape(q)}  ·  recorded runs (no re-run, no tokens)</h1>
<div class="tabwrap">{radios}<div class="tabbar">{labels}</div><div class="panels">{panels}</div></div>"""
    open(out, "w").write(doc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs="?", default="list", help="list | q")
    ap.add_argument("n", nargs="?", type=int, help="question number for 'q'")
    ap.add_argument("--exp", default=DEFAULT_EXP)
    ap.add_argument("--question"); ap.add_argument("--answer")
    ap.add_argument("--vars"); ap.add_argument("--qualities")
    a = ap.parse_args()
    rows = load(a.exp)
    qf, af, varf, qualf = schema(rows, a)
    if a.cmd == "q":
        if a.n is None:
            raise SystemExit("usage: replay.py q <N>")
        cmd_q(rows, qf, af, varf, qualf, a.exp, a.n)
    else:
        cmd_list(rows, qf, af, varf, qualf, a.exp)


if __name__ == "__main__":
    main()
