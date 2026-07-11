# Production move checkpoint (2026-07-11)

Live log of the "converge the working DSS out of `benchmarks/` into a production shape" move, so a
post-compaction agent can resume. Ordered plan lives in `benchmarks/algebra/MASTER_PLAN.md`
(§"WHERE WE ARE NOW"). Branch: `connectors`. Commit as you finish each step.

## THE EMBEDDINGS FINDING (do not lose — this is the load-bearing result)

`dss/connectors/discovery.py` = SEMANTIC retrieval over the 169-card corpus (`dss/corpus/cards.jsonl`,
each card = title + all column names + codebook) via **bge-small** (fastembed, ONNX, **no torch**).
Self-heals to the PERSISTENT `/opt/data/work/venv` (NOT the image venv `/opt/hermes/.venv` — that is wiped
on `chat.sh --restart`). Embeddings cached to `/opt/data/work/discovery/emb_<hash>.npy`.

**Retrieval bench** (`benchmarks/discovery_bench/bench.py`, 12 deliberately PARAPHRASED queries, corpus held
constant so the retriever is the only variable):

| retriever | recall@5 | MRR |
|---|---|---|
| keyword (BM25-lite over cards) | 0.50 | 0.20 |
| **embeddings (discovery.search)** | **0.75** | **0.67** |

The win is RANKING — the right dataset lands at **rank 1 for 8/12** paraphrased queries where keyword buries
it at rank 3–5 or misses ("bee numbers on tribal coffee farms", "birds coming back after replanting" →
keyword whiffs, emb rank-1). 2 genuine misses both ways (roadkill, myna). This is the blind spot in the
earlier "keyword ≈ emb, both .91" finding: THOSE queries had literal keyword matches; real lay queries
don't ("weed in coffee" → "coffee invasion").

**KEY LESSON: a wired connector is invisible until the always-on constitution NAMES it.** First deepseekv4
agent run ignored discovery and fell back to habitual `paper_data.find` (keyword). Only after rewriting
PLAYBOOK **constitution rule 4** ("first literature call is `discovery.search`") + registering it in the
router connector list + `recipes/papers-first.md` did the agent run the intended chain
`discovery.search → paper_data.extract` (13 tools vs 18), surfacing "Brewing trouble: coffee invasion" for
a lay Lantana ask. chat.sh ALREADY mounts `dss/corpus` → `/opt/data/corpus` (wired).

## MOVE STATUS (check boxes as you go)

- [x] (1) `dss/connectors/` — 25 connectors + recipes + PLAYBOOK + SITE_EBTL.json. LIVE-mounted. smoke ✓
- [x] (2) `discovery.py` embeddings wired + benchmarked (above). PLAYBOOK rule 4 + router + recipe updated.
- [ ] (3a) corpus: `dss/corpus/` = cards.jsonl + paper_data_index.jsonl (+ paper_catalog.jsonl source);
      git the small indexes, gitignore the big caches; README naming regen-vs-checked-in.
- [ ] (3b) `dss/loop/` = scout · proposer · controller · miner · loop · crawl · build_cards (the EXPANSION
      ENGINE, promoted from `benchmarks/algebra/{components,research,discovery}/`). Fix paths (see below).
- [ ] smoke after each move; golden-regression / multi-turn bench after the loop move (constitution intact).
- [ ] one pass of scout+proposer+miner on Eastern-Ghats native-species conservation (EBTL AOI).
- [ ] (4) docs (Phase 2, later).

## PATH FIXES REQUIRED when moving to dss/loop/ (they point at OLD locations)

- `components/loop.py`: `SB_CONNECTORS = ALGEBRA/../semantic_broker/connectors` → **dss/connectors**;
  `ALGEBRA/aois` + `ALGEBRA/runs` outputs → parameterize (`--out`, env `MINER_LOGS`); AOIs STAY in
  `benchmarks/algebra/aois/` (experiment inputs).
- `research/paper_crawl.py` (→ `crawl.py`): `sys.path … semantic_broker/connectors` → **dss/connectors**;
  writes `paper_data_index.jsonl` + `paper_catalog.jsonl` → point at **dss/corpus/**.
- `discovery/build_cards.py`: `CATALOG=../research/paper_catalog.jsonl` → **dss/corpus/paper_catalog.jsonl**;
  `CARDS=cards.jsonl` → **dss/corpus/cards.jsonl**.

Nothing OUTSIDE `components/` imports the components (verified). `research/ask.py` imports `kb`.

## SMOKE RESULTS (append as you run)

- discovery bench: emb MRR .67 vs kw .20 (above). ✓
- agent chain discovery→paper_data.extract on deepseekv4: 13 tools, coffee-invasion dataset found. ✓
