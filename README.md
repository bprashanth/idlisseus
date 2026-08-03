# Idli Insights

A chatbot that answers questions about one place, using that place's own data,
and shows you where every number came from.

It runs on a box in a room. No data leaves it.

## Why

Conservation and social sector teams tend to be small, and the evidence they need
is scattered. Some of it is in papers on Dryad and Zenodo. Some is in a CSV a
student made in 2018. Some is in a PDF of field forms nobody has opened since.
Answering a simple operational question, like where to put six camera traps this
season, means someone spends a week reading and joining things by hand.

A general purpose chatbot will answer that question in four seconds and sound
confident doing it. You have no way to tell whether it read anything real. For a
team about to spend a third of its annual budget on mitigation work, that is
worse than no answer.

So this is built the other way round. Every claim resolves to source rows. When
the data cannot support a recommendation, the answer says so and shows the
evidence anyway.

## Place based memory

The unit is a place. Not a document, and not a chat session.

A **site pack** holds everything known about one place: the datasets, the records,
the species and people and plots inside them, the geography, the provenance for
each row, and the digests that let you tell one version from another. Valparai is
the live one. It has 46,260 source linked records across 22 datasets.

The pack is memory in the ordinary sense. It persists between conversations, it is
versioned, and everyone working on that place shares it. Four things sit on top:

**The graph.** Everything in the pack and how it connects. Search any name, place,
dataset or measurement, expand its neighbourhood a few hops, and see which links
are recorded in a source and which were derived.

**Themes.** Questions repeat across users. The producer mines them, and each theme
collects the phrasings people actually use ("where should we restart roadkill
monitoring", "which road sections were dangerous for mammals"). An answered theme
carries a published field note: the short answer, a map, what to do now, what was
measured, the named estimator, and a plain language account of how it was tested.
A theme nobody can answer yet lists the evidence that is missing.

**Data streams.** The rail beside a conversation shows the datasets consulted for
the last answer, and updates with each question.

**Contributors.** The landing page draws each pack as a light. Inside it are the
people credited with the data, resolved from the DOIs the pack publishes. Hover
one and you get a name.

## What it will not do

These are enforced in code, with tests that fail if they stop holding.

- A place is never styled as recommended unless a declared test passed. A failed
  test keeps its evidence and loses its recommendation.
- Observations withheld to test a model are drawn differently from the ones used
  to fit it, using shape rather than colour, because they share an evidence class.
- A record with no count is reported as having no count. It never becomes a zero.
- Contributor names come from the DOI registries. If a source resolves to nobody,
  it contributes nobody. No placeholder people.
- Author prose is rendered as text. Nothing published into the reading view can
  execute.
- Where the producer publishes nothing, the screen shows less. No invented mined
  counts, no invented bylines, no invented basemap sources.

## How it is put together

Two repos, one contract.

**totalrecall** is the producer. It owns the data, the computation, the scientific
claims and the immutable result payloads. It decides what passed a test.

**This repo** is the consumer. It owns rendering, interaction and everything a
person touches. It renders what the producer supplies and never infers scientific
meaning from a field name.

They talk through versioned contracts (`idli-result/1`,
`idli-decision-map-catalog/1`, `idli-graph/1`) and a written exchange in
[`dss/integration/`](dss/integration/). The producer files proposals, the consumer
files responses saying what shipped and what it refused. Requests go the other way
when the UI needs something the contract does not carry yet. That paper trail is
worth reading if you want to know why the UI is shaped the way it is.

Contract fixtures live in `chatbots/odysseus/static/contracts/fixtures/`, payloads
included, so `static/visual-lab.html` renders every case with no backend running.

## Running it

```bash
docker start vllm-qwen35
cd chatbots/odysseus && docker compose up -d
```

[`docs/running.md`](docs/running.md) has ports, model switching, site packs, health
checks, and the failure mode that looks like a hang.

## Repo layout

```
chatbots/odysseus/    the UI. static/js/visual/ is where the interesting parts are
dss/                  contracts, site pack deployment, the producer exchange
models/               per model configs, run scripts, systemd units
agents/               agent harnesses, Hermes token proxy
benchmarks/           seven rounds of benchmarks, plus semantic_broker
docs/                 running, access, architecture, setup
ds4/                  ds4 inference engine source, its own repo, gitignored here
```

Weights, KV cache, venvs, credentials and downloaded corpora are gitignored.
[`REPLICATION.md`](REPLICATION.md) lists what to fetch to rebuild from a clone.

## Docs

| Doc | What is in it |
|-----|---------------|
| [`docs/running.md`](docs/running.md) | Start, stop, models, ports, health checks |
| [`docs/access.md`](docs/access.md) | Adding a teammate, network flow, cloudflared |
| [`chatbots/index.md`](chatbots/index.md) | The UI in detail: shell, themes, decision maps, validation treatment |
| [`dss/SITE_PACK_DEPLOYMENT.md`](dss/SITE_PACK_DEPLOYMENT.md) | Site pack and launcher contracts |
| [`dss/integration/`](dss/integration/) | Proposals and responses between producer and consumer |
| [`docs/IDLI_INSIGHT_MODEL_COMPOSITION.md`](docs/IDLI_INSIGHT_MODEL_COMPOSITION.md) | Request path and model responsibilities |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System architecture and inventory |
| [`models/index.md`](models/index.md) | Every model, memory, start and stop |
| [`benchmarks/index.md`](benchmarks/index.md) | Benchmark results and takeaways |
| [`REPLICATION.md`](REPLICATION.md) | What to download to reproduce this |
