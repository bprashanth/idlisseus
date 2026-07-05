# Research discovery loop

A bounded loop that **consults real research, derives questions + indicators, looks
them up over time against real data, indexes everything with provenance, and answers
open user questions** — so when the EBTL team asks "is a new invasive showing up?",
"are livelihoods improving?", "how are the nurseries?", we can give *some* grounded
answer and say exactly where the data came from (or that there is none — collect it).

**No fabrication.** Every value comes from a live API/connector and carries a source.
A gap is recorded as a gap with a "collect it / write a connector" suggestion.

## Engines (all verified available on this box)

| Role | Engine | Notes |
|------|--------|-------|
| Mine literature | **OpenAlex** (free, no key) | 800+ real papers per ecoregion query |
| Mine datasets | **Zenodo** (datasets + CSV/codebooks) | attached data files |
| Extract indicators/questions from a paper | **cursor-agent** (`-p` headless) | paid cloud — kept single-shot & bounded |
| Measure over time | **GBIF** (incl. eBird/iNaturalist), **SoIB 2023**, **EE connectors** | occurrence-by-year, bird trends, NDVI/fire/land cover |
| Solve harder questions | **Hermes + 122B** (`run_solver.sh`) | the existing Solver |

## The tick (`loop.py`)

```
compute the AOI's satellite indicators once (NDVI trend / fire / land cover)   # real EE
for each theme:
    papers = OpenAlex(theme + ecoregion)                    # real literature
    for each paper:
        indicators = cursor-agent(abstract)                 # {indicator, question, unit, measurable_via}
        for each indicator:
            reading = measure(indicator)   routed by measurable_via:
                species_occurrence   -> GBIF occurrence-by-year (is it appearing/increasing?)
                bird_trend_dataset   -> SoIB priority/trend/IUCN
                satellite_timeseries -> the precomputed EE indicators
                socioeconomic        -> data.gov.in CKAN, else GAP (livelihoods)
                field_survey/unknown -> GAP (collect it / paper's own CSV)
            append to KB with paper + source + provenance
```

Bounded by `--themes`, `--papers`, `--budget-seconds`; every external call is
timeout-wrapped, so it cannot hang. cursor-agent is paid — keep `--papers` small.

```bash
python3 research/loop.py --aoi aois/elephants_by_the_lake.json \
    --themes invasives,restoration,livelihoods,nurseries --papers 2
```

## Answering an open question (`ask.py`)

```bash
python3 research/ask.py --aoi aois/elephants_by_the_lake.json "is a new invasive showing up?"
```

Retrieves matching indexed knowledge **and** runs a live occurrence-over-time reading,
then gives a grounded verdict with sources — or says it's a collect-it gap.

## The index (`kb.jsonl`)

Append-only. One record per indicator: the question, the paper it came from, the real
reading (or the gap + what to collect), and full provenance. This is the durable asset
— it grows every cycle and is what open questions are answered from.

## Where cursor / the frontier fits

`cursor-agent` is the frontier reasoner here (extraction; and, on a solver failure,
writing a new connector — same gate as every other connector: self-test before it can
mint gold). The loop surfaces the *demand*; the frontier fills it; the KB records it.
