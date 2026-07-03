# What we're building — from a conservation question to an insight

> A plain-language strategy doc. (Not mounted into the agent — this is for us.)

## The goal in one sentence

Let someone ask a real conservation question about a place and get a trustworthy
answer quickly — without them having to hunt for data, clean spreadsheets, or
write GIS code themselves.

## The kind of question we care about

Not one-shot lookups ("what's the elevation here?"). We care about the harder
questions that normally take an analyst days:

- "Which of our restoration sites are most at risk from fire?"
- "Where should we focus lantana removal — where is it spreading near fields?"
- "Are our restored plots actually recovering native species?"

Answering these means **stitching several datasets together** — a spreadsheet of
plots, a fire map, a land-cover map, species records — often across both **space**
(where) and **time** (when). Today the person asking does all that stitching by
hand. We want the machine to do it: **idea → insight**, fast.

## What data we work with

We group data into buckets: **invasives, fire, land cover, restoration,
biodiversity, governance.** So far it comes from three places:

1. **CSV/Excel files attached to conservation papers** on Zenodo (e.g. NCF's
   Western Ghats datasets) — this has been our main source.
2. **CSV/Excel files people contribute** directly.
3. **Map layers** — satellite products in Google Earth Engine, species records in
   GBIF, protected areas in WDPA.

Everything is scoped to an **area of interest (AOI)** — for us, the
Nilgiris–Anamalai region.

## What we learned in the v-1 experiment (the important bit)

We handed the agent (Hermes, on the 122B model) the raw data + the map tools and
asked the hard questions. The result was clear and a little surprising:

- **It IS good at finding the right dataset.** It opened the correct plot
  spreadsheet, pulled out the coordinates, and ignored the irrelevant papers.
  *Finding data is not the problem.*
- **It is NOT good at using the data.** It either produced a confident wrong
  answer, or struggled for a long time and gave up.

The struggle came from three specific places:

- **a. Naming.** It doesn't know the exact names *inside* a map layer — the
  dataset ID, the band name, the class codes. It guesses, and guesses wrong (it
  called land-cover class 50 "Shrubland"; class 50 is actually "Built-up"). A
  legend isn't something you can reason out — you either know it or you don't.
- **b. Setup.** Logging in to the data platform, using the right Python, getting
  the credentials in the right place — fiddly plumbing it kept tripping over.
- **c. The computation.** The actual spatial operation — "count the fires within
  5 km of each site" — has to be written against a finicky map API. It spent 25
  minutes writing slightly-wrong versions and never got a clean answer.

## Why this is hard for a language model specifically

LLMs are strong at language, planning, reading a paper, and writing ordinary data
code (pandas). But three things fight them here:

- They **can't reliably recall exact "magic strings"** (a band name, a class
  code). They produce something plausible — and they don't know when it's wrong.
- They **can't hold a fiddly, stateful API in their head** correctly, so they
  write spatial computations that are subtly broken.
- They **stumble on deterministic setup** (auth, environment) that has exactly
  one right answer and no room to improvise.

A plain function has none of these problems: it doesn't *guess* the legend — it
*knows* it.

## The idea: boil questions down to a few building blocks

Here's the bet. Most map questions, underneath, are the **same handful of
operations combined**. If we implement those operations correctly once, the LLM's
job shrinks to *choosing and chaining* them — which it's good at.

The recurring shape is:

> **get some points → look up or summarise something about them → group / rank.**

The building blocks, in plain words (with a motivating question each):

| Block | What it does | Motivating question |
|-------|--------------|---------------------|
| **FIND** | get a set of points | "where has lantana been recorded?" |
| **LOOK UP** | read a map value at each point | "what land cover is each lantana point on?" |
| **SUMMARISE IN AN AREA** | aggregate a map over a circle/region | "how much fire within 5 km of each site?" |
| **RELATE** | inside a boundary? distance to nearest? | "which lantana is inside a reserve / near a field?" |
| **GROUP / RANK** | count and sort | done by the LLM in pandas |

Those five already answer a lot: exposure, co-occurrence, presence-in-a-category,
proximity. This is the "algebra" we're trying to pin down — a small set of
primitives that composes into most questions.

## Connector vs. function (two different things)

- A **connector** is the piece that can *talk* to a source — handle the
  login/credentials and open a session (e.g. the bit that authenticates to Earth
  Engine).
- A **function** *understands a specific layer* and its documentation — it knows
  WorldCover's band is "Map", that class 50 is Built-up, that fire = FireMask ≥ 7.
  This is where the borrowed expertise lives.

You need **both**: the connector to reach the data, the function to interpret it
correctly. The functions are what stop the guessing. (So far each of our
connectors bundles both — auth *and* the per-layer functions.)

## Two kinds of data source

**Known sources** — we already know where the data is:

- We have the **data dump** (the CSV/Excel): just give it to the agent. It reads
  it, extracts points, and goes. No function needed — this is where Hermes can
  "go wild."
- We only have a **platform link** (Earth Engine, GBIF, WDPA): the agent can't
  safely query it raw. Someone must write the **connector + functions first**.
  Until that function exists, the layer isn't usable reliably.

**Unknown sources** — we don't yet know where (or whether) data exists:

- Handled by **nightly scrapes** or **runtime web searches**.
- If a search finds a file it can **download**, it becomes a known *dump* — usable
  immediately.
- If it finds a new **platform layer** (say a new Earth Engine dataset), that
  *can't be used accurately until we submit it for ingestion* — i.e. write a
  function that owns its naming and operations. **Discovery alone isn't enough.**

## The buckets it can't do yet (where the building blocks run out)

The five blocks cover "where is X relative to map Y, summarised." They don't cover:

- **Over time** — "are plots greening up year on year?" needs a *trend*, not a
  single value. (This is the first one we'll likely need.)
- **Networks / corridors** — "are these fragments connected?" needs *paths* over a
  landscape, not point lookups.
- **Shape / fragmentation** — "how broken-up is this forest?" measures the
  *pattern* of a whole area.
- **Prediction** — "where will lantana spread next?" builds a *new map* from a
  model.
- **Cause** — "did our removal actually cause recovery?" is a *study design*, not
  a map operation. This one sits *above* everything else.

These are the honest edges: a few are new building blocks to add later; "cause"
is a separate layer entirely.

## The open question: functions vs. richer data cards

There are two ways to give the agent what it's missing. We should be deliberate:

**Option A — write functions (what we've done so far).** Pre-build tested code
that owns each layer's names and operations.
- *Good:* correct, deterministic, no guessing, reusable across questions.
- *Costly:* a human writes a function per layer/operation *ahead of time*; a
  brand-new layer is unusable until someone does.

**Option B — richer data cards.** Instead of code, the card *describes* the layer
in structured text — band names, the full legend, valid operations, units,
gotchas — and the LLM writes the query at run time from that description.
- *Good:* no code per layer, just metadata; a new layer becomes usable by writing
  a card; keeps the LLM flexible and covers far more layers cheaply.
- *Risky:* the LLM still has to write correct map code from the description — the
  exact step it failed at in v-1. Cards fix the *naming* problem (a) but not the
  *API/setup fumbling* (b, c).

**A likely answer: both, split by who's good at what.** Put the **semantics** in
the card (what the layer is, its legend, what it can answer) so the agent — or the
broker's search — can *discover and pick* the right layer. Keep a **function** for
the operations the LLM can't reliably execute (the spatial reductions, the auth).
The card is the index and the label; the function is the muscle. This also gives a
clean path for unknown sources: discovery writes a **card**; if the operation is
hard, that card **graduates into a function**.

---

*Related: [`CONNECTORS_DESIGN.md`](CONNECTORS_DESIGN.md) is the technical version
of the building blocks; [`connectors/PHILOSOPHY.md`](connectors/PHILOSOPHY.md) is
how to build one; [`EXPERIMENT_v-1.md`](EXPERIMENT_v-1.md) is the experiment this
all came from.*
