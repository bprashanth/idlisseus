# Idlisseus visual-first UX — "the Atlas"

Status: design brief for the visual-first chat experience. Implementation lives in
`chatbots/odysseus`. Contract: [`VISUAL_RESULT_CONTRACT.md`](VISUAL_RESULT_CONTRACT.md)
(`idli-result/1`). This document is pack-agnostic by construction: nothing in it may name a
sector, entity, source or metric.

## The bar

Every answer reads like a New York Times graphics piece: a full-bleed visual first, a short
headline that states the finding, two or three sentences of caption — never a wall of text. The
audience will not read paragraphs; they will read a map. Text explains the visual; the visual
carries the evidence.

## Experience model

The browser viewport is a **stage**. A conversation is a scrollable sequence of **chapters**.
One question → one chapter. Each chapter owns the full viewport height when active.

```text
┌────────────────────────────────────────────────┐
│  STAGE (full viewport)                         │
│                                                │
│   primary visual (full-bleed, animated entry)  │
│                                                │
│   ┌────────────────────────┐                   │
│   │ headline (answer)      │  caption card,    │
│   │ 2–3 sentence caption   │  overlays visual  │
│   │ evidence chips         │                   │
│   └────────────────────────┘                   │
│   [supporting visual thumbnails →]             │
│                                                │
│  ────────────────────────────────────────────  │
│  ask a question…                    [history]  │
└────────────────────────────────────────────────┘
```

- **Ambient orientation.** When a chat starts on a visual-capable endpoint, the stage
  immediately shows the site-orientation visual (from the sub-200 ms result service) before any
  question is asked. The user lands *in the place*, not in an empty chat.
- **Chapters on scroll.** Scrolling up moves through prior chapters; each stays live and
  interactive. The chat history is the scroll itself. A slim chapter rail (dots + question
  stubs) gives random access.
- **Caption cards, not messages.** The assistant's prose renders as a compact card overlaying
  the visual: headline (from `answer.headline`), detail (2–3 sentences max shown; the rest
  behind "more"), evidence chips, limitation banners.
- **Layout is chosen by the envelope, not hardcoded.** `priority: primary` → full-bleed.
  `supporting` → thumbnail rail that expands to split view. Two primaries or
  `visual_type: dashboard` → grid. Text-only answers (no visuals) → centered narrow column,
  still caption-styled.

## Progressive delivery (never blank, never late)

1. Question submitted → chapter is created instantly with the question and an activity line.
2. `idli-activity/1` events drive a live "what's happening" ticker (one line, subdued).
3. First `working`/`complete` revision → primary visual animates in (fade + zoom-settle).
4. Later revisions replace visuals in place (crossfade); the chapter never jumps.
5. Streamed prose lands in the caption card as it arrives.
6. Failure keeps whatever visual was valid: a failed gate or partial source shows the
   observed-data visual plus a structured limitation banner — never an empty screen.

If a harder question needs slow model work, the first revision must still show the cheap
observed layer (points/coverage) as scaffolding; the model surface arrives as a later revision.

## Visual grammar (generic renderers)

Renderers key off `visual_type` + `geometry_type` of layers, never off view names:

| visual_type | renderer | notes |
|---|---|---|
| map | Leaflet stage map | polygon AOIs, cell choropleths, point layers with uncertainty, layer toggles |
| chart / timeline | time-series canvas | line/area + coverage strip beneath; intervention markers |
| metric | stat tiles | value + unit + denominators |
| hierarchy | sunburst/tree | click to descend |
| matrix / network / table | grid/graph/table renderers | phase 2 |
| dashboard | composition grid of the above | each card is a full renderer |
| report | rendered document link panel | existing document panel |

**Evidence classes are the design system.** Every layer/series/tile carries its
`evidence_class`; the palette, texture and legend derive from it, not from the sector:

- `observed` — saturated solid (the only class allowed full saturation)
- `reported` — outlined / neutral fill
- `derived` — solid, second hue
- `proxy` — dashed outline
- `modelled` — translucent gradient + uncertainty; never occludes observed
- `designed` — pin/diamond markers, clearly "proposed"
- `model_memory` — presented only as a search lead chip, never on a map/chart
- `missing` — explicit hatched gray; absence is drawn, not implied

Evidence chips sit in the caption card and in every legend. The same class always looks the
same, in every pack, in every renderer.

## Interaction: no black boxes

- **Hover** any point/cell/series → tooltip with value, unit, date, source id, evidence class.
- **Click** → evidence panel slides in: the underlying rows (`drilldowns[].data_ref`), source
  version, digest, limitations affecting that layer. Every aggregate answers "show me the
  rows" or states its disclosure boundary.
- **Actions** from `actions[]` render as chips under the caption (follow_up, filter,
  drilldown, run_capability, request_data…). Clicking one submits a new audited request — the
  browser never computes analysis itself.
- **Layer toggles** on maps; **brush/zoom** on time series (phase 2).

## Data path

```text
browser
  → odysseus backend proxy  /api/visual/<endpoint_id>/…   (auth: session)
      → site bridge (per-endpoint base URL, bearer token server-side)
          → result service:  POST /v1/results/query
                             GET  /v1/results/<id>
                             GET  /v1/results/<id>/data/<handle>   (immutable, cacheable)
```

- The browser never holds bridge tokens; odysseus proxies and enforces the session.
- Payloads are fetched by handle and cached immutably (digest-addressed).
- The chat stream (Codex) tells the UI *which* result to show via a result marker in the
  stream; the UI fetches the envelope through the proxy. Ambient orientation is UI-initiated
  (capability `site-orientation`, no arguments).
- Fixtures: a dev route serves `dss/contracts/fixtures/*` plus generated real envelopes so the
  whole experience runs with zero backends. The renderer test page iterates every fixture.

## Anti-overfit rules

1. No sector vocabulary in JS/CSS — labels, units, legends all come from the envelope.
2. Renderer selection uses `visual_type`/`geometry_type`/`priority`/`status` only; unknown
   `view` values must render via their grammar; unknown `visual_type` falls back to the
   summary card + drilldown table.
3. Every renderer must handle: `ready`, `partial`, `blocked`, `failed`, empty layers, missing
   denominators, and `site.synthetic: true` (persistent test-data ribbon).
4. Swapping the site pack behind an endpoint must require zero UI changes — this is tested by
   running the same UI against contract fixtures from more than one pack.

## What success looks like

An expert asks a question and, within a second, sees the place light up with what is actually
known — and equally clearly, what is not known. They hover, they drill to rows, they click one
suggested action to widen the search or request the missing measurement. They screenshot the
stage and put it in a proposal. Nothing on screen is decoration: every mark is evidence with a
class, a source and a way in.
