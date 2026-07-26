# Idlisseus design system — "Field journal"

One system for the whole product: login, shell, chat, cards, charts, maps, panels.
Inspiration: the figure pages of a nature journal and the calm chrome of a modern
data platform. Warm, precise, traceable. Nothing in this file changes the
`idli-result/1` producer contract — it is presentation only.

## Tokens

| Role | Value | Notes |
|---|---|---|
| Page (paper) | `#f7f5f0` | warm paper, whole app background |
| Surface (card) | `#fffdfa` | cards, composer, panels |
| Chart surface | `#fcfcfb` | validated dataviz surface — charts only |
| Ink | `#1b1a17` | primary text |
| Ink secondary | `#52514e` | supporting text |
| Ink muted | `#8a8781` | labels, footnotes |
| Hairline | `#e7e3da` | borders everywhere; stronger `#d9d4c8` |
| Pine (brand) | `#1d5c45` | buttons, links, active nav, user-turn accent |
| Pine deep | `#144533` | hover |
| Pine wash | `rgba(29,92,69,0.08)` | hovers, active pills, user bubble |
| Marker (highlight) | `rgba(252,211,77,0.42)` | `mark.eco-mark` behind key figures; ink text on top |
| Status | good `#0ca30c` · warning `#fab219` · serious `#ec835a` · critical `#d03b3b` | dataviz status palette; caveat washes derive from these |

Evidence-class chart palette is unchanged (`visualTheme.js`, validated):
observed `#2a78d6` / derived `#1baf7a` / modelled `#eb6834`, designed magenta
diamonds, proxy yellow dash, missing hatched. Aqua sits at 2.74:1 on the light
surface → relief rule: every chart keeps its legend and a table/rows view (the
inline cards and panel already do).

## Type

- **Display serif** — `Source Serif 4` (vendored variable woff2 + italic):
  landing h1, site names, figure headlines, stat-tile values, panel titles.
- **UI sans** — Inter (vendored): everything else. Body prose 16px/1.7.
- **Mono** — JetBrains Mono: audit ids, coordinates, code. Never for UI labels.
- Eyebrow labels (small caps feel): Inter 600 10.5px, letter-spacing 0.08em,
  muted ink — used sparingly (card kind, rail headings), not on every label.

## Voice rules (consumer-side)

- No machine text in the reading line: tracebacks, `no_local_evidence_match`,
  audit hexes live behind the "How this was answered" disclosure, never in prose.
- The Why panel defaults **closed**; its summary reads like a sentence.
- Card kind labels are human words ("Map", "Time series"), not `FIGURE_MAP`.
- Highlights (`eco-mark`) stay capped at 3, text nodes only — unchanged.

## Layout

- Left nav rail 232px on paper, hairline right edge: serif wordmark, site card,
  Chat/Maps/Data/History/Sites with icons, pine "New analysis" button at foot.
- Content column max 780px; answers are article prose on paper (no AI bubble);
  the user turn is a pine-washed card, right-aligned.
- Inline visual cards are **figures**: white card, hairline, eyebrow kind row,
  serif headline, canvas, caveats as amber left-rule notes, producer statements
  as pine left-rule notes, action chips, provenance foot.
- Side panel `min(56vw, 940px)` white, hairline left edge — same tokens.
- Right context rail (≥1360px): stat tiles with serif values, data streams,
  recent visuals. Hidden while the detail panel is open.
- Composer: one white card (border on the bar, never on its halves), pine send.
