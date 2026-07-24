# dss/corpus — the ingested paper/dataset corpus (the discovery layer's source of truth)

What `discovery.py` searches and what `paper_data.extract` pulls points from. Three text indexes are
**checked into git** (small, the reproducible product); the large raw download cache is **not** (1.5 GB,
regenerates via the crawler).

## Checked in

| file | lines / size | what it is | produced by |
|---|---|---|---|
| `cards.jsonl` | 256 cards / ~1.3 MB | one **content card** per dataset = title + ALL column names + codebook definitions + n_points + georef status. The retrieval surface `discovery.py` embeds. | `dss/loop/build_cards.py` (over `paper_catalog.jsonl`) |
| `paper_catalog.jsonl` | 256 / ~0.75 MB | every inspected dataset's raw metadata + columns + codebook — the **card source material**. | `dss/loop/crawl.py` |
| `paper_data_index.jsonl` | 21 084 / ~7.7 MB | the **extracted georeferenced points** (35 datasets, ~28.8k points) — occurrences pulled out of dataset tables. | `dss/loop/crawl.py` |

## NOT checked in (regenerable — gitignored)

- raw downloaded dataset files (`paper_cache/`, ~1.5 GB) — re-fetch via `dss/loop/crawl.py`.
- the embedding cache (`emb_<hash>.npy`) — lives in the container at `/opt/data/work/discovery/`, NOT the
  repo; rebuilds on first `discovery.py search` (bge-small over the cards).

## How it's served to the agent

chat.sh mounts `dss/corpus` → `/opt/data/corpus` (read-only). `discovery.py` reads
`/opt/data/corpus/cards.jsonl`. To grow the corpus for a new site/topic: run the loop crawler
(`dss/loop/`), which appends to `paper_catalog.jsonl` + `paper_data_index.jsonl`, then rebuild
`cards.jsonl` with `build_cards.py`. See `dss/loop/README.md`.

## Why embeddings over these cards (the benchmark)

Semantic retrieval over the cards beats keyword search on paraphrased lay queries — MRR 0.67 vs 0.20,
recall@5 0.75 vs 0.50 (`benchmarks/discovery_bench/`). The lever is the CARD (codebook-in-card bridges
lay-word→cryptic-column); embeddings add the semantic map ("weed in coffee" → "coffee invasion") that
keyword misses. See `dss/PRODUCTION_MOVE_CHECKPOINT.md`.
