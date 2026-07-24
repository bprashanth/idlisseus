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
  "capability_id": "observed-presence-map",
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
        "kind": "query",
        "href": "/results/immutable-result-id/data/observations",
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
        "kind": "query",
        "href": "/results/immutable-result-id/rows",
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
include a digest. Access control is enforced when dereferencing it, not by hiding a browser
button.

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

## Actions and conversational continuation

Actions are suggestions, not automatically executed commands:

```jsonc
{
  "action_id": "expand-search",
  "kind": "follow_up",
  "label": "Search a wider region",
  "capability_id": "observed-presence-map",
  "arguments": {"scope_role": "context"},
  "requires_confirmation": true
}
```

Initial kinds are `follow_up`, `filter`, `drilldown`, `run_capability`, `request_data`,
`request_model`, `open_dashboard` and `export_report`.

The benchmark supplies valid capability ids and typed arguments. Idlisseus decides whether to
render them as buttons, chips, menu entries or ordinary follow-up prompts. Pressing an action
starts a new audited request; the browser does not run analysis itself.

## Capability descriptors

Site packs register capabilities independently from individual sources:

```jsonc
{
  "capability_id": "observed-presence-map",
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

## Compatibility and validation

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
