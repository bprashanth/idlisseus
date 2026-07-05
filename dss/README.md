# DSS — the decision-support / data layer (meta layer above the agent)

This directory documents the **system around** the Hermes agent + chatbot: how we take a new
user's Area of Interest (AOI), build up its data, and decide how to answer questions when the data
is thin. It is deliberately OUTSIDE `benchmarks/` — the benchmark measures whether it works; this
plans how it works, and how to replicate it for the next AOI/user.

## The core assumption: **most AOIs are data-starved**

A field NGO's restoration site (like Elephants by the Lake, EBTL) has almost no georeferenced
data *at the site* — we found **0 GBIF Lantana/elephant records inside EBTL's 70-acre bbox**, while
the surrounding region and the wider literature have some. So the whole system is built around
scarcity. Given a question about a data-poor AOI, there are only **three moves**:

1. **TRANSFER** — borrow analog/nearby data and carry it in *honestly* (gate → SDM/RF, MESS-gated),
   refusing when the analogy doesn't hold.
2. **INGEST** — go get new data: crawl papers/datasets, add authenticated sources, parse messy files.
3. **EXPAND along the axis of maximum data reliance** — use whatever data type we have MOST of
   (e.g. birds at EBTL: 136 eBird species) as a *bridge*, via known ecology, toward what we have
   LEAST of (e.g. plants/invasives), and turn the gap into a concrete data request.

Every answer is **modelled/estimated with honest limits, never fabricated**, and every gap becomes
a **specific data ask** (survey X, deploy Y sensor, get Z imagery).

## Onboarding a new AOI (the loop, per new user/site)
`get AOI → characterize it → census its data → ingest a corpus → index it → per question: route
(transfer/bridge/answer) → surface data requests.` Full step-by-step, grounded in exactly what we
did for EBTL: **[AOI_ONBOARDING.md](AOI_ONBOARDING.md)**.

## The data strategies we employ (the toolbox)
Corpus crawl (community + author-graph + theme retargeting + authenticated sources) · paper search
& document embeddings/cards · the axis-of-maximum-data-reliance bridge · transfer & interpolate
algebra (gate/route/SDM/RF/MESS) · satellite & hyperspectral (AlphaEarth/EMIT/Pixxel) · requests
for data. Catalogued in **[DATA_STRATEGIES.md](DATA_STRATEGIES.md)**.

## Status / where the code lives
This is a planning layer; the working implementation is in `benchmarks/semantic_broker/connectors/`
(the connectors + skill) and `benchmarks/algebra/` (the crawl, discovery, transfer algebra, benchmark).
When we build the long-term productized system, these docs are the spec. Keep adding as we learn.
