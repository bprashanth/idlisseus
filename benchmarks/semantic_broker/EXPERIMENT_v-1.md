# Experiment v-1 — "Hermes runs wild" (the prelude)

> Before we build any broker, cards, or embeddings: can raw Hermes (on 122B)
> find and use the right data by itself? And **where does that break?** The
> break-point defines when a broker starts earning its keep.

This is the prelude to everything in [`PLAN.md`](PLAN.md). It sets the baseline
the broker must beat, and — more importantly — produces a **scale timeline**:

```
corpus size  →  approach
small        →  raw Hermes (no broker)          ← v-1 establishes this
~threshold   →  Hermes + dataset cards          ← v0/v1 test this
larger       →  cards + vector embeddings
```

## What v-1 tests

**Q1 — Does raw Hermes find the right assets at all?**
Give Hermes (122B) the small raw asset pile in [`assets/`](assets/) + the live
connectors + one benchmark question. No cards, no index, no embeddings. Does it,
on its own, open the right papers/files, call the right connector, and assemble a
sane answer?

**Q2 — Where does "wild" break?**
Grow the corpus (more assets, more heterogeneity, larger files) until the naive
strategy — *read everything / write your own Earth Engine script / join the raw
excels* — degrades or fails. Failure modes to watch: context blowout, wrong-file
selection, giving up and hallucinating (the failure we saw in the Odisha run),
or runaway runtime. That failure point is the **card/embedding threshold**.

## Non-negotiable principle (applies to the whole suite)

**No coercion.** Neither Hermes here, nor the card generators in v0, get
hand-tuning from Claude. Hermes gets the raw assets + connectors + the question
and a generic instruction — nothing that pre-labels which file answers which
question. A wrong pick or a hallucination is a **recorded finding**, not
something we prompt-engineer away. We are measuring the model's *unassisted*
competence, because in production nobody hand-holds it over each contributed
dataset.

## Setup

- **Agent:** Hermes, backed by **122B** (`vllm-qwen35`, `172.17.0.1:8001`).
- **Runner:** [`run_v-1.sh "<question>"`](run_v-1.sh) — mounts the corpus at
  `/opt/data/corpus:ro` (inside the agent's workspace so it looks there naturally),
  wires Earth Engine, and issues one question with a no-coercion prompt.
- **Connectors:** see [`CONNECTORS.md`](CONNECTORS.md). **Earth Engine is wired
  and verified end-to-end from inside the container** (FIRMS / WorldCover / SRTM,
  project `plantwars`). GBIF + WDPA are public, to wire. Distractor connectors
  (ocean SST, air quality) are advertised too, to test discrimination.

### Corpus inventory (in `assets/` → mounted at `/opt/data/corpus`, gitignored)

**Gold assets:**
| Path | What | Real region |
|------|------|-------------|
| `2018_Prasad_lantana_eradication.pdf` | lantana **removal** experiment, cut/uproot/control, 96 plots | Mudumalai |
| `2024_Osuri_restoration_beyond_degraded.pdf` | restoration literature (canopy/native context) | Western Ghats |
| `zenodo_10426971_longterm_census/` | long-term woody-stem census, 2 plots 2017–22 (CSVs+README) | Anamalai/Valparai |
| `zenodo_10630501_seedling_survival/` | restoration seedling **survival** by site/canopy (CSVs+README) | Valparai/Anamalai |

**Distractors (plausible, wrong):**
| Path | Trap type |
|------|-----------|
| `distractors/distractor_westernghats_birds_community.pdf` | right region, **wrong topic** (birds) |
| `distractors/zenodo_13340613_sakleshpura_mammals_WRONGREGION/` | species data, **wrong sub-region** (central WG, not AOI) |

## v-1 question set

Run each via `run_v-1.sh`. For each: what a good answer pulls together, the right
connector(s), and the **trap** — the distractor most likely to waste its time.
Success = opens the gold assets, calls the right connector for the AOI, avoids
the trap, and doesn't loop/probe wrong connectors.

| # | Question | Gold assets | Gold connector(s) | Trap (time-waster) |
|---|----------|-------------|-------------------|--------------------|
| 1 | Which restoration sites are most exposed to fire risk? | census / survival (site coords) | EE FIRMS + WorldCover | reading bird/mammal PDFs; querying FIRMS globally instead of near plot coords |
| 2 | What does the evidence say about where/how to prioritise lantana removal? | Prasad removal paper | GBIF (lantana occurrence) | Sakleshpura mammals; over-searching the web for a "removal dataset" that isn't there |
| 3 | Are restored plots recovering native species? | census + survival + Osuri (what's "native") | GBIF (native ref, optional) | Sakleshpura mammals (species but wrong region/taxon); birds paper |
| 4 | Compare species/invasive records inside vs outside protected areas | (occurrence from census) | WDPA boundaries + GBIF | mammals wrong-region; treating WDPA attributes as if they were boundaries |
| 5 | Is fire risk higher in scrub or plantation land cover? | — (pure connector join) | EE FIRMS + WorldCover | opening any PDF at all; not clipping to the AOI |

**Scale step (Q2 of the experiment):** after the small-corpus run, grow `/corpus`
with more distractor papers/datasets and rerun, watching for the break-point
(context blowout, wrong-file selection, hallucination, runaway time).

## Procedure

1. Drop the raw assets in `assets/` and mount them where Hermes can read them.
2. Ensure connectors are reachable from the Hermes container.
3. For each benchmark question, run Hermes 122B with a generic prompt (question +
   "here are some files and these connectors; answer it"). No hints about which
   file is relevant.
4. Capture the full tool trace from `~/.hermes/state.db` (this is where Hermes's
   auditability pays off — exact code per `execute_code` call).
5. Score which assets it actually opened/used vs the gold mapping; note whether
   the connector calls were correct; note any hallucinated / fabricated numbers.
6. Repeat with a **grown corpus** (add distractor papers/files) until it breaks.

## What we measure

- **Retrieval-by-agent:** did Hermes open the gold assets for each question
  (Recall against gold), and did it avoid distractors?
- **Connector correctness:** right EE/FIRMS/WDPA call for the AOI?
- **Answer integrity:** grounded in the opened files, or fabricated (audit the
  code, per the Odisha lesson)?
- **Break-point:** corpus size / heterogeneity at which the above degrades —
  reported as the raw→cards threshold.

## Deliverable

A short report with (a) the raw-Hermes baseline per question, (b) the observed
break-point, and (c) the resulting scale ladder ("raw Hermes holds to ~X; beyond
that, cards; beyond that, embeddings"). This baseline is what v0/v1 must improve.

## Then what

- **v0 — card quality, no coercion.** Feed the same raw assets to **cursor** and
  **122B** as card generators; compare whether each *naturally* produces a card
  that lands the asset in the right conceptual place (e.g. the Prasad paper's
  card is about lantana removal, not birds). Eyeball + retrieval check.
- **v1+ — the full retrieval benchmark** ([`PLAN.md`](PLAN.md)): fixed embedder,
  card recipes (baseline / +questions / +tags), distractors, both retrieval
  modes, Recall@5.

## Results

### Q5 — "Is wildfire risk higher in scrub or plantation land cover?" (2026-07-02, 122B)

**Plumbing: works.** The agent ran real Earth Engine analysis end-to-end —
MODIS/FIRMS fire × ESA WorldCover land cover, server-side reductions over the
Nilgiris–Anamalai AOI — and produced a quantified answer (~898 km² "scrub",
claimed ~470× more fire-prone than "plantation"). It was genuinely self-critical
(caught an implausible fire density, wrong band names, mask-logic bugs) and
**correctly used no corpus files** for this pure-connector question — it did not
fall for the distractor papers. ~18 min wall, ~20 execute_code calls (several EE
reductions 50–260 s each).

**Semantics: wrong — and this is the finding.** The agent invented the WorldCover
class legend: it called **class 50 "Shrubland"** and used **classes 70+90 as a
"plantation proxy."** Actual ESA WorldCover v200: 50 = *Built-up*, 70 = *Snow/ice*,
90 = *Herbaceous wetland*; Shrubland is **20**, Cropland **40**, and there is **no
plantation class at all**. So the whole quantification rests on the wrong classes,
delivered with only mild hedging.

**Takeaway (the motivation for the broker):** raw Hermes can *reach and join* the
data — the connector layer is sufficient — but without curated dataset metadata
(e.g. a card carrying the correct class legend, or telling it plantation isn't a
WorldCover class and pointing at the restoration/land-use datasets instead) it
makes semantic errors that corrupt the insight. This is precisely the boundary
v-1 set out to locate: the plumbing is not the bottleneck; the *semantics* are.

**Connector-provisioning gotchas fixed along the way** (setup, not results):
ee/pymupdf must be preinstalled in the image (import-name≠pip-name); EE creds must
sit at the sandbox HOME `/opt/data/home/.config/...`; `~/.hermes` must be uid-10000
owned. See `CONNECTORS.md`.

### Q1 — "Which restoration sites are most exposed to fire risk?" (2026-07-02, 122B)

**Corpus grounding: excellent.** It found and used the *right* datasets with zero
hand-holding — `ncf_zenodo/10077040/01_sites.csv` (27 fragments with coordinates
+ habitat descriptions) and `03_pcqlocations.csv` (plot-level coords) — extracted
~20 real restoration sites in the AOI (Andiparai, Iyerpadi-Top, Korangamudi,
Puduthottam, Manamboly, Karian-Shola, Varagaliar…), and interpreted the habitat
text to classify them (fragments / coffee / cardamom). It did **not** get lost in
the bird/mammal distractors. The data-*finding* half worked perfectly at a
49-record corpus.

**Connector analysis: did not complete.** After ~25 min and ~25 EE calls it could
not get the per-site fire aggregation working (FIRMS/VIIRS access errors, MODIS
`reduceRegion` returning unexpected structures). It **gave up on the quantitative
fire join and fell back to a qualitative ranking** based on habitat fragmentation
/ isolation (fragments surrounded by tea estates = higher risk) — domain
reasoning, not fire data.

**Honesty: high.** Unlike the Odisha run (confident fabrication) and unlike Q5
(confident *wrong* class codes), here it clearly labelled the fire analysis as
incomplete, disclosed that the ranking is a habitat proxy, and recommended
alternatives (GEE JS API, FIRMS HTTP). Graceful degradation with disclosure.

### Q5 vs Q1 — the core v-1 finding

- **Data-finding is not the bottleneck.** In both runs raw Hermes surfaced the
  right data (Q1 found the correct site datasets; Q5 correctly used none) and
  avoided distractors — at a 49-record corpus. So the thing the broker fixes
  (finding) isn't where raw Hermes breaks *at this scale*.
- **The analysis/connector-execution layer is the bottleneck.** Q5 finished but
  with wrong WorldCover semantics; Q1 couldn't finish the multi-site EE
  aggregation at all and degraded to qualitative reasoning. The failures are in
  *executing the join correctly* (band names, class legends, per-site reducers),
  not in locating data.
- **Implication for the roadmap.** The broker (cards/embeddings) earns its keep
  when the corpus grows past what "read everything" can scan — that's the Q2/scale
  question, still to run. But even with perfect finding, an **insights/analysis
  layer** is needed: tested connector recipes/skills carrying correct band names,
  class legends, and AOI-clipping patterns. This empirically confirms the hunch in
  `NOTES.md` that the insights layer needs its own scaffolding, and that NOTES'
  own idea of "tried and tested skills" for connectors is the right direction.
