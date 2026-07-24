# why — Hermes provenance plugin (`/why`)

A self-contained Hermes plugin. After any answer, **`/why`** shows — client-side, out of the
conversation — **how that answer was derived**: what data was pulled, what the gate decided, what
model ran, and the result. Two purposes:
1. **Provenance for the user** (an NGO field worker): plain-language, dismissable, trustworthy.
2. **Observability for us**: a per-answer decision-trace we can collect across a benchmark syllabus
   to see *why* the agent decided what it did (which method, gate verdicts, scale, connector-vs-custom).

Everything here is **stdlib-only** and depends on nothing in this repo, so it lifts cleanly into a
standalone Hermes-plugins repo (see "Moving it out" below).

## Files
```
why/
├── plugin.yaml    # manifest: name, hooks provided (post_tool_call, pre_llm_call)
├── __init__.py    # register(ctx): wires the 2 hooks + the /why command
├── ledger.py      # the mining (capture + parse) + the render
├── install.sh     # copy into ~/.hermes/plugins/ + enable
└── README.md      # this file
```

## How it works
- **`register(ctx)`** (`__init__.py`) wires three things:
  - hook `post_tool_call` → `ledger.on_tool_call` — captures each tool call into a per-answer ledger.
  - hook `pre_llm_call` → `ledger.on_user_turn` — clears the ledger when a **new user question** arrives
    (so `/why` = the *last* answer).
  - command `/why` → `ledger.render_why` — renders the ledger **client-side** (returns a string; never
    calls the LLM, never enters the transcript).
- The ledger also mirrors to `/opt/data/work/.why_ledger.json` (survives the process → enables an HTML
  view later, and lets us collect traces during benchmarks).

## The mining (what `ledger.py` parses) — the fiddly, important part
Hermes tools are `terminal` calls running our connector CLIs, and `execute_code` for custom work.
Reconstructing provenance means parsing both. Lessons already baked in (each was a real bug):
- **Two invocation styles.** The agent runs connectors as BOTH `python /opt/data/connectors/name.py`
  AND `cd /opt/data/connectors && python name.py`. The capture regex matches both, with a
  **known-connector allowlist** (`_KNOWN`) so `setup.py` etc. don't get captured.
- **Result envelope.** Hermes wraps a terminal result as `{"output": "<stdout>"}` — we unwrap it before
  parsing the connector's CSV/JSON.
- **Record counts** come from CSV rows / `wrote N` / JSON (`n_records`, `n_waterbodies`, …).
- **Custom code** (`execute_code`) is captured coarsely + summarised (`groupby`→"grouped/summarised the
  results"; `ee.Image(...)`→"custom map calculation"), and trivial post-processing is suppressed when
  real data/models are present. This also **surfaces when the agent went off the standard connectors**.
- **Doc-reads** (`--describe`/`--help`) are skipped (not data steps).
- The render **consolidates one line per connector** (keeping the richest capture), so re-runs/dupes
  collapse.

## The render (NGO-plain)
Sections **Data we pulled / Estimates we modelled / Also ran (one-off steps)**, ANSI colour carries
the signal (green = observed, yellow = estimated, red = not enough data — no emoji), percentages not
raw thresholds. Model lines read: `from N records → checks (look-alike %, climate %) → so estimated …`.

## Install / manage (how we run it here)
Source of truth is THIS dir. To (re)install into the running Hermes home:
```
bash install.sh          # copies to ~/.hermes/plugins/why, chowns uid 10000, enables it
```
`~/.hermes` is owned by the Hermes sandbox user (uid 10000), so the script uses `sudo`. Hermes loads
user plugins from `<home>/plugins/` (here `/opt/data/plugins` inside the container = host
`~/.hermes/plugins`). `/why` takes effect on the next session. Debug discovery with
`HERMES_PLUGINS_DEBUG=1`.

## Moving it out to a standalone plugins repo (later)
It's already isolated. To ship independently: put this dir in its own repo and either (a) keep the
"copy into ~/.hermes/plugins" install, or (b) package it with a pip entry point so Hermes auto-discovers:
```toml
[project.entry-points."hermes_agent.plugins"]
why = "why"
```
Nothing in `ledger.py`/`__init__.py` imports from idlisseus — only stdlib — so it lifts as-is. The only
coupling is *content* (it knows our connector names in `_KNOWN` and the predict.py JSON fields); those
are the intended integration surface.

## Known limits / TODO
- **Interactive `/why` needs a real TTY** (the Hermes REPL). Verified: plugin loads, hooks + command
  register, capture fires live, render validated on real payloads. The final keystroke is a human test.
- **HTML side-by-side view** for demos — not built yet (the persisted ledger makes it easy).
- Scale-default (agent sometimes uses the corridor bbox for a site question) is a **skill** issue that
  `/why` now *exposes* but doesn't fix.
- Reference: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/guides/build-a-hermes-plugin.md
