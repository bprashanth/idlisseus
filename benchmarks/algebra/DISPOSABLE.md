# Disposable-artifact manifest (what to delete if this experiment is a dead end)

If the research broker turns out useless, delete the **regenerable / runtime** items
below. Keep the **methodology**: code, connectors, plans, self-tests, AOI configs.

## Safe to delete (regenerable or runtime-only)
- `research/kb.jsonl` — the index; fully regenerable by re-running `autoloop.py`.
- `research/narratives.jsonl` — hypotheses; regenerable.
- `research/state.json` — checkpoint cursor; runtime only.
- `research/cache/` — scraped papers/datasets scratch; runtime only (also mirrored to
  `s3://idlisseus/cache` when disk is low — delete the bucket too: `aws s3 rb s3://idlisseus --force`).
- `research/*.log`, `runs/*.log`, `runs/*.console` — run logs.
- `aois/*/` output dirs (`sources.json`, `questions.jsonl`, `bootstrap_report.md`,
  `driver_report.md`, `playbook_rules.md`) — regenerable by re-running `loop.py`/`driver.py`.
- `ledger/*_ledger.jsonl`, `ledger/gold_*` — regenerable gold/ledger.
- any `/tmp/*fix*`, `/tmp/*probe*`, `/tmp/lcfix*` scratch dirs.

## KEEP (the actual work — do NOT delete)
- `research/*.py`, `research/README.md`, `research/RESEARCH_AUTOLOOP_PLAN.md`.
- `components/*.py`, `driver.py`, `goldmint.py`, `run_solver.sh`, `run_selftest.sh`,
  `detect_struggle.sh`, `tests/*.py`.
- `../semantic_broker/connectors/*.py` + `*.md` + `selftests/*` (the validated library).
- `aois/*.json` (the AOI configs), `NOTES.md`, `RESULTS_2h.md`, `ONBOARDING.md`,
  `ebtl/DATA_ASSESSMENT.md`, this file.

## External resources created
- S3 bucket **`s3://idlisseus`** — only created if disk went low; holds cache + kb
  mirror. Remove with `aws s3 rb s3://idlisseus --force` if abandoning.
- cursor-agent usage — paid; capped per run via `--max-cursor`.
