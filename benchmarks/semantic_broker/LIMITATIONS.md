# Known limitations to consider (agent behaviour)

A running register of *behavioural* limitations observed in real Hermes sessions — the kind that don't
show up in a connector self-test but do show up when a human asks a real question. Each entry: symptom →
evidence → why it matters (tie to the MASTER_PLAN win-condition: site-specific · data-grounded · **honest,
no fabrication** · actionable) → candidate mitigation. These are *considerations for future work*, not a
committed backlog — brainstorm before building.

How these are found: mine session transcripts from `state.db` (see
[`agents/hermes/TRACE_INTROSPECTION.md`](../../agents/hermes/TRACE_INTROSPECTION.md)). Add an entry
whenever a trace shows the agent being confidently wrong, under-delivering, or bypassing the intended path.

---

## Case study: the "snakes at EBTL" trace (2026-07-08, local qwen, session `20260708_125835_45e282`)
Three turns: *"tell me about snakes at ebtl"* → *"did you check other papers?"* → *"where can i find the
green cat snake?"*. Good instincts (genus-fallback search, honest scarcity framing, thorough paper sweep
once nudged, auto-wrote a reusable skill note) — but it surfaced the limitations below.

### L1 — Common-name → scientific-name is resolved by free association, not verified  ⚠ highest severity
- **Symptom:** the agent labelled **Boiga flaviviridis** as the "Green Cat Snake" and, when asked *where
  can I find the green cat snake*, handed over a confident GPS point (12.731, 78.181) for it.
- **Reality:** Green Cat Snake = **Boiga cyanea** (re-queried: **zero** records at EBTL or region-wide).
  **Boiga flaviviridis = Wall's Cat Snake** — a *different* species. The honest answer was "no green cat
  snake records; we do have a related Wall's cat snake here."
- **Why it matters:** this is a **fabrication-class error** (a judged dimension we must not lose), and it's
  worse than a refusal. The existing PLAYBOOK "verify-species" rule checks that a *scientific* name exists;
  it does **not** verify the **common-name the user actually spoke** maps to that scientific name.
- **Candidate mitigation:** a common-name resolver step — before answering about a named species, resolve
  the spoken name via GBIF/iNaturalist taxonomy to a scientific name + its *accepted* common name, and if
  the user's word doesn't match, say so. `/why` should flag any unresolved/assumed name.

### L2 — Spatial "where can I find X" does not route to the transfer/map pipeline
- **Symptom:** turn 3 ran **zero tools** (`tool_turns` unchanged) and just restated a single earlier GPS
  point. No habitat-suitability model, no `groundtruth_lens` map, no `/why`.
- **Why it matters:** for a data-scarce species, one dot is not "where you can find it" — the **modelled
  map** is the value-add (the same predict → lens → provenance path invasives get). Text-only under-delivers
  exactly where our stack is supposed to beat a context-free CLI.
- **Candidate mitigation:** recognise "where can I find / where does X occur" as a spatial intent → run the
  transfer/route + `groundtruth_lens` (confirmed points + modelled likelihood), honestly labelled MODELLED.

### L3 — The self-curation turn persists unverified facts
- **Symptom:** the background "update the skill library" turn baked the L1 taxonomy error into a durable
  file (`skills/data-science/conservation-data-analysis/references/snake-data-availability-ebtl.md`), which
  will now mislead future sessions.
- **Why it matters:** self-improvement that persists *wrong* facts is negative learning — it compounds.
- **Candidate mitigation:** gate the curation turn — only persist a species/quantitative claim that was
  tool-verified in the session; or re-verify claims on write; or mark unverified claims as such in the file.

### L4 — Direct connector calls bypass the `points` resolver
- **Symptom:** the agent called `inaturalist.py search` directly instead of `points.get(...)`, so it
  skipped the GBIF + paper merge/dedup — its own note admits "GBIF: not checked".
- **Why it matters:** the `points` resolver exists so skills never hand-pick sources (provenance + coverage
  + dedup). Bypassing it silently drops a whole source and the honesty it carries.
- **Candidate mitigation:** make the PLAYBOOK route occurrence through `points.get`; consider deprecating
  direct `inaturalist.py`/`occurrence.py` calls in the skill guidance.

### L5 — Multi-source thoroughness is reactive, not default
- **Symptom:** turn 1 was iNaturalist-only; the agent checked papers **only after** the user asked "did you
  check other papers?".
- **Why it matters:** a "tell me about X" question should sweep the sources it has by default, not wait for
  a nudge — thoroughness is part of beating the context-free baseline.
- **Candidate mitigation:** PLAYBOOK default for open "tell me about X" → iNat/GBIF (via `points`) **and**
  `paper_data` before the first answer.

### L6 — Serial single-item calls (efficiency, minor)
- **Symptom:** 5 separate iNat searches (one per genus) + 7 separate `paper_data.find` (one per keyword),
  ~2 min/turn.
- **Candidate mitigation:** batch (multi-species / multi-keyword) where the connector allows.

---

*Add new cases above this line, newest first. Keep each entry short; link the session id so it can be
re-mined from `state.db`.*
