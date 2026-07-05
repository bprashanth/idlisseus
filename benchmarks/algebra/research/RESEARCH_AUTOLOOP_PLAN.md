# Autonomous research broker — plan (checkpointed)

**Goal.** A loop that builds a general, provenance-tracked corpus + methodology for
answering real land questions — first for **EBTL** and **Anamalai/Nilgiris**, then
anywhere. Given an open question ("is a new invasive showing up?", "are livelihoods
improving?", "how are the nurseries?"), return *some* grounded answer with sources,
or an honest "no data — collect it".

**Method (the iterating cycle).** mine papers → extract indicators/questions →
measure them against real data over time (occurrence-by-year, SoIB trends, MODIS
NDVI/fire, ESA land cover, **AlphaEarth embeddings** for similarity/convergence) →
index to KB with provenance → **snowball** (species/keywords from papers become new
queries) → **hypothesize** (cursor as an independent judge proposes a narrative +
clarifying questions) → try to answer those → repeat. Gaps are recorded as gaps with
a "collect it / write a connector" note, never faked.

## Engines
- **OpenAlex / Zenodo** — literature + datasets (free).
- **GBIF (incl. eBird/iNaturalist), SoIB 2023** — occurrence over time, bird trends.
- **EE connectors** — greenness, fire, landcover, terrain, ecoregion, **embedding**.
- **cursor-agent** — frontier reasoner (extraction, hypothesis, and, on a solver
  failure, writing a connector — gated by a self-test before it can mint gold).
  PAID/quota-limited → capped and fallback-guarded.
- **Hermes + 122B** — the Solver for hard questions (`run_solver.sh`).

## Running it (safe for 10–12h unattended)
```bash
python3 research/autoloop.py --budget-seconds 39600 --max-cursor 60   # ~11h
python3 research/autoloop.py                                          # resume from checkpoint
```
- **Checkpoint:** every paper → `state.json` (+ append-only `kb.jsonl`). **Resumable**:
  re-run and it skips `seen_dois` and continues the queue.
- **Quota:** cursor capped by `--max-cursor`; after the cap or 3 failed calls it falls
  back to the **free heuristic extractor** and keeps going. Got more quota? Edit
  `state.json` (`cursor_calls:0, cursor_dead:false`) and re-run.
- **Disk:** if free < `--disk-min-gb` (10), sync `research/cache` + `kb.jsonl` to
  `s3://idlisseus` and prune local cache (aws cli).
- **Budget:** stops cleanly at the time limit; all state checkpointed.

## Outputs
- `kb.jsonl` — the durable index (indicator → question → paper → real reading/gap → provenance).
- `narratives.jsonl` — hypotheses + clarifying questions (the "why is this happening" thread).
- `state.json` — checkpoint/resume cursor.
- `ask.py` — answer an open question from KB + a live reading, with sources.

## Roadmap the loop's gaps define (what to build next)
- **Per-indicator connectors** so satellite indicators stop sharing one AOI reading:
  `carbon`/biomass, `rainfall` (CHIRPS), `forest_change` (Hansen), `water` (JRC).
- **NETWORK / PATTERN** primitives (elephant corridors / fragmentation).
- **News/partnership question mining** (cursor web step) → land-owner-specific questions.
- Embedding **PCA** + multi-reference averaging; **embedding self-test is gated** already.
- Embedding-based **anomaly / change** detection (cosine drop year-on-year).

## Known open finding to chase (example the loop is meant to resolve)
EBTL is *greening* (NDVI +0.014/yr) yet **diverging** from the Melagiri reference in
embedding space (0.94→0.83). Hypothesis to test: early restoration (shrub/regen) is
structurally unlike mature forest, or the single reference is unstable → try
multi-reference + a mature-forest reference.

## If this experiment proves useless
Everything disposable is listed in `DISPOSABLE.md`; delete per that manifest. The
**code + connectors + this plan** are the keep-set; `kb.jsonl` is regenerable.
