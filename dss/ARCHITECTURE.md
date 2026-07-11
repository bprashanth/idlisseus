# DSS architecture — how it all fits together (first outline)

**Status: a working sketch, not final.** It will be refined at the end of the MASTER_PLAN via a doc-by-doc
review. The point now is one shared mental model so we stop losing behaviors between iterations.

## The frame: one brain that knows a place
A DSS instance is a persistent agent **bound to one site** (a 100+ acre AOI). It **knows** the place, it
**grows** with use, and it is **honest** about what is observed vs modelled. Everything below serves that.

```
        ┌──────────────────────────  CONSTITUTION  ──────────────────────────┐
        │  tiny, always-on, TESTED invariants — never thinned                 │
        └─────────────────────────────────────────────────────────────────────┘
   CONTROL PLANE  (cheap / mechanical)        REASONING PLANE  (capable model)
   classify → clarify-or-proceed → enforce    run connectors → synthesize SHORT answer
        │  budget & length & ask-when-unsure         │  transfer/gate, points, lit, maps
        └───────────────┬──────────────┬─────────────┘
                        ▼              ▼
                 ┌───  SITE BRAIN  ───┐   ┌──  CAPABILITY LIBRARY  ──┐
                 │ FACTS (what it IS) │   │ connectors · recipes ·   │
                 │ LEDGER (what it's  │   │ ALGEBRA ops · transfer   │
                 │   DONE, time-order)│   │ gates · groundtruth lens │
                 └────────────────────┘   └──────────────────────────┘
                        ▲ improvement loop ▼
        scout/litscout (find data) → bench+GOLDEN traces (measure+guard) → miner (propose fixes)
```

## 1. Constitution — the invariants (what must ALWAYS be true)
A small, protected, always-loaded block. Each rule is pinned to a **golden-trace test** so a refactor can't
silently drop it (that is exactly how we kept regressing — answer-style, transfer, "knows the site").
- **Know the site** — never search for what EBTL is; it's ground truth (see FACTS).
- **Short answers, quick turns** — ~1 min, no thesis. Lead with the finding; details on request.
- **Ask, don't assume** — vague question → ask *which species / what scope*, and **"what are you trying to
  understand?"** (the goal drives which model to run — not "run everything").
- **Offer the right next step** — 1–3 concrete follow-ups (incl. data-based options the user may not know
  exist) — suggested, never forced, never fabricated.
- **Resolve names first**, **papers-first** for literature.
- **Transfer even when points are outside** the AOI — map distributions into the region via a model, and
  **always flag it as a modelled transpose + push for field data to corroborate**.
- **Observed vs modelled is always labelled.**

Enforcement is layered (see §7): prose states it, **golden tests catch regressions**, **runtime hooks
enforce mechanically** (budget/length/clarify). Prose alone is necessary but not sufficient — models ignore it.

## 2. Site brain — what the agent KNOWS about the place
Two always-loaded parts (this fixes "had to search for EBTL" and makes the system cumulative):
- **FACTS** (`connectors/SITE_<name>.json`, already exists for EBTL): identity, `site_bbox`, the donor belt
  bbox, known points inside AND outside, ecoregion, protected status, hotspot ids. Authoritative, small,
  never re-derived.
- **LEDGER** (new): a **time-ordered log of events/actions** at this site — *not* memorized facts.
  Append-only entries like `{ts, question, connectors_run, transfer(kind, gate_verdict), points_found,
  data_gaps_flagged, artifact}`. Each turn loads the **recent tail + a rolling summary**; when it grows,
  **chunk it** (summarize older chunks, keep pointers). This is memory-as-history: "we transferred 29
  Lantana records via RF, flagged missing field GPS" is recalled, not recomputed. Distinct from Hermes
  per-user memory (durable prefs) — the ledger is per-SITE work history.

## 3. Capability library — what the agent can DO
- **Connectors** — deterministic points-in/points-out tools (`points`, `litscout`, `paper_data`, `s2`,
  `predict`, `invasive`, `groundtruth_lens`, `indicators`, `water`, …). The hands.
- **Algebra** — the operation taxonomy every question maps to: **STATE / RELATION / CHANGE / TREND / VALUE**,
  with **TRANSFER** cross-cutting and **GROUND-TRUTH (verify)** as an output layer
  (`semantic_broker/SKILL_ALGEBRA.md`, `algebra/TRANSFER_ALGEBRA.md`).
- **Transfer & gates** — SDM, RF, stay-green phenology are the modelled-transfer techniques; the **gate**
  decides `answerable / need-more-data / need-better-models` and the answer always says "modelled, corroborate."
- **Recipes** — on-demand HOW-TO per question type (`connectors/recipes/*.md`), loaded only when routed.
- **Indicators** — for change/health questions: use satellite AND name the bioindicators + prompt to
  survey/acquire them. Communities/settlements: answer from map/landcover data, flag if modelled.

## 4. Control plane vs reasoning plane
Splitting these is the fix for our regressions — not a "smart planner over a dumb runner" (that only added
latency in the bench, +33% for 0 quality, because the failures are discipline/state, not planning).
- **Control plane** (cheap model + code/hooks): classify the theme → **clarify-or-proceed** (ask when the
  species/scope/goal is unclear) → **enforce** turn budget, answer length, and "modelled" flags.
- **Reasoning plane** (capable model): run the connectors and **synthesize the short answer**. The only place
  a smarter model clearly earns its cost (e.g. literature synthesis).
- Which tasks go to smart vs cheap is an **open experiment** (the "top-3 uses" test) — the split above is the
  hypothesis, not settled.

## 5. Improvement loop — getting better WITHOUT regressing
- **Syllabus / curriculum** (`algebra/components/controller.py`, run syllabi): realistic, **multi-turn**,
  neutrally generated (larger model generated) question sets.
- **Bench + GOLDEN traces**: run the syllabus; a fixed **golden subset carries behavioral ASSERTIONS**
  (site-known, short, offered-follow-up, did-transfer, asked-when-ambiguous, flagged-modelled). Run after
  every change — a failed assertion is a caught regression. (Substrate: `eg_bench.py` + `state.db` mining.)
- **Miner** (`algebra/components/miner.py`, `agents/hermes/TRACE_INTROSPECTION.md`): mine traces → propose
  constitution/recipe/connector edits, **human-gated** (auto-writes have poisoned skills before).
- **Scout / litscout** (`components/scout.py`, `connectors/litscout.py`): push the data frontier (new
  sources, author co-authorship graph → datasets → points) → feed the site brain's FACTS.
- Loop: scout finds data → connectors use it → bench measures → golden guards → miner proposes → ledger records.

## 6. How skills/context load - avoiding PLAYBOOK bloat
The load ladder — **small index always, detail on demand** (the progressive-disclosure principle):
1. **Constitution + Site brain** (always, tiny): invariants + FACTS + ledger tail/summary.
2. **Router** (`connectors/PLAYBOOK.md`, ~45 ln, always): question-type → recipe table + universal how-to.
3. **Recipe** (`recipes/<x>.md`, on trigger): the detailed workflow for that question type.
4. **Connector `--describe`** (on use): exact flags/legends.
Skills (Hermes Agent-Skills): only `name`+`description` sit in the always-on index; the body/references load
via `skill_view` when matched. **Invariants are the exception — always-on and tested; everything else is
disclosed on demand.** That split is what prevents bloat AND regression at the same time.

## 7. How the constitution is actually enforce
1. **Prose** — the always-on invariant block (necessary, not sufficient; models drift).
2. **Golden-trace tests** — assertions over `state.db` traces catch a regression *after* a change but
   *before* it ships (the guardrail we lacked).
3. **Runtime hooks** — a Hermes plugin/hook that enforces *mechanically* at run time: a tool-budget cap +
   "wrap up now" injection past N calls, an answer-length target, and a clarify-gate that makes the agent
   ask before assuming. This is where quick-turns / no-thesis / ask-when-unsure actually get *held*, because
   we proved prose can't hold them.

## Status & gaps — what's wired vs what's a v2 job
Each architecture piece has a wiring reality (full status map: `benchmarks/CONCEPT_MAP.md` Part 2). The
gaps below are the v2 work; each is owned by a benchmark spec in `docs/benchmarks/` so it's driven by
evidence against a fixed baseline, guarded by the regression suite (`docs/REGRESSION_SUITE.md`).

| Piece | Status | Gap → benchmark |
|---|---|---|
| Constitution, connectors, points-resolver, discovery, skill | 🟢 wired | guarded by the regression suite |
| **Control plane vs reasoning plane** (§4) | 🟡 assembled mode + clarify-classifier BUILT, not default | `docs/benchmarks/model-positioning.md` |
| **Improvement loop** (§5) — miner + golden gate | 🟡/🔴 offline; golden gate re-checks stored results, doesn't re-run | `docs/benchmarks/improvement-loop.md` |
| **Name-verify (L1/L4) + where→transfer routing (L2)** | 🟡 correctness gaps (`../benchmarks/semantic_broker/LIMITATIONS.md`) | `docs/benchmarks/correctness-routing.md` |
| **Transfer perf** — RF retrains every call | 🟡 no covariate cache / sklearn fast-path | `docs/benchmarks/correctness-routing.md` |
| **Discovery hybrid re-rank + functions-vs-cards** | 🟡 open (VISION.md §open) | `docs/benchmarks/retrieval-onboarding.md` |
| **Ledger** (§2) — the site work-history | 🔴 designed, not built | `docs/benchmarks/improvement-loop.md` |
| **Cold-AOI onboarding** end-to-end | 🟡 only EBTL battle-tested | `docs/benchmarks/retrieval-onboarding.md` |

Still-open DESIGN questions (settle as the benchmarks resolve): ledger schema/chunking/recall; which
control-plane steps are a cheap MODEL vs pure code; the exact clarify-gate; one taxonomy for
constitution-vs-recipe-vs-skill (they overlap today).

See: `docs/README.md` (the heartwood-mirrored reading order) · `HISTORY.md` · `PHILOSOPHY.md` ·
`AOI_ONBOARDING.md` · `DATA_STRATEGIES.md` · `../benchmarks/CONCEPT_MAP.md` ·
`../benchmarks/algebra/MASTER_PLAN.md` · `../benchmarks/semantic_broker/SKILL_ALGEBRA.md` ·
`../agents/hermes/TRACE_INTROSPECTION.md`. General mirror: `../../heartwood/docs/architecture/memory/`.
