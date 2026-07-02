# Semantic Data Broker — Experiment Plan

> Refined, decided design derived from [`NOTES.md`](NOTES.md). NOTES.md is the
> brain-dump; this file is what we actually run. Update this file when a
> decision changes.

## What we are actually measuring

A retrieval-evaluation (IR) benchmark. Given a fixed set of conservation
questions and a fixed corpus of dataset "cards", measure whether the broker
surfaces the *right* datasets for each question. The card recipes we test map
onto known IR techniques (document expansion / doc2query, controlled-vocabulary
expansion), so we are tuning a known-good method, not betting on something
exotic.

**Primary question, in order:**
1. **Do cards preserve enough signal?** — give the agent *all* cards in context,
   no retrieval, ask it to select. (Oracle baseline, Experiment 0.)
2. **Does semantic retrieval scale-select correctly?** — introduce a vector
   index + distractors and see if top-k recovers what the oracle could see.

If (1) fails, no retrieval layer saves us — the card is losing information.
If (1) passes and (2) fails, the problem is retrieval, not cards.

**Non-goals (unchanged from NOTES):** we do not judge Hermes's final analysis
quality, and we do not try to ingest all conservation data. This is about
*finding* the right data.

## Experiment ladder

The broker's value is defined by where the *simpler* approach breaks. So we
climb, not jump:

- **v-1 — Hermes runs wild** ([`EXPERIMENT_v-1.md`](EXPERIMENT_v-1.md)): no
  broker at all. Raw assets + connectors + 122B. Establishes the baseline and
  the corpus size at which "read everything / write your own GEE script / join
  the excels" breaks. That break-point is the card/embedding threshold.
- **v0 — card quality (no coercion):** feed the same raw assets to **cursor**
  and **122B** as generators; does each *naturally* land the asset in the right
  conceptual place? (Prasad paper → a lantana-removal card, not a birds card.)
- **v1+ — full retrieval benchmark:** everything below (fixed embedder, recipes,
  distractors, both retrieval modes, Recall@5).

## No coercion (methodological rule)

Neither Hermes (v-1) nor the card generators (v0+) get hand-tuning from Claude.
They receive the raw asset + a generic prompt — nothing pre-labelling which asset
answers which question. A wrong pick, a bad card, or a hallucination is a
**recorded finding**, not a bug we prompt-engineer away. We measure *unassisted*
competence, because production has no one hand-holding the model per dataset.

## Roles — keep these separate

These were conflated in NOTES; they are four distinct components.

| Role | What it does | Candidates on this box |
|------|--------------|------------------------|
| **Card generator** | Writes the card *text* from a raw dataset | cursor `agent`, `qwen3.5-2b`, `seed-oss-36b`, `qwen80b`, **qwen3.5-122b** (current primary, B7), ds4 |
| **Embedder** | Turns card text → vector for cosine search | **install** `sentence-transformers` + one fixed model (`bge-large-en-v1.5` recommended) |
| **Retriever/broker** | Cosine top-k over the vector file; returns cards + connector hints | python script we write |
| **Agent (Hermes)** | Consumes retrieved cards, fetches the data, answers | Hermes container (unchanged) |

**Fixed vs varied:** hold the **embedder fixed** across every run (it is what
actually does retrieval; the card is just its input). Vary the **card
generator** and the **card recipe**. A "known-good embedder" means the embedding
model — not cursor. Cursor is a card generator.

### Model note (needs your pick)

NOTES said "cursor cli, qwen 2.5 coder 14b, qwen 122b". Reality on this box:
the "122b" is real (`qwen3.5-122b`, the current primary from B7). The gap is the
**14b** — there is no mid-size coder. Proposed substitution for the generator
comparison:
- **small generator:** `qwen3.5-2b` (sidekick) — or `seed-oss-36b` if 2b is too weak *(your pick)*
- **large generator:** `qwen3.5-122b` (primary), with `qwen80b` as alt
- **reference generator:** cursor `agent`

Card generation is offline/nightly batch (a few hundred tokens per card), so
running all three is cheap — this is **not** the ds4/80B coexistence problem.
Prediction worth testing: card quality saturates fast (cards are short
structured text), so 2b may retrieve ~as well as 80b — a strong efficiency
result for the nightly loop.

## Corpus — the distractors ARE the experiment

With only 7 datasets, top-5 returns ~70% of the corpus and no recipe can be
distinguished from another. We need enough distractors that top-k is actually
selective.

- **Gold set:** 7 datasets (A1–A7 from NOTES), scoped to the S. India AOI
  (Valparai / Gudalur / Kotagiri / Nilgiris / Annamalai).
- **Distractors:** **25–40** plausible-but-wrong conservation datasets — soil
  carbon, hydrology, urban land use, marine, other geographies, non-AOI fire,
  etc. Enough that a wrong retrieval is a real error.

Corpus total target: ~35–47 cards.

## Card schema (v1)

File-based to start (one JSON per card + a flat vector file); DB later. Every
card carries a stable id + provenance from day 1 — this is the **lineage**
substrate and the grounding that distinguishes a *retrieved* dataset from
hallucinated numbers.

```jsonc
{
  "id": "A2-firms-fire-nilgiris",        // stable, human-readable
  "type": "asset" | "connector",         // static file vs live API
  "title": "...",
  "tags": ["wildfire", "disturbance"],
  "source_url": "https://zenodo.org/...",// where it came from
  "summary": "...",
  "connector": "earthengine" | "firms" | null,
  "access_hint": "how Hermes fetches it (cli/endpoint/param)",
  "provenance": {
    "ingested_at": "2026-07-02",
    "generator_model": "qwen80b",        // which model wrote this card
    "recipe": "baseline|questions|tags", // which recipe version
    "source_files": ["restoration_plots.xlsx"]
  }
  // recipe-dependent fields:
  // "possible_questions": [...]  (recipe 2)
  // "conservation_tags": [...]   (recipe 3)
}
```

### Card `type`: connector vs asset

- **asset** — static data the broker stores/points to: Zenodo excels, codebooks,
  experiment writeups, zip files. Card summarizes contents; `access_hint` is a
  download URL / file path.
- **connector** — a live API capability, not stored data: FIRMS fire points, ESA
  WorldCover / Earth Engine layers, Protected Planet boundaries. Card is a
  *capability* card ("gives you active fire points; call via `earthengine`
  like X"). Hermes runs the connector itself.

Confirmed working connectors: **Earth Engine** (authenticated, project
`plantwars`, tested with a real SRTM query). FIRMS and Protected Planet are
public APIs to wire next.

## Card recipes (the variable we tune)

1. **Baseline** — title, tags, source, summary, connector.
2. **+ possible questions** — append NL questions the dataset can answer
   (document expansion).
3. **+ conservation tags** — controlled ecological vocabulary (invasion
   pressure, fuel load, fire exposure, native recruitment, edge effect,
   canopy cover, fragmentation…) + geotags (state/site/district). Captures
   attributes the summary misses (e.g. a fire dataset that also carries
   lantana lat/lon).

Sequencing: **recipe comparison first** (one fixed generator + fixed embedder,
vary recipe → pick best recipe), **then generator comparison** on the winning
recipe. Clean the index between recipe runs.

## Retrieval: test both modes on every question

The join questions each need a *complementary set* (e.g. fire + restoration +
land cover). Plain top-k can pull 3 fire cards and 0 land-cover. Two possible
fixes — we test both, on every question, since calls are local and cheap:

- **Mode A — agent decomposes:** Hermes issues specific sub-queries ("fire near
  these coords", "land cover here"). Tests whether *Hermes* understands what to
  ask for.
- **Mode B — broker diversifies:** the broker returns a bucket-diversified /
  MMR top-k spread across data buckets. Tests whether the *broker* can cover the
  complementary set from one query.

Record both. The interesting failure modes live here.

## Benchmark questions (gold mapping)

From NOTES, may be revised after dataset search:

1. Which areas seem most exposed to forest fires near restoration sites? → A2, A5, A3
2. Where should we prioritize lantana removal? → A1, A6, A3
3. Are restored plots showing recovery in native species? → A5, A7, (+literature)
4. Compare invasive records in protected vs non-protected areas? → A1, A4
5. Is fire risk higher in scrub or plantation areas? → A2, A3

Each question also gets an **expected-reasoning** note (why each dataset, what
join is needed, what cannot be inferred) for the "explain your choice" step.

## Core experiment loop

1. Ingest the same corpus (gold + distractors).
2. Generate cards with recipe X, generator M.
3. Index cards with the fixed embedder.
4. Run the fixed question set — **both retrieval modes A and B**.
5. Retrieve top-5 per query.
6. Score vs gold.
7. Ask Hermes to explain its selection.
8. Record failure modes.
9. Write report.

Hold corpus + question set constant while changing the recipe/generator.

## Metrics

- **Primary: Recall@5** against the gold set per question (did we surface the
  complementary datasets?). Presence matters more than rank for a join.
- **Distractor intrusion:** which distractors appeared, at what rank (rank-1
  intrusion is the worst error).
- Keep the NOTES "+1 per required in top-5, penalty for rank-1 irrelevant" as a
  secondary readable score.

## Report format (per run)

```
Experiment name / marker recipe / generator model / embedder
Retrieval score (Recall@5, distractor intrusions)
Per question: retrieval (mode A & B) | reasoning | pass/fail
Recommended marker changes
```

## Open items / TODO (in order)

1. **Install embedder:** `sentence-transformers` + `bge-large-en-v1.5`; hold fixed.
2. **Find datasets:** confirm the 7 gold (Zenodo/GBIF/FIRMS/WorldCover/WDPA),
   scoped to the AOI. (Claude does this.)
3. **Build distractor pool:** 25–40 plausible-but-wrong cards.
4. **Finalize question set** + expected-reasoning notes.
5. **Wire connectors:** EE (done), FIRMS, Protected Planet.
6. **Write the broker script** (ingest → card → embed → flat vector file →
   cosine top-k, modes A & B).
7. Run Experiment 0 (oracle baseline), then recipe comparison, then generator
   comparison.
