# litscout — author co-authorship-graph paper & dataset discovery (OpenAlex)

- **purpose:** beat a manual literature review by **walking the people**, not just matching titles. From a
  topic or a seed author, find the tight **co-authorship cluster**, then pull their works and especially
  their **archived datasets** (Zenodo/Dryad/figshare via OpenAlex `type:dataset`) — where the presence
  **points** live. Chain: author → co-authors → topic → datasets → (bridge) points.
- **engine:** OpenAlex (free, no key; polite pool via mailto). Stdlib only.

**functions**
- `works(query, kind='dataset'|'article', india=False)` — ranked works/datasets on a topic (`--india` =
  authored from an Indian institution).
- `authors(query)` — the co-authorship cluster for a topic (authors ranked by # of its works) = seeds.
- `expand(author, topic)` — resolve author → their topic works → co-authors → the cluster's **datasets**.

**use:** run FIRST for any literature / taxonomy / phylogeny / diet question, alongside `paper_data`:
`litscout authors "<topic>"` → pick a seed → `litscout expand --author "<seed>" --topic "<topic>"` → take
the **dataset DOIs** → `paper_data.extract --url <doi>` for the points inside. This reaches archived data a
keyword search never lists.

**gotcha:** a DOI here is a POINTER — extract the actual points with `paper_data`. `type:dataset` catches
Zenodo/Dryad/figshare records. The `--india` filter is author-institution, not species locality.

**example**
```
python /opt/data/connectors/litscout.py authors --query "shieldtail snake Uropeltidae phylogeny India"
python /opt/data/connectors/litscout.py expand --author "David J. Gower" --topic "Uropeltidae India"
python /opt/data/connectors/litscout.py works --query "Ahaetulla phylogeny peninsular India" --kind dataset
```
Validated (2026-07-08): surfaced the real uropeltid cluster (Ganesh, Bhupathy, Gower → Surya Narayanan,
V. Deepak, Sandeep Das) + archived reptile datasets with DOIs. Corpus demo: `benchmarks/eastern_ghats_run/
rescout.json` (63 papers + 3 datasets over 6 Eastern Ghats themes).
