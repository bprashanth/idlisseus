# discipline plugin

Puts the benchmark-winning conversational behavior into the **real hermes chat**, natively — so `./chat.sh`
itself is short, honest, and disciplined, with the full hermes UI (tool previews, `/why`, streaming). No
external wrapper, no `--smart-model` dumb shell.

## What it does (two automatic hooks — you type nothing special)
- **`pre_llm_call`** injects a per-turn **STEER** into the user message (where the model actually attends,
  unlike the always-on constitution which qwen ignores):
  - brief (~1 min, no essay); lead with the finding + numbers; 1-3 follow-ups
  - OBSERVED vs MODELLED, "backed by N records"; never present modelled as observed
  - clarify **at most once**, only on a genuinely-vague opener; if the user gave any direction, PROCEED
  - records only via `points.py get` (never raw inaturalist/occurrence with a name); short paper queries
  - **batch independent read-only tool calls** (concurrent → faster)
- **`pre_tool_call`** caps tool calls per turn (`_CAP=12`); past the budget it **blocks further tools** and
  says "answer now as final text" — stops serial runaways and empty truncation.

## Install / update
```
agents/hermes/plugins/discipline/install.sh      # copies into the container + `hermes plugins enable`
```
Edit `__init__.py` and re-run to update (takes effect next session). `_CAP` and the STEER text are the knobs.

## Why it exists (the finding)
The constitution PROSE (short/clarify/compute-fresh) is loaded every turn but qwen122b ignores it. The
benchmark's win came from a per-message nudge + a tool cap that lived only in the test harness. This plugin
moves both into the live chat. Verified on the exact failing case ("tell me about snakes at ebtl" →
serial 16-tool thesis before; short, honest, capped, multi-turn drill-down after).

## Known limits (honest)
- **Clarify is not deterministic** — prose steering makes qwen clarify *sometimes*; a smart-model
  **classifier** (see `benchmarks/place_memory_run/clarify_classifier.py`) is the deterministic route.
- The cap can still cause an occasional empty-then-retry when it fires mid-thought (mitigated by `_CAP=12`
  + a strict "next message MUST be final text" block message).

## Related
- Parallelism is **model-conditional** (this plugin owns it, per-model, via the `model` kwarg): **qwen122b
  → serial** (its batched calls emit an empty tool name → `Unknown tool ''`; isolated test: qwen 2
  empty-name vs deepseek 0); **deepseek/glm → batch** (they batch cleanly, concurrent = faster). SOUL is
  neutral on tool-count — don't put a blanket rule there (it slows every model for one model's bug).
- Benchmark + golden gate: `benchmarks/place_memory_run/`.
