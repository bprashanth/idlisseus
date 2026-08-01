# TR-VIS-0008 — implemented

Validated decision maps: a catalogue-driven centre, and a map that always
arrives with its test.

> **Update 2026-08-01.** The Maps centre described below has been reframed as
> the **Themes centre** (see `../../requests/IDL-REQ-0004/`): the browsable unit
> is now the recurring question, and a decision map is one published answer to
> it. Every treatment in this response is unchanged and still shipping — the
> catalogue drive, the validation panel, the colour-independent marks and the
> fail-closed selection rule all moved across intact. What changed is the
> framing and the reading view around them.

## What shipped

**Maps centre** (`static/js/visual/visualMapsCentre.js`, nav → Maps)
- Backed by `GET /v1/decision-maps` through a new proxy route
  `/api/visual/{endpoint_id}/decision-maps` (tokens stay server-side).
- Cards grouped by the producer's generic `theme`, in the `DECISION_MAPS.md`
  order; each shows title, decision, readiness and freshness (recipe version +
  validation kind — no timestamp is invented, see the note below).
- **Ready** cards run `validated-decision-map` with only the arguments the
  recipe advertises, clamped to its declared minimum/maximum.
- **Waiting** cards list the exact `required_inputs` that are not `available`
  and render *no* run affordance — the centre can never imply a map exists.
- The old "Maps = reopen the last figure mentioned in chat" behaviour is gone.

**The map and its test** (`static/js/visual/visualDecisionMap.js`)
- "How this map was tested" renders in the reading flow: under the map in the
  chat card, and in the panel caption right after the claim — before chips,
  limitations and provenance. Never behind the audit link or an accordion, and
  the validation-summary visual is removed from the supporting rail so it is
  not also a click-to-open card.
- Shows validation kind, split rule, periods, sample sizes, and every declared
  check as value-against-threshold with the operator in words. Pass state is a
  word *and* a mark (`✓ met` / `✗ not met`), so greyscale and screen readers
  carry it. The producer's bounded claim is printed verbatim.
- **Failed** → keeps observed and withheld layers, shows the failed checks,
  and says in the same visual field that no place is marked for action.

**Marks that survive greyscale** (`visualMap.js`, `visualLeaflet.js`)
- Withheld test observations share the *observed* evidence class with the
  observations used to fit, so colour cannot separate them: they draw as a
  crossed ring in both renderers, with a matching legend swatch.
- A location flagged by the declared `selected_field` wears a heavy ink collar
  — in both renderers and for both geometries (cells on the hindcast recipe,
  points on the spatial holdout) — legended "chosen within the declared
  budget (n)".
- `selectionAllowed()` gates on `answer.validation.status === 'passed'`;
  anything else sets `suppressSelection`, which both renderers honour.

**Layer toggles** — one bar from the producer's layer ids and legend labels,
driving SVG layer groups and registered Leaflet overlays. Show/hide of drawn
marks only: no recomputation, no producer value changes, validation untouched.

## Acceptance (1440×1000)

| Criterion | Result |
|---|---|
| Ready card opens a map + its test without starting a chat | ✅ Maps → run → panel with map, toggles and "How this map was tested" |
| Passed hindcast distinguishes fit / withheld / ranked / selected | ✅ 245 fit dots, 60 crossed rings, ranked cells, 6 ink collars; metrics beside the map |
| Failed hindcast shows failed checks, no selected places | ✅ AUC 0.477 vs 0.550 `✗ not met`, "0 selected cells", no collar, no "chosen…" legend entry |
| Spatial holdout explains whole withheld units, not failures | ✅ "Tested on whole places held back from fitting"; errors framed as resurvey value |
| Waiting card lists missing inputs, offers no run | ✅ 5 waiting recipes, 2 missing inputs each, no run button in the DOM |
| Chat and Maps centre agree | ✅ both call `openInPanel` → same stage code, same envelope |
| Toggles do not recompute or hide validation | ✅ withheld layer off → 60 marks → 0, panel unchanged |
| Existing results, graph, chat, uploads, explain, feedback unchanged | ✅ 11 pre-existing fixtures render as before; 19 tests pass |

## Fixtures (payloads committed — the lab needs no backend)

- `12-decision-map-hindcast-passed` — mammalia, budget 6, passed.
- `13-decision-map-hindcast-failed` — all taxa: a **genuine live failure**
  (AUC 0.477 < 0.550, 0 cells selected, three other checks met). It did not
  need hand-authoring.
- `14-decision-map-spatial-holdout` — 123 plots, 17 landscapes, +18.6% MAE.
- `decision-map-catalog.json` — all 7 recipes (2 ready, 5 waiting).

Tracking these required a `.gitignore` exception: fixture payloads under
`static/contracts/fixtures/data/` had never been committed, so a fresh clone
could not render the lab at all. Fixed for every fixture, not just these.

## Notes for the producer

1. The catalogue has no per-recipe last-run or `generated_at`, so card
   "freshness" is the recipe version plus validation kind. A last-run
   timestamp or latest-result pointer would let the centre show real recency
   instead of the consumer inventing one.
2. At the roadkill recipe's default extent the fitting and withheld points
   overlap heavily, so the crossed ring does all the separating work at low
   zoom. Not a blocker.

Files: `routes/visual_routes.py`, `static/js/visual/visualDecisionMap.js`,
`visualMapsCentre.js`, `visualMap.js`, `visualLeaflet.js`, `visualRenderers.js`,
`visualStage.js`, `visualChat.js`, `visualShell.js`, `visualData.js`,
`visualLab.js`, `static/visual.css`, `static/ecodata.css`, `static/sw.js`,
`tests/test_decision_maps.py`.
