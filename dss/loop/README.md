# dss/loop — the expansion engine (how the DSS grows to a new site or topic)

The connectors (`dss/connectors/`) answer questions **today**; this loop is how the framework **expands**:
go out and search many data sources → transform what's found into searchable **cards + embeddings** →
propose a **syllabus** of questions scored by a rubric → **mine the agent's own traces** to turn recurring
failures into permanent playbook rules. It is first-class because onboarding a new AOI or subject = running
this loop, not hand-writing connectors.

```
  crawl.py        search sources (Zenodo/Dryad/OpenAlex + author graphs) → inspect → paper_catalog.jsonl
       │                                                                    + paper_data_index.jsonl (points)
       ▼
  build_cards.py  catalog → content CARDS (title + every column + codebook) → dss/corpus/cards.jsonl
       │                                                (what discovery.py embeds & searches semantically)
       ▼
  loop.py  ── the AOI bootstrap tick, wires the four components for one site: ──────────────
       ├─ scout.py       discover + VERIFY the data frontier (GBIF/eBird/Zenodo/CKAN + analog ecoregion;
       │                 flags "phantom" species that resolve but return 0 rows — never admitted)
       ├─ proposer.py    turn the AOI's weighted theme buckets → candidate questions (primitive chains)
       ├─ controller.py  classify/dedup into a bank: answerable_now · needs_connector · blocked_no_data
       └─ miner.py       read past run logs + state.db → recurring failures → playbook_rules.md
```

## Run it

```bash
# one bootstrap tick for an AOI (scout hits live APIs; proposer/controller/miner are local + fast)
python3 dss/loop/loop.py --aoi benchmarks/algebra/aois/elephants_by_the_lake.json
#   → writes dss/loop/runs/<aoi>/ : sources.json, questions.jsonl, playbook_rules.md, bootstrap_report.md
#   LOOP_OUT=<dir>     override the output dir
#   MINER_LOGS=<glob>  override the run-log glob the Miner mines (default: benchmarks/algebra/runs/*.log)

# grow the corpus (crawl new datasets, then rebuild cards)
python3 dss/loop/crawl.py --max-datasets 40 --max-authors 20   # → appends to dss/corpus/{catalog,index}
python3 dss/loop/build_cards.py                                 # → rebuilds dss/corpus/cards.jsonl
```

`crawl.py` reuses `dss/connectors/paper_data.py` (inspect/extract) and writes to `dss/corpus/`; the raw
download cache (`paper_cache/`, ~1.5 GB) stays local and gitignored. `build_cards.py` is the source of truth
for `cards.jsonl` — always rebuild it after a crawl so `discovery.py` sees the new datasets (the embedding
cache re-keys by corpus size and rebuilds itself on the next search).

## The AOI (the site config the loop expands from)

An AOI json (in `benchmarks/algebra/aois/`, `template.json` to start) declares the site: bbox, ecoregion,
weighted theme **buckets**, seed species (invasive + flagship), analog ecoregion sites, known sources. The
proposer reads the buckets to theme questions; the scout reads bbox + species to verify the data frontier.

## Improvement loop (why traces matter)

The Miner is the seed of self-improvement: it reads what the agent actually did (`~/.hermes/state.db` +
run logs), finds REPEATED failure patterns (e.g. write-to-read-only, direct-occurrence-by-common-name), and
emits playbook rules — the same engine documented in `agents/hermes/TRACE_INTROSPECTION.md`. Provenance +
design: `dss/ARCHITECTURE.md`, `dss/AOI_ONBOARDING.md`.
