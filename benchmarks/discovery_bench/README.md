# discovery_bench — does semantic retrieval beat keyword over the ingested corpus?

Tests the `dss/connectors/discovery.py` embeddings wire-up. Holds the CORPUS constant (the same 169 content
cards) and varies only the retriever, so any gap is the embeddings lever, not the cards.

`bench.py` — 12 deliberately **paraphrased** query→DOI pairs (lay phrasing whose target dataset title uses
different vocabulary: "weed taking over coffee" → *"Brewing trouble: coffee invasion"*). Compares a keyword
baseline (BM25-lite over card content) vs `discovery.search` (bge-small embeddings). Metrics: recall@5, MRR.

Run inside the hermes container (needs the fastembed venv + the `/opt/data/corpus` mount):
```
docker cp bench.py hermes-live:/opt/data/work/bench.py
docker exec hermes-live /opt/data/work/venv/bin/python3 /opt/data/work/bench.py
```

## Result (2026-07-11)

| retriever | recall@5 | MRR |
|---|---|---|
| keyword (BM25-lite over cards) | 0.50 | 0.20 |
| **embeddings (discovery.search)** | **0.75** | **0.67** |

The win is **ranking**: the right dataset lands at rank 1 for 8/12 paraphrased queries where keyword buries
it at rank 3–5 or misses entirely. This is the earlier "keyword ≈ embeddings (both .91)" finding's blind
spot — that bench used queries whose keywords literally matched; these don't, which is the real lay-user
case. 2 genuine misses both ways (roadkill, myna).

Agent-level: after PLAYBOOK constitution rule 4 was rewritten to name `discovery.search` as the FIRST
literature call, a deepseekv4 hermes run chained `discovery.search → paper_data.extract` (13 tools vs 18)
and surfaced the coffee-invasion dataset end-to-end. Wiring a connector isn't enough — the always-on
constitution reflex has to point at it.
