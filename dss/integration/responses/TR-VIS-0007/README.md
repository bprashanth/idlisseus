# TR-VIS-0007 — implemented (amended: automatic, no control)

Node resizing by visible connections, consumer-only, no API change.

## What shipped

- **Automatic**: full graph -> producer record counts (the proposal's default).
  Any legend kind switched off -> every remaining node re-sized by its distinct
  visible neighbours in the retained subgraph. The two-mode control shipped
  first but was removed at the product owner's direction — filtering *is* the
  connections view.
- Degree uses only producer edges already on canvas whose endpoints both
  survive the filters. No inference, no refetch. Floor r = 3 for visible
  isolated nodes.
- **Perf**: the 320ms radius transition is scoped to an `is-resizing` class
  (~400ms window) — no transitions during load or simulation settle. Mild
  reheat (alpha 0.25) after rescale.
- Landmark labels rank by current radius, so filtered views label their
  actual landmarks.
- Status line while filtered: *"sizes now rank by connections among what you
  kept — bounded to this canvas, not complete totals"*.

## Acceptance (live Valparai pack, 1440×1000)

| Criterion | Result |
|---|---|
| Filtering does not refetch; radii change | 0 new `/api/visual` requests; radii re-rank on chip toggle |
| Kind toggles update connection sizing | names×places view: mapped-square places largest, then the names at the most places |
| Bounded-canvas wording present | in status line while any kind is off |
| Records mode restores producer sizing | 180/180 radii restored |
| Search / isolation / cards / labels unchanged | hornbill search → isolation → card verified |

Files: `chatbots/odysseus/static/js/visual/visualAtlas.js` (state, `updateSizes()`,
control, status), `chatbots/odysseus/static/ecodata.css` (control styles, radius
transition).
