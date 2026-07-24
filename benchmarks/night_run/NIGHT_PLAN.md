# Overnight run — plan, state, and wrap-up checklist (2026-07-06 → 07)

**Goal:** run a 36-question EBTL syllabus (nursery / invasives / elephants / birds / water / recovery /
soil / corridor / fire / climate), improve the skill + performance as it runs, keep answers short + honest +
multi-turn, use paper_data + iNaturalist as point sources, ensure /why works, surface odd findings as a
demo hook. User wakes in ~6h and leaves — **must be clean, no corrupt state, checkpointed.**

## Running now
- `night_bench.py run --cap-usd 10` → `results.jsonl` + `report.md`, checkpoints every question.
- Model: **DeepSeek-V4** via the persistent `hermes-live` container; **falls back to local qwen** when
  OpenRouter spend hits +$10 (baseline was ~$4.41). Resumable (skips done questions).
- Persistent infra (leave up): container `hermes-live`, map server tmux `mapserver` (:8000 → agents/hermes/gt).

## Improvements landed this session
- **/why testable standalone**: `agents/hermes/plugins/why/why.sh` prints the last answer's provenance
  (same output as the `/why` command). `/why` capture bug fixed (was a mid-turn reset; now `is_first_turn`).
- **points resolver merges GBIF + iNaturalist + paper_data** (`points.py`) — the single source-of-truth;
  skills call it, never hand-pick sources. Cached per species+bbox.
- **PLAYBOOK ANSWER STYLE**: ~2-min data-backed answer → stop → offer 1–3 concrete follow-ups (multi-turn);
  paper_data first-class for drivers/covariates; cheaper layers before Maxar.
- Colocation sweep is one call (`geo.cooccur --b-species-list`); groundtruth_lens = hollow squares on crisp imagery.

## Overnight loop (each wake cycle)
1. `night_bench.py report` — scan for `STUCK` / `ERR` / low paper-use / no-followup questions.
2. For stuck ones: read the transcript, find the gap → fix a connector / add a source / tighten PLAYBOOK
   (connectors + PLAYBOOK are LIVE-mounted — no restart). May use cursor-agent, may scout for data.
3. Re-run the fixed question (delete its line from results.jsonl → run resumes it).
4. **Checkpoint**: update this file + memory; commit nothing unless asked.

## Odd-findings hook (build toward the demo)
As results come in, note surprising/contradictory data (e.g. a species GBIF says is here but papers say needs
hills we lack; a pond that dries far earlier than neighbours; birds present but no fruiting plants). Collect
these into `walkthrough_questions.md` — a set of provocative questions to walk the EBTL team through.

## ⏰ WRAP-UP CHECKLIST (do at ~5.5h, before user wakes)
- [ ] Stop `night_bench` cleanly (let the current question finish; do NOT kill mid-write).
- [ ] `night_bench.py report` — final report.
- [ ] Verify hermes-live + mapserver still up; `chat.sh --help` works; `why.sh` prints; a map renders.
- [ ] No orphan containers (`docker ps`), no half-written files, git status sane (don't commit).
- [ ] Update NIGHT_PLAN + memory with the summary + the walkthrough questions.
- [ ] Leave a short "what I found / what's ready for the demo" note at the top of report.md.
