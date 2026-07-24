#!/usr/bin/env python3
"""Generate deterministic, synthetic Idli renderer fixtures."""

from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parent
OUTPUT = ROOT / "fixtures"


def digest(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode()).hexdigest()


def data_ref(handle: str, media_type: str = "application/json") -> dict[str, Any]:
    return {
        "kind": "result_data",
        "handle": handle,
        "media_type": media_type,
        "digest": digest(handle),
    }


def limitation(code: str, message: str, severity: str = "warning",
               affects: list[str] | None = None) -> dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "message": message,
        "affects": affects or ["answer"],
        "details_ref": None,
    }


def layer(layer_id: str, evidence_class: str, geometry_type: str,
          label: str, media_type: str = "application/geo+json") -> dict[str, Any]:
    return {
        "layer_id": layer_id,
        "evidence_class": evidence_class,
        "geometry_type": geometry_type,
        "data_ref": data_ref(layer_id, media_type),
        "legend": {"label": label},
        "style_hint": {"palette_role": evidence_class},
    }


def visual(visual_id: str, visual_type: str, view: str, title: str,
           layers: list[dict[str, Any]], headline: str,
           denominators: dict[str, Any], *,
           status: str = "ready", priority: str = "primary",
           limitations: list[dict[str, Any]] | None = None,
           drilldown: bool = True) -> dict[str, Any]:
    return {
        "visual_id": visual_id,
        "visual_type": visual_type,
        "view": view,
        "title": title,
        "priority": priority,
        "status": status,
        "scope": {
            "aoi_ids": ["target", "context"],
            "time": {"start": None, "end": None},
        },
        "layers": layers,
        "summary": {"headline": headline, "denominators": denominators},
        "drilldowns": (
            [{
                "action_id": f"inspect-{visual_id}",
                "label": "Inspect source rows",
                "data_ref": data_ref(f"{visual_id}-rows"),
            }]
            if drilldown else []
        ),
        "limitations": limitations or [],
    }


def action(action_id: str, kind: str, label: str, capability_id: str,
           arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "action_id": action_id,
        "kind": kind,
        "label": label,
        "capability_id": capability_id,
        "arguments": arguments,
        "requires_confirmation": True,
    }


def result(key: str, original: str, resolved: str, headline: str,
           evidence_classes: list[str], visuals: list[dict[str, Any]], *,
           status: str = "complete",
           limitations: list[dict[str, Any]] | None = None,
           actions: list[dict[str, Any]] | None = None,
           capability: str = "fixture-capability") -> dict[str, Any]:
    return {
        "schema_version": "idli-result/1",
        "result_id": f"fixture-{key}",
        "request_id": f"fixture-request-{key}",
        "revision": 1,
        "status": status,
        "site": {
            "site_id": "synthetic-fixture-site",
            "label": "Synthetic fixture site",
            "pack_digest": digest("synthetic-fixture-pack"),
            "synthetic": True,
        },
        "question": {
            "original": original,
            "resolved": resolved,
            "bindings": {"aoi_ids": ["target"], "fixture": True},
        },
        "answer": {
            "headline": headline,
            "detail": "Synthetic renderer fixture; not evidence about a real place.",
            "evidence_classes": evidence_classes,
        },
        "visuals": visuals,
        "limitations": [
            limitation(
                "synthetic-data",
                "This result uses synthetic test data and is not evidence about a real place.",
                severity="info",
            ),
            *(limitations or []),
        ],
        "actions": actions or [],
        "audit": {
            "audit_id": f"fixture-audit-{key}",
            "source_versions": [{
                "source_id": "synthetic-fixture-source",
                "version": "1",
                "digest": digest("synthetic-fixture-source"),
                "synthetic": True,
            }],
            "capability_runs": [{
                "capability_id": capability,
                "version": "1.0.0",
                "status": "partial" if status == "partial" else (
                    "blocked" if status == "blocked" else "complete"
                ),
            }],
            "query_hash": digest(f"fixture-query-{key}"),
        },
    }


def fixtures() -> dict[str, dict[str, Any]]:
    orientation = visual(
        "orientation-map", "map", "site-orientation", "Site and observed coverage",
        [
            layer("declared-aoi", "reported", "polygon", "Declared analysis area"),
            layer("event-density", "derived", "cell", "Indexed record density"),
        ],
        "The declared area contains records in 12 indexed cells.",
        {"indexed_cells": 12, "records": 148},
    )
    observed = visual(
        "observed-map", "map", "observed-points", "Where records are available",
        [layer("observations", "observed", "point", "Observed records")],
        "Thirty-two source-linked records are available.",
        {"records": 32, "sources": 2, "surveyed_cells": 9},
    )
    coverage = visual(
        "coverage-effort-map", "map", "coverage-and-effort",
        "Records and documented effort",
        [
            layer("coverage", "derived", "cell", "Record coverage"),
            layer("effort", "observed", "line", "Documented survey effort"),
        ],
        "Effort is documented in 7 of the 12 cells containing records.",
        {"record_cells": 12, "effort_cells": 7},
    )
    empty_limit = limitation(
        "no-target-records",
        "No admitted records fall inside the target area; this is not evidence of absence.",
        affects=["surrounding-map", "answer"],
    )
    surrounding = visual(
        "surrounding-map", "map", "surrounding-data",
        "Where data exists around the target",
        [
            layer("target-aoi", "reported", "polygon", "Target area"),
            layer("surrounding-records", "observed", "point", "Surrounding records"),
        ],
        "No target records were returned; 27 records are available in the context area.",
        {"target_records": 0, "context_records": 27},
        status="partial", limitations=[empty_limit],
    )
    modelled = visual(
        "transfer-map", "map", "donor-target-gates", "Transferred estimate and uncertainty",
        [
            layer("donor-records", "observed", "point", "Donor observations"),
            layer("estimate", "modelled", "raster", "Modelled estimate"),
            layer("uncertainty", "modelled", "raster", "Model uncertainty"),
        ],
        "The registered transfer gate passed for 68 target cells.",
        {"donor_records": 84, "target_cells": 68, "holdout_rows": 21},
    )
    gate_limit = limitation(
        "transfer-gate-failed",
        "Environmental support did not cover enough of the target; no estimate is shown.",
        severity="error", affects=["failed-gate-map", "answer"],
    )
    failed_gate = visual(
        "failed-gate-map", "map", "donor-target-gates",
        "Donor coverage and failed transfer gate",
        [
            layer("failed-donor-records", "observed", "point", "Donor observations"),
            layer("unsupported-target", "missing", "cell", "Unsupported target cells"),
        ],
        "Observed donor records remain visible, but the estimate was blocked.",
        {"donor_records": 19, "supported_target_fraction": 0.31},
        status="partial", limitations=[gate_limit],
    )
    request_map = visual(
        "data-request-map", "map", "value-of-information",
        "Where another measurement would help most",
        [
            layer("uncertainty-surface", "modelled", "raster", "Current uncertainty"),
            layer("candidate-actions", "designed", "point", "Candidate collection locations"),
        ],
        "Eight candidate locations are ranked by expected information gain.",
        {"candidate_locations": 8, "accessible_locations": 6},
    )
    time_series = visual(
        "time-series", "chart", "metric-time-series", "Metric through time",
        [
            layer(
                "metric-series", "observed", "series", "Monthly measurements",
                "application/json",
            ),
            layer(
                "coverage-strip", "derived", "series", "Monthly coverage",
                "application/json",
            ),
        ],
        "The chart contains 60 monthly values with units and coverage.",
        {"months": 60, "missing_months": 3, "sources": 1},
    )
    outage_limit = limitation(
        "source-refresh-failed",
        "One source refresh failed; last-known-good records remain visible.",
        affects=["outage-map", "answer"],
    )
    outage = visual(
        "outage-map", "map", "source-coverage", "Available source coverage",
        [layer("last-known-good", "observed", "point", "Last-known-good records")],
        "Two sources are current and one is serving its last-known-good version.",
        {"current_sources": 2, "stale_sources": 1},
        status="partial", limitations=[outage_limit],
    )
    dashboard = visual(
        "dashboard", "dashboard", "composed-results", "Investigation dashboard",
        [
            layer("result-cards", "derived", "none", "Immutable prior results",
                  "application/json"),
        ],
        "The dashboard composes four immutable prior results.",
        {"results": 4, "maps": 2, "charts": 1, "gaps": 1},
        drilldown=False,
    )

    return {
        "01-site-orientation.json": result(
            "site-orientation", "Tell me about this site.",
            "Orient the user to the declared AOI and indexed source coverage.",
            "The site has records in 12 indexed cells.",
            ["reported", "derived"], [orientation],
            capability="site-orientation",
            actions=[action(
                "inspect-coverage", "drilldown", "Inspect source coverage",
                "source-coverage", {},
            )],
        ),
        "02-observed-points.json": result(
            "observed-points", "Where has this entity been recorded?",
            "Map admitted observations for the resolved entity.",
            "Thirty-two source-linked records are available.",
            ["observed"], [observed], capability="entity-record-map",
        ),
        "03-coverage-effort.json": result(
            "coverage-effort", "Where are there records and survey effort?",
            "Compare record coverage with explicit effort denominators.",
            "Documented effort covers 7 of 12 record cells.",
            ["observed", "derived"], [coverage], capability="coverage-versus-effort",
        ),
        "04-empty-target-surrounding.json": result(
            "empty-target-surrounding", "Is this entity present at the site?",
            "Check the target first, then show admitted data in the context area.",
            "No target records were returned; surrounding data is available.",
            ["observed", "missing"], [surrounding], status="partial",
            limitations=[empty_limit], capability="entity-record-map",
            actions=[action(
                "test-transfer", "run_capability", "Test transfer to the target",
                "gated-transfer", {"donor_scope": "context", "target_scope": "target"},
            )],
        ),
        "05-modelled-passing-gates.json": result(
            "modelled-passing-gates", "Can surrounding data be transferred here?",
            "Run the registered transfer model and disclose all gates.",
            "The transfer gate passed; estimate and uncertainty are available.",
            ["observed", "modelled"], [modelled], capability="gated-transfer",
        ),
        "06-failed-gate.json": result(
            "failed-gate", "Can surrounding data be transferred here?",
            "Run the registered transfer model and retain valid donor evidence if a gate fails.",
            "The transfer gate failed; observed donor coverage remains available.",
            ["observed", "missing"], [failed_gate], status="partial",
            limitations=[gate_limit], capability="gated-transfer",
            actions=[action(
                "request-model", "request_model", "Request a model for this target",
                "request-model", {"failed_gate": "environmental-support"},
            )],
        ),
        "07-data-request.json": result(
            "data-request", "Where should the next survey happen?",
            "Rank feasible collection locations using a versioned uncertainty surface.",
            "Eight candidate locations are ranked for additional collection.",
            ["modelled", "designed"], [request_map], capability="value-of-information",
            actions=[action(
                "submit-data-request", "request_data", "Submit this data request",
                "request-data", {"candidate_layer": "candidate-actions"},
            )],
        ),
        "08-time-series.json": result(
            "time-series", "How has this metric changed through time?",
            "Plot unit-compatible measurements with an explicit coverage strip.",
            "Sixty monthly values are available; three months are missing.",
            ["observed", "derived"], [time_series], capability="metric-time-series",
        ),
        "09-partial-source-outage.json": result(
            "partial-source-outage", "Show current source coverage.",
            "Show last-known-good evidence and disclose failed source refreshes.",
            "Most coverage is current; one source refresh failed.",
            ["observed"], [outage], status="partial", limitations=[outage_limit],
            capability="source-coverage",
        ),
        "10-dashboard.json": result(
            "dashboard", "Summarise this investigation as a dashboard.",
            "Compose immutable prior results without recomputing their evidence.",
            "Four audited results are ready in one dashboard.",
            ["derived"], [dashboard], capability="compose-dashboard",
            actions=[action(
                "export-report", "export_report", "Export an audited report",
                "export-report", {"result_ids": ["fixture-a", "fixture-b"]},
            )],
        ),
    }


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for path in OUTPUT.glob("*.json"):
        path.unlink()
    values = fixtures()
    values.update({
        "activity-01-query.json": {
            "schema_version": "idli-activity/1",
            "request_id": "fixture-request-observed-points",
            "phase": "query",
            "label": "Finding admitted records",
            "capability_id": "entity-record-map",
            "state": "running",
            "sequence": 1,
        },
        "activity-02-compute.json": {
            "schema_version": "idli-activity/1",
            "request_id": "fixture-request-modelled-passing-gates",
            "phase": "compute",
            "label": "Testing transfer gates",
            "capability_id": "gated-transfer",
            "state": "running",
            "sequence": 2,
        },
        "activity-03-complete.json": {
            "schema_version": "idli-activity/1",
            "request_id": "fixture-request-modelled-passing-gates",
            "phase": "publish",
            "label": "Visual result ready",
            "capability_id": "gated-transfer",
            "state": "complete",
            "sequence": 3,
        },
    })
    for name, value in values.items():
        (OUTPUT / name).write_text(
            json.dumps(value, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
