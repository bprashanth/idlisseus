# Research broker — final corpus report

**Status: FROZEN 2026-07-04.** The autonomous loop reached **saturation** of the
accessible open data frontier across 5 Indian restoration landscapes and was stopped
cleanly (checkpoint in `state.json` is intact — the run is fully resumable). This is
the deliverable summary; the corpus itself is `kb.jsonl` (provenance-tracked, every
value sourced or flagged a gap). Final `kb.jsonl` ≈ 2,975 lines, of which ~370 are
`extractor:"refresh"` maintenance re-measurements (filterable; the substantive corpus
is ~2,600).

## Reproduce / resume / query

**Prereqs** (same box; see repo `REPLICATION.md`): 122B up (`vllm-qwen35`),
`hermes-agent-local` image, EE creds staged, the 11 connectors in
`benchmarks/semantic_broker/connectors/`. **Data engines used** (no API keys):
EuropePMC, OpenAlex, Semantic Scholar, Crossref, Zenodo, GBIF, SoIB, Unpaywall;
Earth Engine (project `plantwars`) for the map/embedding/EMIT/RF connectors.
`cursor-agent` (already authenticated) is optional — used for indicator extraction +
hypotheses; the loop **falls back to a free heuristic** if it's unavailable.

```bash
cd benchmarks/algebra
# QUERY the frozen corpus (fast, grounded, cites sources):
python3 research/ask.py --aoi aois/elephants_by_the_lake.json "is lantana showing up?"

# RESUME / re-run the loop (reads research/state.json; skips seen papers):
nohup python3 research/autoloop.py --budget-seconds 39600 --max-cursor 150 \
      --disk-min-gb 10 >> research/autoloop_run.out 2>&1 & echo $! > research/autoloop.pid
# STOP / freeze:  kill $(cat research/autoloop.pid)
# FRESH run (discard corpus): rm research/{kb.jsonl,state.json,narratives.jsonl}

# Onboard a NEW AOI: write aois/<name>.json (see aois/template.json + ONBOARDING.md),
#   add it to AOIS in research/autoloop.py, re-run.
```

Full design + safety (checkpoint/quota/disk-S3/pacing): `RESEARCH_AUTOLOOP_PLAN.md`.
What's disposable vs keep: `../DISPOSABLE.md`.

## Totals
- **2,591 indexed findings** — **2,025 measured, 566 honest gaps** (never fabricated).
- **1,783 research papers** mined (EuropePMC / Semantic Scholar / OpenAlex / Crossref,
  Indian-fundee-prioritised; Unpaywall for legal OA). Literature saturated.
- **75 species** catalogued with occurrence trends (biodiversity per AOI).
- **37 hypotheses** (cursor-as-judge narratives + clarifying questions).
- **5 AOIs**, **11 gated connectors**, **8 NCF/ATREE Zenodo datasets** indexed.
- Extractors: heuristic 2009 · cursor 128 · discover 75 · refresh 367 · predict 4 · zenodo_org 8.

## The 5 AOIs generalised (differentiated real signals)
| AOI | ecoregion | signal (satellite + EMIT + RF) |
|---|---|---|
| Elephants by the Lake | S. Deccan dry deciduous | greening +0.014/yr, Shrubland, Lantana modelled 0.9% (RF acc .895) |
| Anamalai–Nilgiris | S.W. Ghats wet | flat/Tree-cover, Lantana 6.6% (.858), hyp_ndvi 0.67 |
| Kanha–Pench | Central Indian teak | **NDVI declining** −0.006/yr |
| Aravalli (FES) | NW thorn scrub | **arid** hyp_ndvi 0.12, Built-up, Prosopis (.938) |
| Meghalaya groves | NE subtropical | **high fire 4.2** (jhum), Chromolaena skipped (3 pts) |

## Example hypothesis (the loop reasoning like an ecologist)
> **EBTL:** *"Early-stage native restoration is greening on a shrubland parcel —
> biomass/canopy respond as expected for regrowth — but the spectral trajectory
> diverges from mature reference."*
> **Clarifying Q:** *"Is plot-level **sapling survival** or planting density rising
> enough to explain the greening without meaningful height growth?"*

That question lands exactly on the field-data gap flagged in `ebtl/DATA_ASSESSMENT.md`
— the loop independently re-derived what EBTL needs to collect.

## What's answerable now vs collect-it (the honest frontier)
- **Answerable (real data):** restoration greening, fire, land cover, NDVI/embedding
  convergence, hyperspectral chemistry, bird conservation status (SoIB), occurrence
  trends, modelled invasive presence (RF). Ask via `research/ask.py`.
- **566 gaps** — mostly field/socioeconomic (sapling survival, livelihoods, soil,
  mammal camera-traps, elephant-corridor GIS). These are the "collect it" list.

## Recommended next value (not auto-run — needs a go-ahead)
1. **Full-text CSV/table extraction** — Unpaywall → pull data tables from the ~1,800
   papers already found (deepens "look inside the CSVs" beyond abstracts).
2. **More AOIs** — the methodology is AOI-portable (one JSON each; proven on 5).
3. **Graduate connectors** from the gaps: rainfall (CHIRPS), forest-change (Hansen),
   water (JRC), and the NETWORK/PATTERN primitives.

## Cleanup
`kb.jsonl` is the keep-artifact. `refresh`-tagged entries are repeated occurrence
snapshots (filterable). Full disposable list in `../DISPOSABLE.md`. The process
self-terminates at its budget; stop early with `kill $(cat research/autoloop.pid)`.
