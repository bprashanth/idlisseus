"""Provenance ledger: capture connector calls, render the /why tree.

Hermes tools are `terminal` calls running `python /opt/data/connectors/<name>.py ...`, so we
parse the command + its stdout to reconstruct: what data was pulled, what the gate decided, what
model ran, and the result. Stdlib only. All hooks catch everything and never raise.
"""
import json
import re

# ANSI (colour carries the observed/modelled/gap signal; no emoji)
G, Y, R, DIM, B, X = "\033[32m", "\033[33m", "\033[31m", "\033[2m", "\033[1m", "\033[0m"

_LEDGER = []          # entries for the current answer
_LAST_USER = [None]   # last user message seen (to detect a new question)

_KNOWN = {"landcover", "fire", "terrain", "protected_areas", "occurrence", "greenness",
          "ecoregion", "embedding", "predict", "hyperspectral", "paper_data", "ebird",
          "phenology", "indicators", "water", "geo", "s2", "invasive", "skyfi"}
# catch BOTH `python /opt/data/connectors/name.py` and `cd connectors && python name.py`
_CONN = re.compile(r"(?:connectors/|python3?\s+)([a-z_]+)\.py(?:\s+([a-z_]+))?")
_SPECIES = re.compile(r"--species\s+\"?([^\"]+?)\"?(?:\s+--|\s*$)")
_BBOX = re.compile(r"--bbox\s+([0-9.,\-]+)")
_POINTS = re.compile(r"--(?:points|train)\s+(\S+)")
_LOC = re.compile(r"--loc\s+(\S+)")


def _summarise_code(code):
    """Plain-English guess at what a hand-rolled execute_code step did (heuristic, from the code)."""
    low = (code or "").lower()
    # spatial proximity / co-occurrence: distances between points, "within N km"
    if (re.search(r"haversine|\bradians\b|\bdistance\b|proximity|nearest|within.*km|radius", low)
            and re.search(r"lat|lon|coord", low)) or re.search(r"math\.(sin|cos|asin|atan2|sqrt)", low):
        return "measured how close points are to each other (distances between records; how many fall within a set radius)"
    m = re.search(r"ee\.(?:Image|ImageCollection)\(['\"]([^'\"]+)", code or "")
    if m:
        return "ran a custom satellite-map calculation on " + m.group(1)
    if "ee." in (code or "") or "earthengine" in low:
        return "ran a custom satellite calculation"
    if re.search(r"groupby|value_counts|counter\(|\.agg\(|crosstab|\bcount\b|\.sum\(\)|\.mean\(\)", low):
        return "grouped and counted the results (e.g. tallies per category)"
    if re.search(r"read_csv|open\(|pandas|csv\.|dictreader", low):
        return "read and organised a data file"
    return "a custom calculation (details not auto-detected)"


def _count(out):
    """Best-effort record count from connector stdout (CSV rows / 'wrote N' / JSON)."""
    if not out:
        return None
    lines = [l for l in out.splitlines() if l.strip()]
    if lines and re.search(r"(^id,lat|\blat\b.*\blon\b)", lines[0], re.I):
        return max(0, len(lines) - 1)          # CSV: data rows (minus header)
    m = re.search(r"wrote (\d+)", out)
    if m:
        return int(m.group(1))
    j = _json_in(out)
    if isinstance(j, list):
        return len(j)
    if isinstance(j, dict):
        for k in ("n_records", "n_species", "n_dispersers", "n_points", "n_waterbodies"):
            if j.get(k) is not None:
                return j[k]
    return None


def _json_in(text):
    """Best-effort: pull the first {...} JSON object out of stdout."""
    if not text:
        return None
    i = text.find("{")
    while i != -1:
        depth, j = 0, i
        for j in range(i, len(text)):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[i:j + 1])
                    except Exception:
                        break
        i = text.find("{", i + 1)
    return None


def _unwrap(result):
    out = result if isinstance(result, str) else (str(result) if result else "")
    try:
        env = json.loads(out)
        if isinstance(env, dict) and "output" in env:
            return env["output"]
    except Exception:
        pass
    return out


def on_tool_call(tool_name=None, args=None, result=None, task_id=None, duration_ms=None, **kw):
    try:
        a = args
        if isinstance(a, str):                      # Hermes sometimes passes args as a JSON string
            try:
                a = json.loads(a)
            except Exception:
                a = {"command": a}
        if not isinstance(a, dict):
            a = {}
        cmd = a.get("command") or a.get("cmd") or a.get("input") or a.get("script") or ""
        code = a.get("code") or a.get("source") or ""
        m = _CONN.search(cmd or "")
        if m and m.group(1) not in _KNOWN:
            m = None  # a .py that isn't one of our connectors (e.g. setup.py)
        # CASE B: the agent hand-rolled analysis (execute_code) instead of a connector — capture it
        # coarsely so provenance isn't silently blank (and so we can SEE it bypassed the connectors).
        if not m and (tool_name in ("execute_code", "python", "run_python") or code) and code:
            out = _unwrap(result)
            _LEDGER.append({"connector": "(custom code)", "sub": "", "custom": True,
                            "summary": _summarise_code(code), "n": _count(out), "raw": out[-200:]})
            _persist()
            return
        if not m:
            return
        conn, sub = m.group(1), m.group(2) or ""
        if sub == "describe" or "--describe" in (cmd or "") or "--help" in (cmd or ""):
            return  # doc-reads aren't data steps
        out = result if isinstance(result, str) else (str(result) if result else "")
        # Hermes wraps a terminal result as {"output": "<stdout>"} — unwrap to the real stdout.
        try:
            env = json.loads(out)
            if isinstance(env, dict) and "output" in env:
                out = env["output"]
        except Exception:
            pass
        entry = {"connector": conn, "sub": sub,
                 "species": (_SPECIES.search(cmd) or [None, None])[1] if _SPECIES.search(cmd) else None,
                 "bbox": (_BBOX.search(cmd).group(1) if _BBOX.search(cmd) else None),
                 "points_file": (_POINTS.search(cmd).group(1).split("/")[-1] if _POINTS.search(cmd) else None),
                 "loc": (_LOC.search(cmd).group(1) if _LOC.search(cmd) else None),
                 "json": _json_in(out), "n": _count(out), "raw": out[-400:]}
        _LEDGER.append(entry)
        _persist()
    except Exception:
        pass  # never break the agent


_LEDGER_FILE = "/opt/data/work/.why_ledger.json"


def _persist():
    """Mirror the ledger to a file (survives the process; enables an HTML view + testing)."""
    try:
        json.dump(_LEDGER, open(_LEDGER_FILE, "w"))
    except Exception:
        pass


def why_text(ledger_file=None):
    """Standalone: render the /why for the last recorded answer from the persisted ledger. Same output as
    the /why command, so you can TEST it without a Hermes session: `python ledger.py [ledger.json]`."""
    global _LEDGER_FILE
    if ledger_file:
        _LEDGER_FILE = ledger_file
    _LEDGER.clear()                 # force render_why to read the persisted file
    return render_why()


def on_user_turn(user_message=None, is_first_turn=None, **kw):
    """Reset the ledger only on a genuinely NEW user question. Ignore slash-commands like `/why` itself —
    the REPL runs this hook on all input, and resetting on `/why` would wipe the ledger before rendering it
    (that's why `/why` showed 'No data steps recorded' mid-answer)."""
    try:
        if is_first_turn is True:                 # explicit new-question boundary (most reliable)
            _LEDGER.clear(); _persist(); return
        um = (user_message or "").strip()
        # fallback when is_first_turn isn't provided: reset on a genuinely new, non-slash user message
        if is_first_turn is None and um and not um.startswith("/") and user_message != _LAST_USER[0]:
            _LAST_USER[0] = user_message
            _LEDGER.clear()
            _persist()
    except Exception:
        pass


# ---------- rendering ----------
def _target(e):
    return e.get("species") or (e.get("points_file") or "").replace(".csv", "") or e.get("loc") or "AOI"


def _pct(x):
    return f"{round((x or 0) * 100)}%"


def _render_model(e):
    """route/predict entry -> a plain 'from data -> checks -> so we estimated' tree for an NGO."""
    j = e.get("json") or {}
    gate = j.get("gate", j)
    verdict = gate.get("verdict")
    n = gate.get("n_train")
    analog = gate.get("frac_aoi_analog")
    floor = gate.get("emb_analog_floor") or 0.5
    clim = gate.get("climate_mess_frac_in_envelope")
    methods = j.get("methods") or {}
    phrase = {"overlap": "we have records right at the site",
              "transfer_rf": "likely a fit (estimated from look-alike sites)",
              "sdm_climate": "likely a fit (estimated from climate)",
              "refuse": "not enough similar data to say"}.get(verdict, verdict or "checked")
    col = G if verdict in ("overlap", "transfer_rf") else (Y if verdict == "sdm_climate" else R)
    lines = [f"{col}{_BULLET} {B}{_target(e)}{X}{col} — {phrase}{X}"]
    if n is not None:
        lines.append(f"  {DIM}from {X}  {n} records in the wider region {DIM}(GBIF){X}" + (f" [{e['points_file']}]" if e.get("points_file") else ""))
    if verdict == "refuse":
        lines.append(f"  {DIM}why  {X}  the site is too unlike where we have data — we did NOT guess a number")
    if analog is not None:
        ok = (analog or 0) >= floor
        lines.append(f"  {DIM}check{X}  site resembles those spots by satellite: {_pct(analog)}" +
                     ("  (close enough to copy directly)" if ok else "  (too different to copy directly)"))
    if clim is not None:
        lines.append(f"  {DIM}     {X}  site's climate matches where it grows: {_pct(clim)}" +
                     ("  (safe to estimate from climate)" if (clim or 0) >= 0.8 else "  (outside its climate range)"))
    for mname, mv in methods.items():
        frac = mv.get("modelled_present_fraction", mv.get("modelled_suitable_fraction"))
        acc = mv.get("test_accuracy")
        how = "from climate" if mname == "sdm_climate" else "from look-alike sites"
        lines.append(f"  {DIM}so   {X}  estimated {how}: about {_pct(frac)} of the site would suit it" +
                     (f"  (model reliability {_pct(acc)})" if acc else ""))
    if not methods and j.get("recommendation"):
        lines.append(f"  {DIM}note {X}  {j['recommendation'][:110]}")
    return "\n".join(lines)


_DATA_VERB = {
    "occurrence": ("found", "records"), "ebird": ("found", "bird records"),
    "phenology": ("checked fruiting/flowering", ""), "indicators": ("checked", "indicator species"),
    "water": ("mapped", "water bodies"), "paper_data": ("searched", "papers"),
    "landcover": ("labelled", "points with land cover"), "terrain": ("read terrain (elevation/slope) at", "points"),
    "greenness": ("checked greenness on", "points"), "geo": ("measured distances for", "points"),
    "ecoregion": ("identified the ecoregion", ""),
}
# name the actual data source (shown in brackets) — the NGO wants to know WHERE it came from.
_SOURCE = {
    "occurrence": "GBIF", "ebird": "eBird", "phenology": "GBIF/iNaturalist", "indicators": "GBIF",
    "paper_data": "published papers", "landcover": "ESA WorldCover 10m", "ecoregion": "RESOLVE/WWF",
    "greenness": "MODIS/Sentinel-2", "water": "JRC Global Surface Water", "terrain": "SRTM",
    "s2": "Sentinel-2 10m", "embedding": "AlphaEarth", "predict": "modelled (RF/SDM)",
    "hyperspectral": "EMIT", "invasive": "Sentinel-2 + GBIF (modelled)", "skyfi": "SkyFi/Vantor imagery",
    "protected_areas": "WDPA", "fire": "FIRMS/MODIS",
}
_BULLET = "●"  # ● — a visible dot, not a period


def _value(e):
    """The meaningful RESULT the connector returned, if we can show it."""
    j = e.get("json")
    if e["connector"] == "ecoregion" and isinstance(j, dict) and j.get("ecoregion"):
        return f": {j['ecoregion']}"
    return ""


# connectors whose output is an ESTIMATE/model, not a direct observation → yellow bullet
_MODELLED = {"invasive", "predict", "embedding"}


def _render_data(e):
    """One consolidated, SOURCED line per connector, in plain field language."""
    verb, noun = _DATA_VERB.get(e["connector"], ("used", e["connector"]))
    n = e.get("n")
    tgt = f" of {e['species'] or e['loc']}" if (e.get("species") or e.get("loc")) else ""
    num = f" {n}" if n is not None else ""
    src = _SOURCE.get(e["connector"])
    line = f"{verb}{num} {noun}{tgt}{_value(e)}".replace("  ", " ").replace(" :", ":").strip()
    if src:
        line += f" {DIM}({src}){X}"
    col = Y if e["connector"] in _MODELLED else G      # yellow = estimated/modelled, green = observed
    return f"  {col}{_BULLET}{X} {line}"


def _load_ledger():
    try:
        return json.load(open(_LEDGER_FILE))
    except Exception:
        return []


def render_why(raw_args=""):
    led = _LEDGER if _LEDGER else _load_ledger()   # fall back to the persisted file if in-memory is empty
    if not led:
        return f"{DIM}No data steps recorded for the last answer yet.{X}"
    models = [e for e in led if e["connector"] == "predict"]
    custom = [e for e in led if e.get("custom")]
    data = [e for e in led if e["connector"] != "predict" and not e.get("custom")]
    out = [f"{B}Where this answer came from{X}  {DIM}(you can dismiss this — it isn't part of the chat){X}", ""]
    if data:
        # consolidate: one line per connector, keeping the richest (max n / has species) capture
        best = {}
        for e in data:
            k = (e["connector"], e.get("species") or e.get("loc"))
            cur = best.get(k)
            if cur is None or (e.get("n") or 0) > (cur.get("n") or 0):
                best[k] = e
        out.append(f"{B}Data we pulled{X}")
        for e in best.values():
            out.append(_render_data(e))
        out.append("")
    if models:
        out.append(f"{B}Estimates we modelled{X}")
        for e in models:
            out.append(_render_model(e)); out.append("")
    if custom:
        seen, lines = set(), []
        for e in custom:
            s = e.get("summary", "custom calculation")
            if s in seen:
                continue
            seen.add(s); lines.append(f"  {Y}{_BULLET}{X} {s}" + (f" -> {e['n']} results" if e.get("n") else ""))
        out.append(f"{Y}Also ran (one-off steps, not our standard checked tools){X}")
        out.extend(lines); out.append("")
    out.append(f"{DIM}colour: {G}green{X}{DIM} = we observed it · {Y}yellow{X}{DIM} = we estimated it · "
               f"{R}red{X}{DIM} = not enough data{X}")
    out.append(f"{DIM}Anything in the answer NOT listed above (e.g. general facts, or the typical tree "
               f"species for an area) is the assistant's own knowledge — not measured at your site. "
               f"Ask for a source if it matters.{X}")
    return "\n".join(out)


if __name__ == "__main__":
    import sys, os
    _p = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.hermes/work/.why_ledger.json")
    print(why_text(_p))
