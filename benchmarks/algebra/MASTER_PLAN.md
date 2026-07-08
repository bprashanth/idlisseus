# MASTER PLAN — EBTL conservation data broker

**Read this first. It's the north star + status so we never lose the thread (survives compaction).**

## North star (never lose this)
Deliver something genuinely valuable to the **EBTL / Rainmatter team (Varun)**: answer their
real, on-the-ground conservation questions with **grounded, sourced data**, and *demonstrably
beat what they'd do today* — ask a plain AI CLI (cursor) that has **zero context** about their
site. The core constraint is **DATA SCARCITY**; that's the whole reason we invest in the
connector + paper-data toolings. Every decision is judged by: *does this help us show Varun
something a plain CLI can't?*

## END GOAL — converge into a replicable DSS (the productization)
The EBTL work is the *proving ground*. The real deliverable is a **replicable Decision-Support
System** (`../../dss/`) any new AOI/user can be onboarded into. The final exercise (do this once
usability is proven, NOT before):
1. **Order ALL md files by date** (here in `benchmarks/algebra/`, the relevant ones in
   `benchmarks/semantic_broker/`, and the dss/ docs), walk the timeline **together**, and **distil each
   learning into `dss/` documentation one-by-one** — then **move the assets out of `benchmarks/` into a
   system in `dss/`.**
2. Lay out, as a replicable system: the **infra** (loop / scout / controller / proposer / miner /
   research crawl+KB), the **design principles** (connectors as points-in/points-out with metadata;
   models; the gate/route transfer algebra; provenance/lineage; the login-connector pattern), and the
   **eval frameworks** (head-to-head vs a frontier model; the curriculum that widens data search;
   the CARDS-beat-LLM-search finding; the **experiment-when-unclear** ideology).
3. Capture the **philosophy** (`dss/PHILOSOPHY.md`) + **onboarding/expansion** (`dss/AOI_ONBOARDING.md`,
   incl. the greedy data-search / Scout, WII-corridor lineage, anti-hallucination guards) +
   **strategies** (`dss/DATA_STRATEGIES.md`). Started; keep adding EVERY discovery here so compaction
   never loses it (e.g. the corridor was derived in a PRIOR run by the Scout — don't re-derive/forget).

## CURRENT PHASE (2026-07-05→): prove usability, then converge
- **Now:** validate the connectors discovered overnight (phenology/indicators/water/ebird/bridge) actually
  work in real Hermes sessions **and that lineage/provenance holds** (the `/why` view — see below).
- **Then, toward the end goal (any/all):** more rounds of the **curriculum**, or **expand the curriculum**,
  or **another head-to-head vs a different frontier model**, or **run A itself on a frontier model** — all
  in service of a bigger, honest win margin + a distilled, replicable system.
- **`/why` provenance view — BUILT (2026-07-05).** Hermes **plugin** (no source hack): source in
  `agents/hermes/plugins/why/` (plugin.yaml + __init__.py + ledger.py), installed to `~/.hermes/plugins/why`
  + enabled. `post_tool_call` hook captures connector calls into a per-answer ledger; `pre_llm_call`
  resets on a new user question; **`/why` command renders client-side** (data→gate→model→result, ANSI
  tree, plain language, no emoji, out of the transcript). VERIFIED: plugin loads + registers 2 hooks +
  /why command; render validated standalone (teak: gate refuses look-alike 0.10 → uses climate SDM).
  Interactive `/why` needs a TTY (can't pipe-test) → **USER tests it live: `./chat.sh` (interactive) →
  ask → `/why`.** Also wired the **absence data-request** into every transfer-model output (predict.py
  ABSENCE_ASK). TODO: HTML side-by-side view for demos; turn-scoping refinement.
  Guide: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/guides/build-a-hermes-plugin.md

## The measure of success (THE benchmark)
Head-to-head, on **Varun-style questions**:
- **A = our stack** — Hermes + 12 connectors + real EE/GBIF/**paper** data + the skill.
- **B = plain cursor CLI** — empty workspace, no context (what Varun uses now).
- **Judge on:** site-specificity · data-groundedness · **honesty (no fabrication)** · actionability.
- **WIN CONDITION (2026-07-05 steer):** beating cursor is NOT "cursor refuses / we refuse." A
  refusal is too easy and is NOT a win for either side. The bar is: *we TRIED to answer* — gave
  our **best gated bet** (best transfer that crosses the gate) with honest caveats, and it's more
  site-specific + data-grounded than cursor's context-free attempt. "I'm learning/improving" beats
  "I can't." Push to answer, not to refuse.

## OVERNIGHT DIRECTIVE (2026-07-05, autonomous) — search→build→benchmark→improve, don't stop
**Goal:** (a) seriously impress the EBTL team, (b) produce specific DATA REQUESTS, (c) **beat cursor
(FRONTIER model — NOT clean-122B; 122B baseline is a floor only)**, (d) grow the win margin a LOT by
improving whatever dimension is weakest. **Give cursor the edge; make our stack catch up + overtake.**
- **Questions:** unbiased, realistic, NOT tailored to what we can do — generate via cursor/neutral
  process (`bench/questions.json`). Don't bias toward our strengths.
- **Improve loop:** benchmark → find where A is weak → improve. If birds abundant → follow that research
  & build transfer; if no RF transfer → SDM; if SDM weak → more weather sources; none → GBIF for more
  covariates; if HS points at something AE doesn't → break down PER SATELLITE CHANNEL and explain. Try to
  EXPLAIN gaps yourself; don't just refuse.
- **Research directions to mine (data-grounded, cite):** Krishnagiri AGRICULTURE ↔ ecological change +
  better crops they could grow; **NURSERY angle (STRONG)** — nurseries supply the ecosystem: seeds/
  saplings/phenology shifts over time, market linkages & planning to supply natives, what the Eastern
  Ghats research facility is likely doing; **arachnid indicators** (EBTL already tracks these);
  **birds × indicators × crops** correlations.
- **HARD RULE: NEVER MANUFACTURE DATA.** Explain gaps honestly; surface the serious asks (Pixxel HS,
  bird acoustic hardware, eBird landscape). Roadblocks (paywalls, accounts) → `ebtl/ROADBLOCKS.md` for
  the human to clear tomorrow. **[#1 roadblock: fresh Cursor account for a clean frontier baseline —
  cursor cloud-memory is contaminated; flag `leaked_our_context` per Q meanwhile.]**
- Keep MASTER_PLAN current every cycle (survive compaction). Loop driven by the benchmark monitor
  (re-arm on timeout); build improvements between per-question notifications.

### Overnight loop LOG (newest first)
- **[cycle 9 — /why polish + Gemini + s2 (2026-07-05)]** **/why improved** (agents/hermes/plugins/why,
  documented + install.sh + shiftable): named sources in brackets (GBIF/RESOLVE-WWF/ESA-WorldCover/…),
  shows the actual RESULT value, visible ● bullet, plain-English custom-code explanations (co-occurrence
  = "measured how close points are"), honesty footer flagging INFERRED-vs-measured claims. Fixed capture
  regex (both `connectors/x.py` and `cd connectors && python x.py`) + doc-read skip + consolidation.
  **GEMINI works as Hermes LLM:** `agents/hermes/chat_gemini.sh` renders a Gemini config (OpenAI-compat
  endpoint, key at ~/.config/idlisseus/gemini.json — free-tier AI-Studio key, ~$0). Gotcha: must insert
  api_key into the TOP `model:` block (awk) + chmod 644 the temp config (uid-10000 reads it). Smoke:
  Hermes+Gemini ran occurrence + answered. **`s2` connector BUILT** (Sentinel-2 10m NDVI canopy-density;
  EBTL site = NDVI 0.558, 71% dense). Running: 2 head-to-heads Hermes+qwen vs Hermes+Gemini.
  **Skill items surfaced (TODO):** (a) label inferred-vs-measured claims, (b) USE available data (S2)
  not just suggest it, (c) scale-default guard, (d) promote co-occurrence/proximity into `geo`. Also
  wired **absence data-request** into predict outputs (ABSENCE_ASK).
- **[cycle 8 — SDM methodology + absence-from-paper experiment]** Documented the modelling layer's
  honesty gap in `connectors/MODELLING.md`: absence = **random background pseudo-absence** (weak; RF
  treats presence/bg as classification, sensitive to bg draw + sampling bias). RF-vs-MaxEnt: MaxEnt
  better-suited for presence-only, BUT **background quality matters more** (target-group bg + spatial
  thinning) and EE has no MaxEnt (needs local libs the container lacks). **KEY EXPERIMENT (quick-check
  DONE, viable): TRUE ABSENCE from paper PLOT CENSUSES** — a complete plot list that omits a species =
  real absence at that coord. Found **43 plot-census candidate datasets** in the corpus (mostly wet →
  need dry-Deccan for EBTL). **Planned SDM upgrade order:** (1) target-group bg + spatial thinning,
  (2) `paper_data.absence(species, region)` → feed real absence into predict, (3) MaxEnt/maxnet. This
  is our data moat (a chatbot can't derive absence from plot censuses).
- **[cycle 7 — FINAL RESULT, 18/18 done]** **A beats cursor 16–2 overall (88%); on the CLEAN
  subset (13 Qs where cursor was NOT leaked = fair frontier test) A 11–2 (84%).** Both losses = the
  human-use category (Q11 grazing, Q15 firewood), root-caused + fixed (skill guidance) → expected to
  flip on a clean rerun. **Overnight deliverables:** 3 new data-grounded connectors (phenology,
  indicators, water) — each won its target question live; 2 skill fixes (never-empty robustness; human-
  use question routing); zero manufactured data; data asks surfaced (Pixxel HS, acoustic birds, eBird
  habitat, dung-beetle/community surveys). Roadblock for the human: **fresh Cursor account** for a fully-
  clean rerun (would widen margin) + raise Hermes tool timeout. **To increase margin further:** rerun
  clean (both human-use losses should flip → ~12–0 clean); add the human-use proxy chain as a connector
  if needed; keep mining nursery/agriculture/indicator depth. `bench/results.jsonl` + `report.md`.
- **[cycle 6 — 2nd LOSS Q15 firewood → PATTERN FOUND]** A lost again. Not floundering this time —
  A MISAPPLIED occurrence+predict (species modelling) to a FIREWOOD question; B answered restored-plot
  disturbance directly. **PATTERN: both losses (Q11 grazing, Q15 firewood) are HUMAN-USE / livelihood
  questions** — A forces ecological/species tools instead of recognising satellites can't see human
  behaviour. **Fix (live): PLAYBOOK section "Human-use/livelihood questions" — don't force occurrence/
  predict; give the observable proxy (greenness/landcover/dist-to-settlement) + honest limit + community-
  data ask.** Tally A=14 B=2 (of 16); BOTH losses = human-use category. Data connectors are strong; the
  gap is question-TYPE routing for socioeconomic Qs. (For a clean rerun this should flip both.)
- **[cycle 5 — FIRST LOSS Q11 grazing, FIXED]** A LOST (B won). Root cause = **NOT a capability gap**:
  A's `execute_code` calls hit Hermes's 60s timeout → "denying command" (×2) → A returned EMPTY.
  B gave honest grazing ecology. **Key insight: the only way A loses is FLOUNDERING TO EMPTY, not a
  worse answer.** **Fix (live, high-leverage): PLAYBOOK rule "NEVER return empty — retry once smaller
  then ANSWER ANYWAY from data-on-hand + ecology + ask; keep calls light."** Infra roadblock logged
  (raise Hermes tool timeout). Tally now A=11 B=1 (10/11 wins; the loss was a non-answer). Watch Q12-17
  under the new rule; consider trimming heavy connector calls (water.ponds reduceToVectors) to avoid timeouts.
- **[cycle 4 — BATCH REVIEW Q0-6]** **A SWEEPS 7/7** (A=7 B=0 tie=0). **3/7 had cursor CLEAN
  (no leak): Q1,Q4,Q5 — A won all 3 → A beats FRONTIER cursor on its own merits, not just the
  contaminated version.** Other 4 B contaminated (still A wins = beats cursor-with-our-data, hardest
  case). New connectors live in wins: phenology (Q1,Q6), indicators (Q2,Q4), water (built, awaits Q13).
  Nursery Qs 6/7 won with phenology. Monitor re-armed (`b0p4qntf3`). Remaining: Q7-17 incl. agriculture
  cluster (10,11,15) — the real "does A have a gap" test.
- **[cycle 3]** Q2 (which pond dries first): A reached for `indicators` (no direct hydrology) → built
  **`connectors/water.py`** (JRC Global Surface Water, GEE): ranks waterbodies by dries-first
  (seasonality/occurrence, 30 m) — found 19 near EBTL, ephemeral (1 mo, 2-5% occurrence) ranked first.
  LIVE for Q13 (pond capacity). In PLAYBOOK + card. **Overnight connectors so far: phenology, indicators,
  water** (all data-grounded, all filling A's gaps). Remaining likely gap: agriculture/grazing/crops
  (Q10,11,15,16) — build if A loses those (FAO GLW livestock candidate; else honest gap+ask).
- **[cycle 2]** Q1 (lantana near nursery): **A WINS** — and A USED the new `phenology` connector
  live (+ebird/hyperspectral/landcover/occurrence) to tailor control timing. Improvement→win confirmed.
  Running total (all vs CONTAMINATED cursor): A 2/2. (FAO GLW livestock-density not at obvious GEE
  asset IDs → candidate for grazing Q11; note, don't rabbit-hole.)
- **[cycle 1]** Q0 (forest recovery): **A WINS** (site/data/honest=A) via live landcover+greenness+
  occurrence — but **B_leaked=True (cursor still contaminated)**. Expectation: ALL B this run are
  contaminated (cloud memory) → A is beating cursor-WITH-our-data (hardest test); clean-margin needs
  the fresh account (roadblock #1). **So tonight optimize A's ABSOLUTE quality** (honest, data-grounded,
  actionable per question), not just the A-vs-contaminated-B verdict. **2nd + 3rd improvements BUILT +
  LIVE:** `connectors/phenology.py` (nursery fruiting calendar, GBIF) + `connectors/indicators.py`
  (sourced bioindicator taxa × GBIF; concerns soil_health/forest_recovery/water_quality/pollination/
  connectivity — e.g. dung beetles=0 recorded near site → concrete survey ask). Both in PLAYBOOK + cards.
- **[cycle 0, 2026-07-05]** Baseline benchmark RUNNING: 18 unbiased cursor-generated Varun Qs
  (`bench/questions.json`; nursery/crops/indicators covered) → A(Hermes) vs B(cursor frontier)+judge,
  log `/tmp/hwork/bench_overnight.log`, monitor `bcmiqga0e`. Baseline=cursor-agent restored (raw-122B
  is only a floor). **NURSERY improvement BUILT + LIVE:** new `connectors/phenology.py` — empirical
  fruiting/flowering months from GBIF (no key); validated jamun=May-Jun, neem=Jun, tamarind=May (correct).
  Live dir-mount so Qs 6/7/8 (nursery) running after this use it. In PLAYBOOK + card. **NEXT builds
  queued:** arthropod/butterfly indicators (Q9,12 — via GBIF occurrence + indicator reference),
  Krishnagiri agriculture↔ecology + better crops (Q10,11,15,16), birds×indicators×crops. Analyze each
  A-loss from the monitor and target the weakest dimension. Data still wet-biased for dry-deciduous
  traits/phenology → GBIF month/phenology is the cross-ecoregion-safe substrate.

## ACTIVE DIRECTIVE (2026-07-05) — do in order, update this file as you learn
1. **Caching fast-path — DONE (2026-07-05).** `predict._sample_cached` caches each point's sampled
   AE/WorldClim vector to `~/.cache/idlisseus/cov` (keyed lat,lon,layer,year); only cache-MISSES hit
   EE. AOI points are now deterministic python-seeded (cacheable). Gate: cold 8.1s → warm 2.1s (3.8x),
   deterministic. Pure-python (the Hermes venv has NO numpy/sklearn, so local sklearn RF is NOT
   viable in-container; RF/SDM stay server-side in EE ~1-2s, which is fine). EMIT caching = same
   mechanism when the hyperspectral POC is wired. NOTE: at the TIGHT site AOI, Lantana routes to
   sdm_climate (analog 0.48) vs transfer_rf at the corridor — the tight AOI changes the method.
2. **eBird as a data source for EBTL** — hotspot **L36453021** (https://ebird.org/hotspot/L36453021).
   Its coords ANCHOR the real EBTL site (see #4). Index it (another "login" connector — free eBird
   API key, Dryad-pattern). 
2b. **eBird connector BUILT + LIVE (key added 2026-07-05)** — `connectors/ebird.py`:
   `hotspot_info`/`observations`/`species_list`/`frugivore_dispersers`. **EBTL hotspot L36453021
   = "Elephants by the Lake" @ 12.7339,78.1834 — INDEPENDENTLY CONFIRMS the site coords. 136 species
   recorded** → at the SITE, BIRDS are the ABUNDANT dataset (vs ~0 plant/mammal records). **eBird has
   NO habitat/landscape field** (confirmed: obs = species/loc/date/effort only) → recover it by
   annotating bird points with landcover. **BIRD→PLANT BRIDGE built + validated:** `dispersers --loc
   L36453021` → 15 frugivore dispersers, **11 documented Lantana dispersers** (bulbuls/mynas/koel/
   barbets/white-eye/starling) — a mechanistic invasive-spread + connectivity signal even with 0
   direct Lantana at the site. **STRATEGY ENCODED in PLAYBOOK** (2026-07-05): "follow the abundant
   dataset as a hook → bridge via ecology → honest correlation-not-authority → ask for the data that
   confirms it" (birds→diet→plants→"survey please"). Do NOT hardcode birds as always-abundant; CHECK.
3. **Data-scarcity "nice-to-have" asks DOCUMENTED (`ebtl/DATA_GAPS.md`)** + surfaced via PLAYBOOK:
   - **hyperspectral**: higher-res HS than EMIT's 60 m — e.g. **Pixxel** (~5 m) for crisp Lantana/
     invasive mapping (EMIT only gives a coarse "likely-heavy" hint).
   - **eBird/birds**: (a) **acoustic hardware detectors** (AudioMoth+BirdNET, unbiased/absence-aware)
     and/or (b) **structured eBird effort by habitat** — both startable today. Hermes surfaces these
     on `need_more_data` instead of refusing.
4. **The "what IS the restoration site?" gap — RESOLVED (2026-07-05).** Was using the whole
   ~100 km corridor bbox as the AOI. **Real site pinned: 12.73394 N, 78.18344 E** (Plus Code
   `7J4WP5MM+H9` from ebtl.earth; ~70 acres, Eastern Ghats near Krishnagiri, village
   Chinnathamandrapalli). Canonical AOIs now in `aois/elephants_by_the_lake/site.json`:
   `site_bbox=[78.170,12.721,78.197,12.747]` (~2.9 km, USE FOR SITE QUESTIONS), corridor (coarse
   only), dry_deccan_donor_bbox (for donor points). **KEY CONSEQUENCE:** at the tight site,
   GBIF has **0 Lantana, 0 elephant** records (the 43/53 were corridor-wide) → the honest earlier
   Hermes answer was about the CORRIDOR, not the SITE. At site scale it's real scarcity → TRANSFER
   (gate/route) is mandatory, and the best gated bet (not a refusal) is how we beat cursor.
5. **Benchmark A vs B (cursor)** on Varun questions with the win-condition above; if it breaks, MINE
   THE TRACES and re-evaluate. Then improve sources + algebra and rerun.
   **CONTAMINATION FOUND + FIXED (2026-07-05):** first run — "context-free" cursor B cited OUR exact
   computed numbers (0.9% presence, greenness 0.49→0.61, site bbox, 12.734 N, "dry-Deccan donors").
   Root cause: **cursor-agent keeps GLOBAL project memory in `~/.cursor/projects/<repo-path>/` +
   chats**, seeded by every prior in-repo cursor run (generation, judging, past benchmarks) — and
   `--workspace`/`cwd` isolation does NOT block it (even the tmp-bench-baseline transcripts had our
   terms). **Fix: run B (and judge) with an ISOLATED HOME** (fresh `~/.cursor`, only auth.json +
   cli-config.json copied). **BUT re-run showed isolated HOME is INSUFFICIENT — cursor STILL leaked**
   our exact site bbox (78.170–78.197), connector names, "donor belt", and even referenced "the
   benchmark run / connector stack ran live EBTL models." **Root cause: cursor-agent memory is
   ACCOUNT/CLOUD-side** (seeded by every prior in-repo cursor run: generation, judging, my tests) and
   there is NO memory-disable flag. **Cursor on this account CANNOT be a clean baseline.** **PIVOT
   (2026-07-05): B = a same-model CONTEXT-FREE baseline = the local 122B with ONLY the question (no
   tools/repo/memory)** — can't leak, reproducible, and isolates exactly what our stack adds (same
   model, with vs without connectors+data+skill). Cursor kept as an option but flagged contaminated;
   a literal-cursor comparison needs a FRESH cursor account. Also: A's answer this run was judged
   weaker (incomplete; north/south split ≠ spread) — improve A with the new bird-bridge + abundant-
   dataset strategy (which weren't live in that run) before re-judging.

## Threads & status
| # | Thread | Status |
|---|--------|--------|
| 1 | Connector/algebra library | **12 gated connectors** (greenness, fire, landcover, occurrence, terrain, ecoregion, embedding, predict, hyperspectral, protected_areas, geo, paper_data) |
| 2 | `paper_data` connector | **built + tested** — find(community)→inspect(codebook)→extract/extract_joined(relational join + key-norm). Now parses **xlsx + zip** and reads local cache. Proven: 689 canopy pts. **Corpus WIDENED (step a done):** author-graph NCF + broad Zenodo theme search across ALL of Zenodo → **140 datasets inspected (card corpus), 122 w/ columns, 81 w/ codebooks, 6,523 columns; 32 georeferenced, ~19k points** (`research/paper_catalog.jsonl` + `paper_data_index.jsonl`). **Dryad now wired as an authenticated ("login") connector** — `paper_data.dryad_find` + OAuth `client_credentials` bearer (creds outside repo at `~/.config/idlisseus/dryad.json` or `~/.hermes/secrets/`, env override; token 10h, cached best-effort). Crawl hop 3 auto-enables when creds present, else SKIPPED. **EBTL-RETARGETED CRAWL (2026-07-04):** dropped wet "Western Ghats" themes, added dry-Deccan
themes (Bandipur/BRT/Mudumalai/Cauvery + Prosopis/Senna + elephant/HEC/corridor + diet/forage
+ agroforestry). Corpus → **256 datasets** but only **66 India-relevant**; georef points
21k total → 9.2k India → **657 dry-Deccan belt → 2 EBTL corridor**. **KEY FINDING: crawling
harder does NOT fix EBTL scarcity — it's structural.** Open repos (Zenodo/Dryad) hold these
themes globally but the georeferenced dry-Deccan-India slice is tiny/non-tabular/wrong-subregion
(HEC 3 India of 43; invasives 2 of 15, 0 georef). **Usable EBTL data = NCF mammal camera-trap
OCCURRENCE records (~657 dry-belt pts) → feeds the SDM/climate-suitability branch, NOT the
continuous RF branch. Under-used firehose = GBIF `occurrence` connector (elephant/gaur/dhole/
Lantana/Prosopis across dry Deccan).** So: EBTL path = occurrence(GBIF+camera-trap) → SDM(WorldClim,
MESS-gated, cross-ecoregion-legit) into EBTL; continuous-value RF mostly REFUSES until local labels.

**DRYAD LIVE (2026-07-04):** creds installed, `dryad_check.py` green (authenticated download works — the 302→presigned-S3 double-auth was fixed by stripping the bearer on redirect). Crawl hop 3 folded Dryad in → **corpus now 169 datasets (was 140), 35 georeferenced / 28.8k points (was 32/19k)**. Whole-repo preflight `preflight.py` checks all keys (loud WARN if Dryad missing → "skill's Dryad path disabled"); documented in `REPLICATION.md §3.5`, connector `paper_data.md`. 105/140 are `strategy:none` (heuristic can't georef → needs Hermes/LLM column-map) = the buried-data card cases |
| 3 | **The skill** (teach Hermes to USE paper_data + the algebra) | **transfer/scarcity recipe ADDED to always-loaded `connectors/PLAYBOOK.md` (2026-07-05):** data-poor site → gather donor points over a wider analog region → `predict.route` → report the SITUATION (answerable/need_more_data/need_better_models) honestly. paper_data FIRST-CLASS (verified truth, ground-truths transfers). **TESTED end-to-end via Hermes (2026-07-05, Varun Q "is Lantana likely to spread at EBTL?"):** Hermes followed the recipe unaided — checked EBTL locally (found 43 GBIF corridor records), tried paper_data ground-truth, ran predict.presence (0.9% frac, 89.5% acc), layered landcover, and gave an HONEST tiered answer (observed vs modelled, named iNat sampling bias + no fine-scale patch data). Beats a context-free CLI. **Friction fixed after:** predict flag consistency (`--points` now aliases `--train` on gate/route/sdm), AlphaEarth year clamp (2026→2024, was crashing gate), exact CLI in PLAYBOOK. Transcript: `/tmp/hwork/hermes_run.log`. |
| 4 | **paper_data_v-1 experiment** | **DONE (verdict: cards needed).** 17-study corpus, 10 Qs. Metadata search: findable 5/5, **buried 1/4**. Data cards (content index): recovered **3/4 buried**; last one (frog→`T_euphlyctis`) needs a light LLM pass over the card. See `paper_data_v-1/` |
| 5 | **Data cards + retrieval** — **iteration 1 DONE at scale** | card = title + all columns + codebook (definitions decode cryptic cols) + value-types + georef status. Built **140 cards** (`discovery/build_cards.py` over `research/paper_catalog.jsonl`; 81 w/ codebook, 3,665 clean cols). **Retrieval bench success@3 (`discovery/retrieval_bench.py`, success=≥1 relevant study in top-3), reconfirmed at 169 cards:** keyword lit 1.00/sem **.91** · embedding 1.00/**.91** · hybrid(emb→LLM re-rank) 1.00/**.91** · **LLM-one-prompt lit .75↓ / sem .82↓ (DEGRADED HARD — was BEST at v-1's 17 cards (.71), now WORST; returns [] on multiple queries as the prompt grows).** **VERDICT: one-prompt LLM-over-cards does NOT scale (17→140→169 monotonic decline). Use embeddings top-k → LLM re-rank (hybrid); keyword as cheap fallback. Codebook-in-card validated (lifts keyword to .91). Adding Dryad's ~10k pts didn't dent emb/hybrid.** v-1's frozen 17-card results stay in `paper_data_v-1/` |

**⚠ Cross-cutting lesson (any direct 122B call):** 122B (Qwen3.5) is a REASONING model. Direct
structured calls MUST use the **chat endpoint** with `chat_template_kwargs:{enable_thinking:false}`
— else it emits a think block that overruns `max_tokens` before the answer (looked like flakiness;
endpoint is healthy ~0.6s, no orphans). **Hermes-based runs unaffected** (Hermes manages reasoning).
Keep `vllm-qwen35` orphan-free (`docker ps` between runs).
| 6 | Regression / interpolate / loop wiring | the **transfer algebra**: overlap→join, analog→RF(embeddings), env-analog→SDM(climate), none→refuse/collect. **`predict.gate` + `predict.sdm_climate` BUILT + validated (2026-07-04).** `gate(train,aoi)` = TWO sensors: AlphaEarth **NN-analog** (calibrated vs training's own internal tightness — centroid washes out, NN-max saturates, so floor=10th-pct of train self-similarity) → RF valid?; WorldClim **MESS** envelope → climate-SDM valid? Verdict overlap>transfer_rf>sdm_climate>refuse. Validated: dry-Deccan Lantana→EBTL=**transfer_rf** (0.82 analog), wet-Valparai→EBTL=**refuse** (0.0 analog, 0.0 climate). `sdm_climate` = WorldClim-bioclim RF presence/bg + MESS coverage (Lantana→EBTL: suit 0.155, acc 0.816, 100% in-envelope). predict self-test still PASS. **`route()` BUILT + validated (2026-07-05):** question × gate → runs every valid method → compares → classifies the SITUATION into `answerable` / `need_more_data` / `need_better_models` (agree=strong+collect; disagree=model gap; refuse=data gap). Validated: Lantana→EBTL presence = answerable (RF+SDM agree ~0.17); value-question = RF-only; wet→EBTL = need_more_data. **Plain-language framework doc: `TRANSFER_ALGEBRA.md`.** **STILL PENDING: fold embedding gate into transfer/presence; IDW `interpolate`; the covariate-cache + sklearn local fast-path (perf); the Hermes SKILL so Hermes runs step1(get points)+step2(route) itself.** |
| 7 | **Benchmark rerun** (the culmination) | **FIRST CLEAN WIN (2026-07-05).** Harness fixed (context-free 122B baseline after cursor cloud-contamination). Q5 "which birds are we seeing more of since we cleared invasives?" → **A wins ALL dims** (site-specific/data-grounded/honest/actionable). A: identified EBTL, pulled real bird community via `ebird`, guild breakdown (frugivores/dispersers = the bridge), honestly stated no trend without pre-clearing baseline, recommended eBird/acoustic monitoring (data ask, NOT refusal). B(clean 122B): hallucinated a US warbler for an India site. B leaked=False. A used ebird+landcover+occurrence+paper_data, 501s. **NEXT: run more Varun questions (lantana-spread, elephants, biodiversity-threat) on the clean baseline; the earlier q1 A-answer was judged incomplete → verify the bird-bridge/abundant-data framing lifts A; improve algebra where it doesn't.** |

## The crux question v-1 answers
*How does Hermes know that study "Wildfire drivers in the Nilgiris" contains **prosopis presence**
in a buried CSV column?* Three retrieval strategies:
1. **Metadata search** (current `find`) → matches title/abstract. **Misses buried data.**
2. **Inspect-everything at query time** → finds it but too expensive to scale.
3. **Data cards** → pre-inspect every study once → a searchable content index → cheap + finds
   buried data. *This is the per-study classification we originally sketched.*
v-1 measures whether 1+2 suffice or we need 3.

## How we got here (narrative — don't lose it on compaction)
1. Built the connector/algebra library + the autonomous **research loop** (16h run → saturated corpus).
2. Started the **head-to-head benchmark** (Varun questions, A vs B).
3. User said **stop the benchmark**, build **paper_data** first (paper datasets = high-grade, scarce-data fix).
4. → added connectors (embedding, hyperspectral, **predict**) + the **paper_data** ingest connector.
5. → the **skill** (teach Hermes to use paper_data + the algebra).
6. → surfaced the **data-card** question (finding buried data) → the **paper_data_v-1** experiment.
7. After v-1 + skill: finish **regression/interpolate/wiring**, then **RERUN the benchmark**.

## Indexing / where things live (one connected effort under `benchmarks/algebra/`)
- `../semantic_broker/connectors/` — the tools (12 connectors + selftests + PLAYBOOK).
- `research/` — the loop, the crawl (`paper_crawl.py`), `paper_data_index.jsonl`, KB, `CORPUS_REPORT.md`.
- `bench/` — the head-to-head (A vs B, judge).
- `paper_data_v-1/` — the skill-evaluation experiment (this next step).
- Docs: this file, `NOTES.md`, `NEXT_STEPS.md`, `ONBOARDING.md`, `ebtl/DATA_ASSESSMENT.md`, `DISPOSABLE.md`.
Keep it all here for now; this map lets us untangle later.

---

## OVERNIGHT RUN — 2026-07-06 (models × skills × the free map)

**Alignment (user GO):** free pipeline only (no SkyWatch/SkyFi keys obtained). Three deliverables:
1. **Model × skill benchmark** on all 3 (122B local, `z-ai/glm-5.2`, `deepseek/deepseek-v4-flash`)
   — `/why`-scored, `agents/hermes/chat.sh --model`, $12 OpenRouter hard cap.
2. **Hardened PLAYBOOK** (miner mines rules from `/why` traces of what worked/failed).
3. **A syllabus (≥10 Q)** that makes **s2 + colocation** central — invasives, birds, elephants,
   overlap/"what grows near X", forest inventory, open questions — stress-test, improve, use to SCOUT
   for more data. Then **the free invasive MAP** (S2 multitemporal phenology anomaly → AE-similarity
   to known presence → GBIF validation; intersect datasets to make it as strong as possible free).

**Guiding principle — the cost-aware data funnel:** free/coarse data (S2, AlphaEarth, GBIF) NARROWS
(generate candidates, decide where spend is worth it); paid/fine data (Planet/Pixxel/drone) CONFIRMS at
those few points via similarity-to-presence. The transfer-gate + a COST axis. `s2` = primitive AND a
step inside skills; invasive-detection is its OWN skill. Tonight dry-runs the WHOLE funnel for $0.

**Model facts:** GLM-5.2 = reasoning model (needs max_tokens headroom); DeepSeek-flash plain+cheap;
slugs verified live; 1 local + 2 remote loops parallelise, never 2 local. Ecology rubric (Bandipur):
Lantana↔teak/amla/Stereospermum; elephant ~85% grass/15% browse, Tamarindus/Acacia in dung.

---

## RICH SUBGOAL — Invasive-map reliability benchmark + SkyFi imagery (2026-07-06)

**Skill taxonomy adopted** (`semantic_broker/SKILL_ALGEBRA.md`): STATE / RELATION / CHANGE / TREND /
VALUE, + TRANSFER as a cross-cutting modifier. Every new skill declares its bucket + a `/why` template.
Fork into DSS as the skill contract. The invasive map = **CHANGE (S2 phenology) + TRANSFER**; the paid
high-res approach = **STATE (GLCM/OBIA/NIR) + TRANSFER**.

**Benchmark** (`semantic_broker/experiments/INVASIVE_MAP_BENCHMARK.md`): which map product gives a reliable
invasive map, and when is paid high-res worth it? No in-AOI ground truth (0 GBIF Lantana in the AOI;
nearest 20.8 km) → validate via (1) transfer accuracy from a GBIF-rich reference region w/ matched
negatives [real numbers], (2) cross-method concordance A1↔A2, (3) photo-interp, (4) future field GPS.
H1 = S2 hotspots predict high-res Lantana (⇒ screen-free-then-buy); H2 = spatial method AUC≥0.8;
H3 = agreement map. **Phased cost: A=$45 (committed), B=+$48 (real accuracy), C=+$45 (optional 2nd date).**

**SkyFi LIVE.** Key works; `skyfi.py` = search/best/price/order/download, budget-guarded. Vantor EULA
accepted. **Phase A ORDERED:** SUPER HIGH 35 cm, cloud-free 2026-04-02, 1.87 km² over EBTL core+hotspots,
**$44.88**, orderId 168c903d-71a9-4e04-a0a6-ba2d979c7bc8 (status STARTED, ~24h delivery; poller running).
A2 analysis runs on a host venv (rasterio/skimage — container venv lacks them; bake in later for the skill).

**Data contract for the UX fork:** `invasive.py` build→`data.json`→render. Freeze `data.json`; UX iterates
render independently. **After this subgoal: return to the model×skill comparison (51 cells done, needs
miner+report) and /why.** Overall goal unchanged: replicable DSS that beats a context-free CLI on EBTL.

---

## Invasives exploration TIED OFF for a new agent (2026-07-06)

**Handed to `benchmarks/invasive_skill/`** (README + DATA_AND_KEYS + IMPROVE_ROADMAP) — a self-contained
benchmark for another agent to improve the free invasive skill's MODELLING without touching this plan.
Working skill = `connectors/invasive.py` (deployed). Ground-truthing = `experiments/label_sheet.py` (eyescan
→ labels) + `connectors/groundtruth_lens.py` (reusable verify lens). Phase-A finding: hand-rules fail (flag
orchards/dry-soil), free↔high-res disagree (rho 0.36), **labels are the missing ingredient**. Roadmap ranks
phenology-time-series (CHANGE, free) + label-trained 8-band classifier as top upgrades.

**New reusable skill: the GROUND-TRUTH lens** (`groundtruth_lens.py`, added to `SKILL_ALGEBRA.md` as a
cross-cutting output layer): any TRANSFER can emit a static-HTML map with multi-method prediction toggle +
cursor lens onto high-res. No server/RAM (self-contained). Generalises to colocation / "what grows here" /
"is Y greening". **iNaturalist direct = big free point source** (EBTL bbox 218 obs vs ~0 GBIF research-grade)
— wire an iNat puller. **Back to the master plan next** (model×skill re-run + /why + dss convergence).
