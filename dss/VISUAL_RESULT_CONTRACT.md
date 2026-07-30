# Visual result contract

Status: normative boundary for parallel benchmark and Idlisseus development.

Contract version: `idli-result/1`

Last checked: 2026-07-25

This contract lets a benchmark repository add sources, indexes, connectors, capabilities and
models while Idlisseus independently develops the visual experience. It describes evidence
returned for one resolved user request. It does not prescribe how a benchmark stores its data or
how Idlisseus lays out a page.

## The boundary

```text
site pack and source versions
  -> benchmark-owned index, connectors and capabilities
  -> idli-result/1
  -> Idlisseus renderer, conversation and audit UX
```

The benchmark side owns meaning and computation. Idlisseus owns presentation and interaction.
Neither side may infer the other's private implementation details.

The existing `visual-site-pack/0.1`, `visual-source-registry/0.1` and
`visual-bundle/0.1` formats are build-time inputs and products. They are not the browser wire
format. A benchmark query service may read them, but must translate a completed query into
`idli-result/1`.

## Required envelope

```jsonc
{
  "schema_version": "idli-result/1",
  "result_id": "immutable-result-id",
  "request_id": "request-or-turn-id",
  "revision": 1,
  "status": "complete",
  "site": {
    "site_id": "stable-site-id",
    "label": "Display label",
    "pack_digest": "sha256:..."
  },
  "question": {
    "original": "What the user asked",
    "resolved": "The typed analytical question that was executed",
    "bindings": {
      "aoi_ids": ["target"],
      "entity_ids": ["canonical-entity-id"],
      "time": {"start": "2020-01-01", "end": "2025-12-31"}
    }
  },
  "answer": {
    "headline": "One short, evidence-bounded result",
    "detail": "Optional concise explanation",
    "evidence_classes": ["observed", "reported"]
  },
  "visuals": [],
  "limitations": [],
  "actions": [],
  "audit": {
    "audit_id": "stable-audit-id",
    "source_versions": [],
    "capability_runs": [],
    "query_hash": "sha256:..."
  }
}
```

Required top-level fields are `schema_version`, `result_id`, `request_id`, `revision`, `status`,
`site`, `question`, `answer`, `visuals`, `limitations`, `actions` and `audit`. Producers may add
fields. Consumers must ignore unknown fields within a major contract version.

`result_id` identifies the evidence result and remains stable across streamed revisions.
`request_id` connects it to the conversation turn. `revision` increases monotonically. A
completed result is immutable; a later changed answer receives a new `result_id`.

Synthetic/demo site packs set `site.synthetic: true`, mark synthetic source versions, and include
the stable informational limitation `synthetic-data`. Idlisseus must show a persistent test-data
notice for that result. The notice is driven only by these fields; swapping to a real pack removes
it without a renderer or layout change.

## Status and progressive delivery

`status` is one of:

- `working`: a valid partial result is available and more work is running;
- `complete`: all promised work for this result finished;
- `partial`: useful evidence is available but a declared source, capability or gate failed;
- `blocked`: no evidence-bearing result could be produced; or
- `cancelled`: the request was stopped.

The first result revision should contain the earliest valid visual, even when source expansion or
modelling continues. Later revisions replace the result with the same `result_id`; they do not
append raw progress markup to answer text.

Runtime activity is a separate event stream:

```jsonc
{
  "schema_version": "idli-activity/1",
  "request_id": "request-or-turn-id",
  "phase": "query",
  "label": "Finding records in the surrounding region",
  "capability_id": "entity-record-map",
  "state": "running"
}
```

Idlisseus may show one current activity beside its progress animation and keep prior activity in
an optional audit view. Activity messages never become answer markdown.

## Visual object

Every member of `visuals` has this shape:

```jsonc
{
  "visual_id": "stable-within-result",
  "visual_type": "map",
  "view": "observed-points",
  "title": "Where records are available",
  "priority": "primary",
  "status": "ready",
  "scope": {
    "aoi_ids": ["target", "context"],
    "time": {"start": null, "end": null}
  },
  "layers": [
    {
      "layer_id": "observations",
      "evidence_class": "observed",
      "geometry_type": "point",
      "data_ref": {
        "kind": "result_data",
        "handle": "observations",
        "media_type": "application/geo+json",
        "digest": "sha256:..."
      },
      "legend": {"label": "Observed records"},
      "style_hint": {"palette_role": "observed"}
    }
  ],
  "summary": {
    "headline": "Records occur in 18 cells",
    "denominators": {"records": 52, "surveyed_cells": 24}
  },
  "drilldowns": [
    {
      "action_id": "open-records",
      "label": "Inspect records",
      "data_ref": {
        "kind": "result_data",
        "handle": "source-rows",
        "media_type": "application/json"
      }
    }
  ],
  "limitations": []
}
```

`visual_type` is renderer-level grammar, initially `map`, `chart`, `table`, `matrix`, `network`,
`hierarchy`, `timeline`, `metric`, `dashboard` or `report`. `view` describes the analytical view
without imposing a layout. A new `view` using an existing grammar is not a UI contract change.
A new `visual_type` requires a renderer or a declared fallback.

`priority` is `primary`, `supporting` or `audit`. Idlisseus should lead with the primary visual
when one is ready. It may choose full-canvas, split, card, side-panel or mobile layouts.

`status` is `ready`, `partial`, `blocked` or `failed`. Partial and failed secondary visuals must
not hide valid primary evidence.

Large rows, points, rasters, tiles and documents stay behind immutable `data_ref` handles. Do not
put a multi-megabyte payload into chat JSON. A reference must include its media type and should
include a digest.

The producer emits an opaque `handle`; it does not guess a browser URL. Idlisseus resolves that
handle through the authenticated result proxy described below and may add an `href` in its
client-facing state. `href` is permitted by the schema for already published same-origin
artifacts, but renderers must accept handle-only references.

## Evidence classes

Every evidence-bearing layer and statement uses one or more of:

- `observed`: direct source-linked records or measurements;
- `reported`: a source-linked textual or organisational assertion;
- `derived`: deterministic aggregation or transformation of admitted inputs;
- `proxy`: a disclosed substitute measurement;
- `modelled`: an estimate produced by a registered model run;
- `designed`: a proposed action, sampling point or scenario;
- `model_memory`: an unverified lead from model weights; or
- `missing`: an explicit coverage or capability gap.

These classes are semantic, not colour names. Idlisseus chooses accessible icons, labels and
colours, but the class must remain visible in the visual, explanation and audit. `model_memory`
may seed search or a follow-up question; it cannot be presented as sourced evidence.

## Limitations, failures and gates

A limitation is structured:

```jsonc
{
  "code": "missing-effort-denominator",
  "severity": "warning",
  "message": "Presence can be shown, but absence and rates are not supported.",
  "affects": ["visual-id", "answer"],
  "details_ref": null
}
```

Severity is `info`, `warning` or `error`. Stable codes let Fable design useful states without
parsing prose.

Model and transfer visuals must expose donor scope, target scope, model run, uncertainty and gate
outcomes as layers or audit references. A failed gate returns the valid observed/data-coverage
visual and a structured limitation; it does not erase the result.

## Uncertainty, denominators and annotations (additive v1 fields)

Three optional, additive fields per the `VISUAL_BACKEND_DECISION.md` roadmap. All are
producer-optional; consumers ignore them when absent and no required list changes.

**Per-layer `uncertainty`** (roadmap #1):

```jsonc
{
  "kind": "interval",
  "level": 0.8,
  "lower_ref": {"kind": "result_data", "handle": "metric-lower", "media_type": "application/json"},
  "upper_ref": {"kind": "result_data", "handle": "metric-upper", "media_type": "application/json"}
}
```

`kind` is `interval` (a credible/confidence interval at `level`) or `agreement` (model or
ensemble agreement, e.g. IPCC-style):

```jsonc
{"kind": "agreement", "agreement": {"fraction": 0.85, "signal_to_noise": 1.6}}
```

For `series` layers, an interval is often cheaper carried inline in the payload rows than as
separate `lower_ref`/`upper_ref` data refs. When the producer does this, each payload row may
carry numeric `lower`/`upper` fields alongside `value`, and the layer's `uncertainty` block
declares only `{"kind": "interval", "level": 0.8, "inline": true}` — no refs needed.

Per the roadmap: a layer with `evidence_class: "modelled"` should carry an `uncertainty` block;
`validate_fixtures.py` emits a warning (not a failure) listing modelled layers without one.

**Per-layer `denominator_ref` and `absence_semantics`** (roadmap #2):

```jsonc
{
  "denominator_ref": {"kind": "result_data", "handle": "effort", "media_type": "application/geo+json"},
  "absence_semantics": "non_detection"
}
```

`denominator_ref` points at the effort/exposure payload a coverage or rate layer should be
normalised against. `absence_semantics` is `complete_survey` (surveyed area with no target
observed — a real absence), `non_detection` (surveyed but detection is imperfect — absence is
not certain), or `unknown` (no basis to interpret a gap as absence at all). Idlisseus should
refuse to render an absence claim when semantics are `unknown`.

**Per-visual `annotations`** (roadmap #7):

```jsonc
{
  "anchor": {"kind": "point", "t": "2023-12-01", "value": 32.16},
  "text": "Highest value in the record",
  "evidence_class": "derived",
  "emphasis": "primary"
}
```

`annotations` is an optional array on the visual object, alongside `layers`. Each entry anchors
a short label to a mark: a `point` anchor (`t`/`value` for a chart mark, `lon`/`lat` for a map
mark) or a `range` anchor (`start`/`end`). `emphasis` is `primary` or `secondary`; a primary
annotation's `text` is a candidate for the visual's headline treatment.

## Actions and conversational continuation

Actions are suggestions, not automatically executed commands:

```jsonc
{
  "action_id": "expand-search",
  "kind": "follow_up",
  "label": "Search a wider region",
  "capability_id": "entity-record-map",
  "arguments": {"scope_role": "context"},
  "requires_confirmation": true
}
```

Initial kinds are `follow_up`, `filter`, `drilldown`, `run_capability`, `request_data`,
`request_model`, `open_dashboard` and `export_report`.

The benchmark supplies valid capability ids and typed arguments. Idlisseus decides whether to
render them as buttons, chips, menu entries or ordinary follow-up prompts. Pressing an action
starts a new audited request; the browser does not run analysis itself.

## Live transport

The current bridge remains OpenAI chat-completions compatible. `idli-result/1` and
`idli-activity/1` travel as typed, non-token events inside that existing SSE stream; they are not
encoded as answer text, comments, tool-call arguments or trailing prose.

An activity frame from the bridge is:

```text
data: {
  "id": "chatcmpl-...",
  "object": "chat.completion.chunk",
  "model": "idli-insight",
  "choices": [],
  "idlisseus_event": {
    "type": "idli_activity",
    "activity": { "schema_version": "idli-activity/1", "...": "..." }
  }
}
```

A result revision uses the same outer chunk:

```text
data: {
  "id": "chatcmpl-...",
  "object": "chat.completion.chunk",
  "model": "idli-insight",
  "choices": [],
  "idlisseus_event": {
    "type": "idli_result",
    "result": { "schema_version": "idli-result/1", "...": "..." }
  }
}
```

Normal answer tokens continue in ordinary `choices[].delta.content` chunks. A bridge may emit
several revisions with one `result_id`; their revision numbers must increase. It emits the final
`complete`, `partial`, `blocked` or `cancelled` revision before `data: [DONE]`.

Idlisseus's upstream reader already unwraps `idlisseus_event` objects from OpenAI-compatible
chunks. The chat route must schema-validate and forward only the two event types above; unknown or
invalid result events are retained in operator audit and not rendered. This transport is additive
to the existing skill/progress compatibility events.

## Result data transport and ownership

The benchmark result service owns immutable bytes internally:

```text
GET /v1/results/{result_id}
GET /v1/results/{result_id}/data/{handle}
```

That service is bound to one configured site pack. It is reachable by the bridge or Idlisseus
server with a service credential and is not a public browser origin.

Idlisseus owns the browser-facing, same-origin surface:

```text
GET /api/visual-results/{result_id}
GET /api/visual-results/{result_id}/data/{handle}
```

For every request Idlisseus verifies the signed-in user can access the chat/session that received
the result, resolves the session's pinned endpoint and pack digest, then proxies the internal
result service using server-side credentials. It must verify the returned media type and digest,
apply response-size limits and preserve download/embedding policy. The browser never receives a
bridge bearer token or an internal host/port.

This ownership keeps authentication, CSP, iframe policy, range requests and revocation in the
Idlisseus layer while leaving result computation and immutable bytes benchmark-side. A later
object-store implementation may replace the proxy with short-lived same-origin or signed URLs
without changing `idli-result/1`.

## Capability descriptors

Site packs register capabilities independently from individual sources:

```jsonc
{
  "capability_id": "entity-record-map",
  "version": "1.0.0",
  "label": "Map where records are available",
  "input_schema": {},
  "output_views": ["observed-points", "source-coverage"],
  "required_planes": ["events"],
  "optional_planes": ["effort"],
  "latency_class": "interactive",
  "evidence_classes": ["observed", "derived"]
}
```

A capability is a site-agnostic analytical operation. Sources and adapters provide its inputs.
The site pack declares whether it is ready, partial or unavailable for that site's current
version. Fable uses descriptors for discoverability and loading states, not to reproduce the
calculation.

Capability ids must describe analytical grammar rather than one sector's vocabulary. For
example, `entity-record-map` can map records for a facility, programme, occupation, organism or
other resolved entity. The pack supplies entity meaning and arguments; the renderer receives the
same map contract.

## Transport (implemented POC binding)

Two additive bindings carry this contract into the live chat product:

1. **Result marker in the chat stream.** When the bridge's conversation agent completes a
   capability run, its streamed answer includes, on its own line,
   `<!-- idli-result:{"result_id":"…"} -->`. The Idlisseus stream consumer strips the marker
   from visible prose (live, resumed and history renders) and raises it as a UI event. Markers
   persist in stored message content, so history replay re-materialises visuals.
2. **Proxy fetch of envelopes and payloads.** The browser never talks to a bridge directly and
   never holds bridge tokens. Idlisseus exposes, for each registered endpoint id:
   `GET /api/visual/{endpoint}/results/{result_id}`,
   `GET /api/visual/{endpoint}/results/{result_id}/data/{handle}`,
   `GET /api/visual/{endpoint}/capabilities` and `POST /api/visual/{endpoint}/query`, proxied to
   the bridge's `/v1/results/*` and `/v1/capabilities` with the endpoint's stored bearer token.
   Payload responses are immutable and digest-verified client-side.

The stage also issues an unprompted `site-orientation` query when a conversation starts on an
endpoint whose capability list declares it ready — the ambient orientation visual.

## Subject bindings and model-selected membership (additive v1 fields, TR-VIS-0003/0004)

`question.bindings.subjects` MAY carry, per subject, `requested` (the reader's phrase),
`resolution_method` (`exact_alias` | `source_declared_group` | `deterministic_widening` |
`model_selected` | `cached_model_selection`), `member_labels` (reader-facing names of the
selected members), `entity_ids`, `binding_id` and `selector` (`model`, `prompt_version`).

Consumer behaviour: when `resolution_method` is `model_selected` or
`cached_model_selection` and `member_labels` is non-empty, the renderer shows a compact
"read as" disclosure beside the visual — the phrase, the member names, and an explicit
"assistant interpretation" label — structurally distinct (dashed rule + wording, never
colour alone) from an exact stored name or source-declared group. `binding_id` and
`selector` stay out of the primary prose. An action whose `action_id` begins
`correct-subject-` renders as the correction affordance ("Change this reading" when the
producer sends no label) and is forwarded through the conversation like any other action.
Results without these fields render unchanged. The consumer never infers membership: it
renders what the producer verified, and forwards choices; the producer remains the
id-verification boundary.

A blocked or unresolved subject lookup produces no result marker, so nothing renders as a
successful visual; the clarification itself is carried by the conversation (agent prose
and, when supplied, guided actions), with progress events covering the selection turn.

## Problem reports (additive, TR-VIS-0005)

The producer MAY expose `POST /v1/feedback/draft` and `POST /v1/feedback/submit`
(proxied at `/api/visual/{endpoint_id}/feedback/draft|submit`). Draft accepts
`{session_id, description (required), include_conversation (default true),
transcript: [{role: user|assistant, content}]}` and returns an immutable draft
(`report_id`, `repository`, `public_warning`, `title`, `body`,
`conversation_messages`, `requires_confirmation: true`). Submit requires
`{report_id, confirmed: true}` and returns either `status: submitted` with the public
issue `url`, or `status: ready_for_browser_confirmation` with a pre-filled issue `url`.

Consumer behaviour: a "Report a problem" action is always discoverable on a result card
and prominent when the envelope is failed/blocked or carries an error-severity
limitation. The dialog requires free-form text, defaults conversation inclusion to on,
sends only the visible user/assistant transcript, and shows the returned repository,
public warning, title and full body before a separate explicit confirmation. Cancelling
publishes nothing. Hidden prompts, progress events, tool output and credentials are
never included — enforced again producer-side.

## Compatibility and validation

The normative machine-readable schemas and synthetic fixture corpus are in
[`contracts/`](contracts/). The fixtures contain no organisation/site records; real producer
conformance stays in the benchmark repository.

The contract version uses `name/major`. Additive fields and new `view` values are compatible
within `idli-result/1`. Removing or changing a required field, enum meaning or reference
semantics requires `idli-result/2`.

Before either workstream depends on a feature:

1. add a minimal contract fixture;
2. validate it against the shared schema;
3. render the fixture in Idlisseus, including mobile, partial and empty states;
4. emit the same shape from at least one real benchmark query; and
5. retain the fixture as a cross-repository compatibility test.

The first fixture set should cover:

- site orientation with a primary map;
- observed points with source-row drill-down;
- coverage with explicit effort/exposure;
- an empty target with surrounding data;
- a modelled layer with uncertainty and passing gates;
- a failed gate that retains observed coverage;
- a designed data-request layer;
- a time series with units and coverage;
- a source outage with a valid partial result; and
- a dashboard/report composed from immutable prior results.

## What may evolve independently

Benchmark agents may add or replace files, database engines, embeddings, connectors, feature
cubes, models and capability implementations without a Fable change when emitted results remain
valid.

Fable may change page structure, visual libraries, colours, responsive behaviour, progressive
disclosure, panel placement and renderer implementation without a benchmark change when it
continues to accept valid results.

Coordination is required only for a breaking contract change, a new renderer grammar, a new
access-control interaction, or a new reference transport that existing consumers cannot safely
open.
