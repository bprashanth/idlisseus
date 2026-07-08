# Overnight run — demo-ready summary (2026-07-07 ~02:00)

**Ran the 36-question EBTL syllabus on DeepSeek-V4 (~$1.1 total — never hit the $10 cap, never fell back to
qwen). `/why` captured on ~34/36. Answers are honest + data-backed + offer follow-ups (the multi-turn feel).**

## What works well (show these tomorrow)
- **Invasives**: "is lantana taking over" / "what grows near lantana" / "where is it" → likelihood map +
  waypoints + honest transfer caveat + concrete follow-ups. Named real associates (Lagerstroemia,
  Vitex altissima). The **ground-truth lens** (`http://localhost:8000/lantana_lens.html`) is the visual hook.
- **Water**: "which ponds dry first" → **6 of 11 waterbodies are ephemeral (~1 month/yr)**, NE pond most
  precarious. Sharp, specific, with the "send me your pond GPS" ask. (Best single demo answer.)
- **Elephants**: diet (bamboo/Grewia), western-corridor activity (16 records 2024–26), people-overlap — each
  with honest bias caveats + the right data ask (camera traps, dung transects).
- **The pattern**: every answer names sources, states its limit, asks for the ONE dataset that sharpens it.

## Known rough edges (fix next, don't demo cold)
- **Nursery species-recommendation is slow** (Q4/6/7/8 "which trees to collect seed / mother trees / natives
  to grow / which survive" hit the 7-min cap). Root cause: the agent exhaustively probes many species even
  with the batch-phenology tool + the ≤5-tool budget hint. **Fix**: a canned nursery recipe — pull a fixed
  drought-tolerant native shortlist, ONE `phenology.py --species-list` call, answer, offer follow-ups.
- Multi-taxa colocation (Q15 birds↔fruiting-trees) also over-researches — same shortlist discipline needed.
- Follow-up offered ~57%, honest-flag ~49% — good, not universal; the budget/style guidance helps but isn't enforced.

## Improvements landed tonight (all live, no restart)
- `/why` capture fixed (mid-turn reset → `is_first_turn`) + testable standalone: `agents/hermes/plugins/why/why.sh`.
- **points resolver merges GBIF + iNaturalist + paper_data**; skills never hand-pick sources.
- **parallel `phenology.py --species-list`** (batch, ~25s for 6 species vs 420s sequential).
- PLAYBOOK: ANSWER STYLE (short → follow-ups → multi-turn), TOOL BUDGET (≤3–5 calls), paper_data-first for drivers.
- Ground-truth lens redesigned: full crisp 35 cm imagery + hollow transfer squares, fits viewport.

## Demo hook
`walkthrough_questions.md` — provocative data-backed questions to open with the EBTL team (ponds ephemeral,
lantana under teak gaps, invasives under-sampled, elephant corridor unprotected).

## Infra (leave running)
- container `hermes-live` (exec: `chat.sh --model qwen122b|deepseekv4|glm5.2`; in-session `/model … --provider openrouter`).
- map server tmux `mapserver` :8000 → `agents/hermes/gt`; view `ssh -L 8000:localhost:8000`.
- Full run detail: `report.md` · per-Q data: `results.jsonl` · plan: `NIGHT_PLAN.md`.
