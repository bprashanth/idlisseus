# The transfer algebra — how we turn scarce data into honest answers

**Plain-language backbone of the EBTL data broker. Read this before touching `predict`.**
Written the way we'd explain it at a whiteboard — no jargon. The point of the whole
system is to answer a field worker's (Varun's) real question about EBTL using whatever
data exists, **even when that data is somewhere else**, and to be honest about when we
can't.

## The one loop everything reduces to

Every question becomes two sub-questions:

1. **How do I get points?** — scan the connectors (GBIF occurrence, paper_data, camera
   traps, landcover, fire, …) and gather the relevant labelled points, from anywhere.
2. **What algebra turns those points into an answer HERE (at EBTL)?** — decide whether
   and how it's valid to carry findings from where the points *are* to where the
   question *is*, run it, and report as a **suggestion with its limits** — never as
   measured fact.

Step 2 is the hard, interesting part. It is: **question × gate → method.**

## The gate = what can LIMIT a transfer

A **gate is a traffic light, not a model.** Before reusing far-away data at EBTL it looks
at the points we have and the place we care about and asks: *can I honestly carry this
over, and by which route?* It outputs a verdict, not a number.

A transfer is only valid if EBTL is "close" to where the data came from — but **"close"
has several independent meanings**, and each is its own gate. Today we have three, and
the design is meant to grow:

| # | Transfer gate — "is EBTL similar in…" | measured by | crosses ecoregions? |
|---|---|---|---|
| 1 | **…how it looks from space** (fine appearance/structure) | AlphaEarth 64-d fingerprint cosine (nearest-neighbour); **hyperspectral** can sharpen this | no — local |
| 2 | **…broad biogeographic zone** | the `ecoregion` connector (a coarse category — the blunt-pencil version of #1) | n/a (it *is* the zone) |
| 3 | **…climate** (rainfall, temperature, seasonality) | WorldClim bioclim envelope (MESS) | yes, within the trained climate range |
| … | **future: …human community / land-use** (e.g. same agroforestry system) | TBD (a land-use / community connector) | — |

These are **not the same thing**, and that's the whole value:
- **Cosine (look-alike)** is a high-resolution photo comparison: is this exact 10 m patch
  of EBTL like a patch where we have data?
- **Ecoregion** is a coarse category stamped on a whole region — a rough stand-in for #1.
- **Climate envelope** ignores what the land looks like and asks only whether EBTL's
  weather sits inside the range of climates our points came from.

## Agreement is the signal

We run whichever gates/methods apply and compare:
- **They agree** → a *strong* reason to trust the transfer, and a strong reason to go
  collect a little more data to confirm (high-value spot).
- **They disagree** → a *strong* reason to stop and understand *why* — which usually means
  the framework or a model needs improving. Disagreement is information, not noise.

## The three transfer methods (what the gate routes you to)

| verdict | method | when | resolution |
|---|---|---|---|
| `overlap` | just report the points | we already have data *in* EBTL | exact |
| `transfer_rf` | RF on satellite fingerprints (AlphaEarth; later + hyperspectral) | EBTL **looks like** the donor area (gate #1 green) | 10 m, fine |
| `sdm_climate` | species-suitability from WorldClim climate | appearance differs but **climate matches** (gate #3 green) | ~1 km, coarse |
| `refuse` | don't model — recommend collecting local data | no gate is green | — |

Everything downstream is labelled **modelled/suggested + caveat**.

## `route` = the situation classifier

`route` ties it together. Given a question and the gathered points, it runs the gates and
returns not just a method but **which of three situations we're in**:

1. **Answerable now** — a gate is green (often several agree) → run the method(s), return
   the suggestion + caveat.
2. **"You need more data here"** — every gate is red (EBTL is unlike our donor points in
   every sense) → the honest answer is a **data gap**: here's what to go measure.
3. **"We need better models / understanding here"** — gates/methods are green but
   **disagree** → a **model gap**: surface the conflict instead of papering over it.

That three-way outcome is the real product. A context-free CLI always gives you (1) even
when the truth is (2) or (3); our edge is telling them apart honestly.

## Why this is fast enough (the RF-every-time worry)

The RF itself is **not** the slow part — a random forest on a few hundred–thousand points
trains in milliseconds. What costs seconds is **fetching the satellite fingerprints**
(asking Earth Engine to sample AlphaEarth/WorldClim at the points and shipping them back).

So the design separates the two:
- **Annotate once, cache.** For a set of points, sample the 64 AlphaEarth + 19 WorldClim
  numbers a single time and store them next to the points (a fixed fingerprint per point
  per year). This is the only Earth-Engine round-trip.
- **Then all the algebra is local Python.** The gate (cosine + MESS) is pure numpy;
  the RF and the climate SDM are `sklearn.RandomForestClassifier` on the cached vectors —
  both run in milliseconds, per question, offline. Earth Engine is only needed again if we
  want to paint a full suitability *map* over every pixel (a server-side raster job).

So `route` can run per question without lag: cached fingerprints + numpy/sklearn.

## Where the code lives
- `../semantic_broker/connectors/predict.py` — `gate`, `transfer`, `presence`, `sdm`, (soon) `route`.
- `ebtl/pull_occurrence.py` — step 1 for EBTL (GBIF + camera-trap → labelled points).
- Hermes learns steps 1+2 via the **skill** (still to write) so it does this itself.
