# Operating philosophy: why the system behaves as it does

The ideology behind the connectors, the transfer algebra, and the overnight benchmark. This is the
part that's easy to lose in code; keep it explicit.

## 1. Data-starvation is the default, not the exception
A real restoration site has almost no data *at the site*. We designed for that, not against it. Every
answer is one of: **transfer** (borrow analog data, gated), **ingest** (go get more), or **expand**
(bridge from what we have most of toward what we have least of). See `README.md` for the three moves.

## 2. Follow the data you HAVE to build a case for the data you NEED
The strongest move under scarcity: **anchor on the most abundant dataset for this AOI** (census it —
don't assume) and use it as a **bridge** to the question via known ecology, then **turn the gap into a
concrete, acquirable data request.**
- EBTL example: birds are abundant (136 eBird species) while plants are ~0. So a plant/invasive
  question routes **birds → frugivore dispersers → invasive-spread signal**, honestly labelled a
  correlate, plus "please survey the plants / log habitat / deploy acoustic sensors."
- This is *not* hand-waving: it's "here's the real signal we can see, here's exactly what would confirm
  it." Every honest gap becomes a **specific ask** (Pixxel hyperspectral, AudioMoth+BirdNET, eBird
  habitat logging, dung-beetle transects, community surveys). **Suggesting where more data helps is a
  first-class output, not a failure.**

## 3. Helpful-then-honest; never fabricate; never empty
- Give the **best gated estimate first**, then the honest limits. A modelled number that names its
  method + uncertainty beats both a refusal and a confident fabrication.
- **Never manufacture data.** Nothing is important enough. If a source is missing, say so and ask.
- **Never return empty.** A floundering non-answer loses to a plain chatbot (we lost exactly one
  benchmark question this way before fixing it). Retry once smaller, then answer from data-on-hand +
  established ecology + the ask.
- **Match the method to the question.** Don't force species/RF/SDM onto human-use questions (firewood,
  grazing) — those need the observable proxy + community-data ask.

## 4. Provenance over assertion — nothing hallucinated, everything overridable
Every derived AOI, source, and number carries its **lineage**: how it was derived, a **citation or
"VERIFIED n rows,"** an **approximate/phantom flag** when soft, and it is **overridable**. The corridor
is cited to the WII/WTI atlas + a data-density rule, not invented; a widened box is never presented
without its story. The `/why` provenance view exists to make this legible to the user (data → gate →
model → result).

## 5. When something isn't clear, run an experiment (don't guess)
This is the core method. Whenever a design choice is uncertain, we **build the smallest experiment that
decides it**, with an honest metric — rather than argue from intuition.
- **Cards vs LLM-search:** we didn't assume; we ran a retrieval benchmark. Finding: data **cards +
  embeddings** beat one-prompt LLM-over-cards, which *degrades as the corpus grows*. Cards won on merit.
- **Does transfer hold?** we built the **gate** and tested it (dry-Deccan Lantana → EBTL transfers;
  wet-Valparai → EBTL refuses) before trusting any modelled number.
- **Are we actually better than a frontier model?** the measure of success is a **head-to-head vs a
  frontier CLI** on unbiased, curriculum-generated questions — and we mine every loss for the fix.
- **Curriculum to expand data search:** the Controller/Proposer generate a widening question set that
  forces the system to reach for new data/angles, which is how we discover missing connectors.

## 6. The loop, restated
`census the AOI → transfer what's analog + ingest what's crawlable + bridge from abundant to scarce →
answer honestly with provenance → request the rest → re-run the curriculum/benchmark → fix the weakest
dimension.` Repeat as data arrives. The system's job is to **move a user from guesswork to data +
systemic analysis**, and to make the case for the data they don't yet have.
