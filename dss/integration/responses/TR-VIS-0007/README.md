# TR-VIS-0007 — implemented

Node resizing by visible connections, consumer-only, no API change.

## What shipped

- **`Size by` control** in the Atlas toolbar: `Records` (default) | `Connections`.
  Presentation state only (`state.sizeMode`), never persisted, never refetches.
- **Connections mode**: each visible node's score = distinct visible neighbours,
  from edges already on the canvas whose endpoints both survive the kind filters.
  Producer edges only — no inference. Nonzero floor (r = 3) for visible isolated
  nodes; same radius scale as records mode.
- **Smooth rescale**: 320 ms CSS transition on `r`, plus a mild simulation reheat
  (alpha 0.25) so collision spacing adapts to the new radii.
- **Recompute triggers**: kind-filter toggle/solo/reset, neighbourhood expansion,
  and mode switch.
- **Honesty wording**: while active, the status line appends
  *"sizes show connections on this bounded canvas, not complete totals"*; the
  control's tooltip repeats it. Intro copy made mode-neutral.

## Acceptance (live Valparai pack, 1440×1000)

| Criterion | Result |
|---|---|
| Toggle does not refetch; radii change | 0 new `/api/visual` requests; 179/180 radii changed |
| Kind toggles update connection sizing | soloing Places recomputed over remaining 20 nodes |
| Bounded-canvas wording present | in status line + tooltip |
| Records mode restores producer sizing | 180/180 radii restored |
| Search / isolation / cards / labels unchanged | hornbill search → isolation → card verified |

Files: `chatbots/odysseus/static/js/visual/visualAtlas.js` (state, `updateSizes()`,
control, status), `chatbots/odysseus/static/ecodata.css` (control styles, radius
transition).
