# IDL-REQ-0004 — Themes, not maps

**Consumer → producer.** Additive. Does not replace TR-VIS-0008; it reframes
what the reader browses and lets an outside author's published work keep its
identity when this consumer renders it.

## Why

A reader arrives with a question, not with a wish to see "maps" — and the
questions repeat. The interesting unit is the **theme**: a recurring question
group mined from conversation history. A map is one *published answer* to it.

The answers increasingly come from outside this chatbot: data-jam participants
write their own mining scripts and publish through the totalrecall publisher.
Today the consumer flattens their work — it imposes its own basemap and layout,
so a published solution looks like a generic figure instead of that author's
piece of work. And the catalogue has no prose: `decision` and
`validation.method` are contract fields, not an explanation you can read.

## What is asked for

| Need | Shape |
|---|---|
| Themes as a leaderboard | `GET /v1/themes` — `theme_id`, question `title`, `questions[]`, `mined` (conversation count, first/last seen, mining run identity), `solutions[]` |
| Author credit + explanation | per solution: `author`, `published_at`, `writeup` (prose / restricted markdown) |
| The author's map survives | `presentation`: `basemap` (declared id or proxied template + attribution + max zoom), `theme` dark/light, optional `initial_view` |
| Reading view | `GET /v1/themes/{theme_id}` |
| Place a pack on a map | `capabilities.bounds` and/or `centroid` (+ optional `weight`) |

## Boundaries the consumer keeps either way

- **Tiles are proxied.** A declared basemap arrives as an id the consumer
  proxies; the browser never calls a third-party host (CSP + existing tile
  proxy). An unrecognised id degrades to the consumer default — it never fails
  the render.
- **Prose is text.** Write-ups render as text; embedded HTML or script is
  inert.
- **A failed test still loses its recommendation.** Nothing an author writes
  can turn a failed validation into a recommendation — the TR-VIS-0008
  treatment holds above the write-up.
- **The consumer does not rank.** Producer order and producer counts.

## What the consumer is shipping meanwhile

The Themes centre is being built now against the existing decision-map
catalogue, with every gap shown as a visible placeholder rather than a guess:

- `recipe.questions` stands in for a theme's question group;
- `decision` + `product` + `validation.method` stand in for the write-up, and
  are labelled as the pack's own words, not an author's;
- there is no mined count, so nothing is ranked and no leaderboard position is
  displayed;
- there is no author, so no byline is shown;
- the consumer's own basemaps are used until `presentation` exists.

Where the producer says nothing, the consumer shows less.
