# Concept map — the DSS architecture, captured in the order it was discovered

**Purpose.** This repo grew as a chain of individual benchmarks (Jun 24 → Jul 11, 2026). Each one
discovered a concept that became an architecture piece — but some pieces are wired into the live agent
(`agents/hermes/chat.sh`), some are proven-but-buried in a benchmark dir, and some are offline tools never
integrated. This doc is the **total capture** for a v2 rework: read it in timestamp order to see how the
ideas accreted, then use the concept blocks (Part 2) to rework each piece with full knowledge of its
status, findings, knowns and unknowns.

**STATUS legend** (the load-bearing column for v2):
- 🟢 **LIVE** — wired into the `chat.sh` agent workflow today.
- 🟡 **PARTIAL** — works, but not fully wired or has a known gap.
- 🔵 **BENCH/OFFLINE** — a harness or offline tool; produces evidence, not in the live loop.
- 🔴 **BURIED** — concept proven, NOT integrated; a v2 candidate to resurrect.
- ⚪ **DEMO** — temporary/demo-grade (e.g. a torn-down S3 bucket).

---

## PART 1 — Chronological doc index (how the concepts accreted)

Grouped by discovery date. Each line: doc → the concept it captures. (Excludes venv/asset READMEs.)

### Phase 0 — Agent harness shootout (Jun 24–26) 🔵
- `benchmark1_ds4/REPORT.md` — ds4 (C+CUDA local model) as an agent backend.
- `benchmark2_hermes/{PLAN,PLAN_MODEL,REPORT,CHECKPOINT}.md` — **Hermes token-proxy harness**: inserts a
  tool-call sentinel token to force any OpenAI-compatible model to emit tool calls. The auditable harness.
- `benchmark3_seed_oss/{PLAN,CHECKPOINT}.md` — Seed-OSS as backend.
- `benchmark4_qwen_sidekick/{PLAN,REPORT,CHECKPOINT}.md` + results — qwen3-next-80b sidekick; wildfire
  research task. **Verdict → `agents/index.md`:** Hermes = planful + auditable (`state.db` stores exact
  code); Idlisseus loop = fast + guard-railed. Both hit the same data wall; Hermes's fabrication is
  auditable.

### Phase 1 — Semantic broker origin: question → insight (Jul 2–3) 🔵→🟢
- `semantic_broker/VISION.md` — **the thesis**: boil a conservation question down to a few **building
  blocks / primitive shapes** (FIND→ANNOTATE→GROUP). Connector-vs-function distinction. Two kinds of data
  source. The still-open **functions-vs-richer-cards** question.
- `semantic_broker/NOTES.md` — data buckets, **dataset cards**, the core experiment loop, benchmark Qs.
- `semantic_broker/{PLAN,VISION,DATASETS,EXPERIMENT_v-1,CONNECTORS,CONNECTORS_DESIGN}.md` — the v-1 design.
- **v-1 KEY FINDING:** data-*finding* is NOT the bottleneck at a small corpus; the **analysis / connector-
  execution layer** is (wrong WorldCover class semantics, couldn't finish EE aggregation). → the insights
  layer needs its own scaffolding.

### Phase 2 — Connectors + the self-improving loop (Jul 3–4) 🟢 (connectors) / 🔴 (loop-in-chat)
- `dss/connectors/{fire,landcover,occurrence,protected_areas,terrain,greenness,ecoregion}.md` +
  `PHILOSOPHY.md` — **connector pattern**: points-in/points-out, own legend/band metadata, `--describe`,
  self-heal to venv python. The insights-layer fix for v-1.
- `algebra/NOTES.md` — **the self-improving connector loop** (2h POC → 16h run): Solver → **struggle
  detector** → write+gate a new connector → mint gold → judge → ledger; the **Curriculum Controller**
  (generator pulls ahead), **Session Mining → permanent rules** (memory as rules, not embeddings), the
  **Scout** (data-frontier discovery). This is the intellectual seed of `dss/loop/`.
- `algebra/research/{README,RESEARCH_AUTOLOOP_PLAN,CORPUS_REPORT}.md`, `DRYAD_SETUP.md` — the autonomous
  **crawl**: Zenodo theme search + NCF author-graph + **Dryad (authenticated "login" connector)**. Corpus
  17 → 169 → **256** datasets. `dss/connectors/paper_data.md` (inspect/extract points from datasets).

### Phase 3 — Data cards + retrieval / discovery (Jul 4) 🟢 (just wired)
- `algebra/paper_data_v-1/` — buried-data experiment: metadata search finds titles, misses **buried
  columns**; **verdict: cards needed**.
- `algebra/discovery/` (`build_cards.py`→`dss/loop/`, `retrieval_bench.py`) + `dss/connectors/embedding.md`
  — **content cards** (title + all columns + codebook) + retrieval bench. **VERDICT:** keyword-over-cards
  ≈ embeddings ≈ hybrid (~.91) on literal queries; **one-prompt-LLM-over-cards DEGRADES at scale**
  (17→256 monotonic). Codebook-in-card is the lever.
- **(Jul 11 update)** `benchmarks/discovery_bench/README.md` — on **paraphrased** lay queries embeddings
  clearly beats keyword (recall .58 vs .33, MRR .40 vs .17 at 256 cards). `dss/connectors/discovery.py`
  now wired + named in the constitution.

### Phase 4 — Transfer algebra + DSS convergence (Jul 5) 🟢 (connector) / 🟡 (routing)
- `algebra/TRANSFER_ALGEBRA.md` + `dss/connectors/predict.md`, `MODELLING.md` — **gate → route → 3
  methods**: gate = AlphaEarth NN-analog + WorldClim MESS envelope; `route` classifies the SITUATION
  (answerable / need_more_data / need_better_models); methods = overlap-join / transfer_RF / sdm_climate.
  **Agreement is the signal.** Always label observed-vs-MODELLED.
- `dss/{README,PHILOSOPHY,AOI_ONBOARDING,DATA_STRATEGIES}.md` — first convergence docs: **most AOIs are
  data-starved**; onboarding a new site = run the loop.
- New connectors: `ebird,phenology,indicators,water`.

### Phase 5 — Skill algebra, colocation, invasive map, model×skill (Jul 6) 🟢 / 🔵
- `semantic_broker/SKILL_ALGEBRA.md` — **skill buckets** + the **ground-truth (verify) lens** as a
  cross-cutting layer on OUTPUT. Feeds `/why`.
- `dss/connectors/{geo,s2,groundtruth_lens,inaturalist,points}.md` — **colocation chain** (`geo.cooccur`)
  + the **verify-species rule** (`points.py` is the ONE resolver; common→scientific name).
- `invasive_skill/{README,DATA_AND_KEYS,IMPROVE_ROADMAP}.md` + `experiments/INVASIVE_MAP_BENCHMARK.md` +
  `invasive.py` — **invasive map** = RF + S2 phenology; map-product comparison; **ground-truth substitutes
  ranked**. FINDING: hand-rules fail; **labels are the missing piece**.
- `algebra/bench/{report,model_skill_report,skill_gaps}.md` — **model×skill benchmark** (cost-capped).
  **Verdict: the SKILL is the moat**, not the model.
- `dss/skills/conservation-data-analysis/SKILL.md` + `references/*` — the packaged skill.
- `semantic_broker/SYLLABUS.md` — the 12-Q s2+colocation stress test.

### Phase 6 — Night run + free data funnel (Jul 6–7) 🔵
- `night_run/{NIGHT_PLAN,SUMMARY,report,walkthrough_questions}.md` — 36-Q syllabus, **$ cost cap**, free
  map pipeline. Cost-aware **free data funnel**; imagery-access verdict (SkyFi/EarthCache → **went free**).

### Phase 7 — Live map, determinism, trace introspection, limitations, recipes (Jul 8) ⚪ / 🟢 / 🔵
- `semantic_broker/experiments/EBTL_LIVE_MAP.md` — the **S3 front-end** (deterministic, cached; `/why`
  panels; mobile). ⚪ temporary bucket.
- `dss/connectors/recipes/{spatial-where,transfer-scarcity,colocation,nursery-water-indicators,human-use,
  abundant-bridge}.md` — **progressive-disclosure recipes** (load ONE when the question matches) vs the
  always-on PLAYBOOK constitution. `PLAYBOOK_naked.md` = ablation overlay.
- `agents/hermes/TRACE_INTROSPECTION.md` — **state.db self-improvement**: mine the agent's own transcript
  → failures → rules. The practical Miner engine.
- `semantic_broker/LIMITATIONS.md` — **L1–L6 behavioural failures** (the snakes trace): L1 name-resolve by
  free-association (⚠ highest), L2 spatial-where doesn't route to transfer/map, L3 persists unverified
  facts, L4 bypasses `points` resolver, L5 thoroughness reactive, L6 serial calls. **The v2 hit-list.**
- chat.sh **deterministic model selection** (register local qwen as a provider; pass `-m` per call).

### Phase 8 — Eastern Ghats run: router refactor + litscout + smart/cheap (Jul 9) 🟢 / 🟡
- `eastern_ghats_run/REPORT.md` — **PLAYBOOK→router refactor**. Verdicts: **skill is the moat**; a
  **planner buys nothing** (+33% slower, 0 quality); **tool-discipline is structural**.
- `dss/connectors/litscout.md` — **author co-authorship-graph** paper/dataset discovery (walk people to
  reach archived data a title search misses).
- `eastern_ghats_run/SMART_SPLIT.md` — the **constitution does NOT hold on the cheap model alone**;
  **smart at the EDGES, cheap in the MIDDLE** ("smart bookends, cheap middle" + mechanism control).
- `dss/ARCHITECTURE.md` — the synthesis: **constitution / site-brain / capability library / control-plane
  vs reasoning-plane / improvement-loop**. Has its own "Open questions" list.

### Phase 9 — Place-memory bench (Jul 10) 🔵 → 🟢 (mechanism)
- `place_memory_run/REPORT.md` (+ `conv_bench.py`, `syllabus.json`, `clarify_classifier.py`) — multi-turn
  conversational bench + **golden regression gate**. **FINDING: a cheap MECHANISM (terse nudge + tool cap)
  beats a SMART GATE end-to-end** (the gate over-clarifies + stalls). **Brevity is a mechanism, not a
  model.** The self-improving loop fixed the green-cat-snake regression. Clarify classifier: glm .94.

### Phase 10 — Discipline plugin, model-conditional parallelism, discovery wire, production move (Jul 11) 🟢
- `agents/hermes/MODEL_OPTIONS.md` — qwen (serial — `qwen3_xml` parser emits a phantom empty-name call on
  batches) vs deepseek (batches/parallel) vs glm (clarify classifier). "Don't stack smart models."
- `agents/hermes/plugins/discipline/` + neutral `SOUL.md` — **model-conditional parallelism** + tool-cap +
  brevity steer, as a plugin (not baked into persona).
- `discovery_bench/`, `dss/{corpus,loop}/`, `dss/PRODUCTION_MOVE_CHECKPOINT.md`, `algebra/MASTER_PLAN.md` —
  the **production code move**: connectors + corpus + discovery + the expansion loop out of `benchmarks/`.

---

## PART 2 — Architecture concept blocks (rework units for v2)

Each block = one architecture component. `where` = the authoritative doc/code. `status` = the wiring
reality. Rework these piece by piece.

### A. Agent runtime & harness 🟢
- **What:** Hermes (token-proxy, auditable `state.db`) is the chosen harness; `chat.sh` runs a persistent
  container with deterministic per-call model selection; plugins hook `pre_llm_call`/`pre_tool_call`/
  `transform_llm_output`; SOUL = persona.
- **Where:** `agents/index.md`, `agents/hermes/chat.sh`, `plugins/{discipline,why}`, `SOUL.md`,
  `MODEL_OPTIONS.md`, `TRACE_INTROSPECTION.md`.
- **Knowns:** persistent container = fast; determinism fix (register local qwen). **Unknowns/gaps:**
  token-proxy is brittle under model updates; assembled "bookends" mode exists in chat.sh but is NOT the
  default.

### B. The Constitution 🟢
- **What:** always-on router prose = 7 rules, each with a golden trace (ask-don't-assume, short answers,
  stop-when-enough, **papers-first (discovery-first)**, points-resolver-only, compute-fresh, transfer +
  observed-vs-modelled).
- **Where:** `dss/connectors/PLAYBOOK.md` (constitution + route table). Ablation: `PLAYBOOK_naked.md`.
- **Knowns:** the constitution does NOT hold on the cheap model alone → needs a MECHANISM (Block L).
  A wired connector is invisible until the constitution NAMES it (the rule-4/discovery lesson).
  **Unknowns:** which rules survive on smaller models; PLAYBOOK-bloat vs recipe split calibration.

### C. Site brain (what the agent KNOWS about a place) 🟢 / 🔵
- **What:** "one brain that knows a place" — read the site, never search for what EBTL is. Per-site AOI
  config drives scout/proposer.
- **Where:** `dss/connectors/SITE_EBTL.json` (live) · `benchmarks/algebra/aois/*.json` + `template.json`
  (loop inputs) · `dss/AOI_ONBOARDING.md`.
- **Unknowns:** onboarding a genuinely new AOI end-to-end has only been exercised on EBTL + a few analog
  AOIs; the site-brain ↔ loop handoff for a cold site is under-tested.

### D. Capability library (connectors) 🟢
- **What:** 25 connectors, points-in/points-out, own metadata, self-heal to venv, `--describe`; recipes
  loaded on demand (progressive disclosure).
- **Where:** `dss/connectors/*.py` + `*.md` + `recipes/*` + `PHILOSOPHY.md`.
- **Knowns:** works; recipes beat a fat PLAYBOOK. **Unknowns:** no automated connector self-test gate in
  the live path (the NOTES.md struggle-detector→write-connector loop is offline).

### E. Points resolver & name resolution 🟢 (but L1/L4 open)
- **What:** `points.py get` is the ONE resolver (merges GBIF/iNat/paper, common→scientific, dedupe, cache).
- **Where:** `dss/connectors/points.md`; verify-species rule in PLAYBOOK.
- **Unknowns (from LIMITATIONS):** L1 name resolved by free-association not verification (⚠); L4 agent
  sometimes bypasses the resolver. **Top v2 correctness fix.**

### F. Transfer algebra (scarce data → honest answer) 🟡
- **What:** gate (AlphaEarth NN-analog + WorldClim MESS) → `route` (situation classifier) → overlap /
  transfer_RF / sdm_climate; agreement = signal; observed-vs-MODELLED labelling.
- **Where:** `algebra/TRANSFER_ALGEBRA.md`, `dss/connectors/{predict,MODELLING}.md`.
- **Knowns:** gate is cheap (numpy), RF only after gate opens. **Gaps:** L2 — spatial "where can I find X"
  does NOT reliably route into this pipeline; embedding gate not folded into presence; IDW `interpolate`
  unbuilt; RF trained on-the-fly every call (perf — wants a covariate cache + sklearn fast-path).

### G. Discovery / retrieval (cards + embeddings) 🟢 (newly wired)
- **What:** semantic retrieval over content cards (title+columns+codebook) via bge-small; the semantic map
  ("weed in coffee"→"coffee invasion") keyword misses; feed DOIs to `paper_data.extract`.
- **Where:** `dss/connectors/discovery.py`, `dss/corpus/` (cards/catalog/points index), `discovery_bench/`.
- **Knowns:** emb > keyword on paraphrased queries, robust 169→256; codebook-in-card is the lever;
  one-prompt-LLM degrades at scale. **Unknowns:** hybrid (emb→LLM re-rank) not wired into the connector;
  the **functions-vs-cards** question from VISION.md is still open.

### H. The expansion loop (how the DSS grows) 🔵 / 🔴
- **What:** crawl sources → build cards → propose a syllabus scored by a rubric → mine traces into playbook
  rules. Scout (verify data frontier + flag phantoms) · Proposer · Controller · Miner.
- **Where:** `dss/loop/` (+ `README.md`), seed thinking in `algebra/NOTES.md`,
  `RESEARCH_AUTOLOOP_PLAN.md`.
- **Status reality:** runs as an **offline bootstrap** (`loop.py --aoi …`); it is **NOT wired into the live
  chat.sh workflow**. The Miner→rules and struggle-detector→write-connector feedback are **manual**. This
  is the biggest 🔴 for v2: close the loop so the running agent improves itself.

### I. Skill algebra & the packaged skill 🟢
- **What:** skill buckets + the ground-truth verify lens (cross-cutting, on OUTPUT); packaged as a loadable
  skill.
- **Where:** `semantic_broker/SKILL_ALGEBRA.md`, `dss/skills/conservation-data-analysis/`.
- **Known:** **skill is the moat** (model×skill bench). **Unknown:** skill/recipe/constitution boundaries
  overlap — v2 should define one taxonomy.

### J. Invasive map 🟢 (connector) / 🔴 (reliability)
- **What:** `invasive.py` = RF + S2 phenology likelihood map + field waypoints.
- **Where:** `invasive_skill/`, `experiments/INVASIVE_MAP_BENCHMARK.md`, `references/invasive-mapping-guide`.
- **Finding:** hand-rules fail; **labels are the missing piece**; ground-truth substitutes ranked (iNat,
  Vantor 35cm). Reliability benchmark is 🔵 evidence, not a gate.

### K. Front-end / live map ⚪
- **What:** single self-contained HTML (S2 overview → 35cm detail crossfade; `/why` panels; deep-links),
  deployed to a public S3 bucket for demos.
- **Where:** `experiments/EBTL_LIVE_MAP.md`, `agents/hermes/gt/`, mapserver on :8000.
- **Status:** demo-grade; the bucket is torn down after use (exposes coords). v2: a real hosting story.

### L. Model positioning (control plane vs reasoning plane) 🟡
- **What:** smart at the EDGES (clarify-gate + synthesizer), cheap in the MIDDLE (connector runner);
  model-conditional parallelism; clarify classifier; "a mechanism beats a smart gate."
- **Where:** `dss/ARCHITECTURE.md §4`, `SMART_SPLIT.md`, `MODEL_OPTIONS.md`, `plugins/discipline/`,
  `place_memory_run/` (clarify_classifier, the mechanism-wins finding), chat.sh assembled mode.
- **Knowns:** cheap MECHANISM (terse nudge + tool cap) > smart gate end-to-end; planner buys nothing.
  **Gaps:** assembled bookends mode is built but not default; clarify classifier (glm .94) built but NOT
  integrated into the live path.

### M. Trace introspection & self-improvement 🟡 / 🔴
- **What:** `state.db` = full transcript = the audit + improvement surface; golden regression gate catches
  behavioural regressions.
- **Where:** `TRACE_INTROSPECTION.md`, `place_memory_run/conv_bench.py golden`, the Miner (Block H).
- **Status:** introspection is manual; the **golden gate re-checks stored results, it does not re-run** —
  v2 needs a live regression gate + an auto Miner tick.

### N. Evaluation harnesses (the evidence base) 🔵
- **What:** the benchmark scripts that produced every verdict above.
- **Where:** `algebra/bench/model_skill_bench.py`, `place_memory_run/conv_bench.py`,
  `discovery_bench/bench.py`, `eastern_ghats_run/{eg_bench,mt_bench,assembled,plan_compare}.py`.
- **Use for v2:** these are the regression suite. Consolidate into one runnable eval harness.

---

## PART 3 — Findings ledger & open unknowns (the verdicts to preserve)

**Settled findings (don't re-litigate):**
1. Data-finding is not the bottleneck at small corpus; the **analysis/execution layer** is. (v-1)
2. **Codebook-in-card** is the retrieval lever; **one-prompt-LLM-over-cards degrades at scale**; use
   embeddings (+ optional LLM re-rank), keyword as cheap fallback. (Phase 3)
3. **Embeddings > keyword on paraphrased lay queries**, robust across 169→256 cards. (discovery_bench)
4. Transfer: **agreement between methods is the signal**; always label observed-vs-modelled; respect a
   gate REFUSE. (Phase 4)
5. **The skill is the moat**, not the model; **a planner buys nothing** (+33% time, 0 quality);
   **tool-discipline is structural.** (eastern_ghats)
6. The **constitution does not hold on the cheap model alone**; a **cheap MECHANISM (terse nudge + tool
   cap) beats a smart gate** end-to-end; **brevity is a mechanism, not a model.** (place_memory)
7. **A wired connector is invisible until the constitution names it.** (discovery rule-4 lesson)
8. qwen batches break (`qwen3_xml` phantom empty tool call) → parallelism must be **model-conditional**.
9. Invasive map: **hand-rules fail; labels are the missing piece.**

**Open unknowns (v2 must resolve):**
- The **functions-vs-richer-cards** question (VISION.md §open) — never settled.
- **L1–L6** behavioural limitations (LIMITATIONS.md) — esp. L1 name-verify and L2 where→transfer routing.
- Close the **self-improvement loop** into the live agent (Block H/M) — today it's offline/manual.
- **Perf**: RF/covariate caching + sklearn fast-path so transfer isn't an EE round-trip every call.
- **Cold-AOI onboarding** end-to-end (Block C) — only EBTL is battle-tested.
- Integrate the **clarify classifier** + **assembled bookends** into the default path, or discard them.
- One **taxonomy** for constitution vs recipe vs skill (they overlap today).

---

*Living pointers: `benchmarks/algebra/MASTER_PLAN.md` (north star + history), `dss/ARCHITECTURE.md` (the
synthesis + its own open questions), `dss/PRODUCTION_MOVE_CHECKPOINT.md` (the current move). Update this map
when a 🔴/🟡 becomes 🟢.*
