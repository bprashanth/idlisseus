# Visual backend decision — Vega-Lite primary, R sidecar for statistical figures

Status: decided 2026-07-25, after a benchmark of ~50 visually-useful data platforms and a
backend evaluation (hand-rolled JS, R server-side, Vega-Lite, Observable Plot, ECharts,
Python server-side). Full analysis lives in the session research report; this file records the
decision, the reasons, and the ranked gap list driving the roadmap.

## Decision

1. **Keep the hand-rolled stage** (chapters, evidence panel, figure maps in `visualMap.js`,
   theme in `visualTheme.js`). Leaflet-style geo stays ours; Vega-Lite's geo is weaker.
2. **Vendor Vega + Vega-Lite into `static/lib/vega/` and use them in CSP-interpreter mode**
   (`vega.parse(spec, null, {ast: true})` + `expressionInterpreter`) as the chart grammar —
   the only evaluated option with an official no-`unsafe-eval` mode. Specs are **built
   client-side from typed envelope data, never transported from producers** (a Vega spec can
   fetch; producer-supplied specs would be a request-forgery primitive).
3. **R sidecar later, batch-path only**: Plumber + ggplot2/ggdist in a no-egress container
   behind the bridge pattern; `dsvg()` SVG output with `data-id` marks, our own delegated
   listeners (never ggiraph's `girafe.js` runtime or `onclick` aesthetic — inline handlers
   violate CSP). Declared `latency_class: batch`; progressive revisions deliver the cheap JS
   visual first, the statistical figure as revision 2. Recipes are scientist-contributed R
   files with digests (`capability_runs[].recipe_digest`). Build it only when the first
   real recipe exists. **No Shiny** (needs `unsafe-inline`+`unsafe-eval`), no webR (~38 MB,
   `wasm-unsafe-eval`), no plotly.js, no Highcharts (licence).

Why: nine of the ten benchmark gaps are statistical-graphics gaps; Vega-Lite closes
uncertainty bands, facets and brushing with configuration rather than bespoke code, at
273 KB gz vendored, while preserving the contract invariant (browser binds digest-verified
payloads into views; nothing renders to bitmaps on the interactive path). R stays because the
audience writes ggplot2 and contributed figure recipes matter more than render speed —
ggdist has no JS equivalent.

## Ranked gap list from the platform benchmark (top 10)

Strengths confirmed: provenance chrome, abstention states, drill-to-rows, two-layer query
representation, ambient AOI orientation — ahead of most commercial BI. Weaknesses:
uncertainty, comparison, reuse. Roadmap order:

1. **Uncertainty as a contract object** — optional `uncertainty` block per layer/summary
   (`interval` / `agreement` / `draws` with data refs). Renderer rules: CI spanning zero →
   open/white marker (eBird); agreement → IPCC stipple/hatch; prefer gradient/violin over
   bar-capped error bars. Modelled layers should not validate without one.
2. **Effort denominators as a togglable view** — `denominator_ref` +
   `absence_semantics: complete_survey|non_detection|unknown`; per-layer raw/per-effort
   normalisation toggle; refuse absence claims when semantics unknown.
3. **Method panel + verified/generated badge** — render `question.resolved`,
   `capability_runs`, arguments, source versions in order; `audit.assurance:
   verified|generated|cached` from registered parameterisations (Genie/Looker pattern).
4. **Citable permalink** — `audit.citation` + same-origin `/r/{result_id}` resolver that
   re-materialises the stage from the immutable envelope; "cite this view" in the footer.
5. **Client-side cross-filter with visible chips** — declared bounded facets
   (`visual.facets[]`, `shared_with`) filtering already-held payloads; chips in the caption
   card; degrade to an audited `filter` action at any boundary the facet can't honour.
6. **Facet grammar for small multiples** — `visual.facet: {by, wrap, shared_scale}` on chart
   and map grammars; Vega-Lite makes this nearly free for charts.
7. **Annotation layers** — `visual.annotations[]` anchored to marks (point/range/region),
   produced by the same capability as the finding; leader-line labels; caption headline
   becomes the summary.
8. **Compare mode** — swipe/opacity/split (Worldview primitives) via `visual.compare`; the
   high-value variant is cross-result: pin a prior chapter's visual, reconcile
   `pack_digest`/source versions in a banner.
9. **Export that preserves the claim** — per-visual PNG/SVG with headline + evidence key +
   limitations + source line + citation baked into the frame; CSV/GeoJSON of exact payloads;
   deep link with facet state.
10. **Time brush + cross-chapter time sync** — brush emits a facet; chapter rail carries a
    global time scope new questions inherit.

Explicitly deprioritised: scrollytelling beyond the chapter model (no comprehension gain),
guess-then-reveal, alerts/subscriptions (different surface), HOPs animation (no mature lib).

## Notes

- Keep `cdn.jsdelivr.net` in the CSP for now — KaTeX/Mermaid/doc-preview Chart.js flows still
  use it; removing it is a separate cleanup once those are vendored too.
- Quarto `embed-resources: true` is the `export_report` implementation; KaTeX/MathJax are NOT
  embedded by default — override or keep exports math-free.
- Contract additions above are additive within `idli-result/1`; each needs a fixture per the
  contract's own five-step rule before either side depends on it.
