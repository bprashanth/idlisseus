"""TR-VIS-0008 — validated decision maps, consumer side.

These are contract tests against the shipped fixtures and the modules that
render them. They do not need the producer to be running: the fixtures are
real producer output (a passed temporal hindcast, a failed one, a spatial
holdout) captured from the live Valparai pack, payloads included.
"""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "static/contracts/fixtures"

PASSED = "12-decision-map-hindcast-passed"
FAILED = "13-decision-map-hindcast-failed"
HOLDOUT = "14-decision-map-spatial-holdout"


def envelope(name):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


# ---- the fixtures themselves ------------------------------------------------

@pytest.mark.parametrize("name", [PASSED, FAILED, HOLDOUT])
def test_fixture_is_a_validated_decision_map(name):
    env = envelope(name)
    views = {v.get("view") for v in env["visuals"]}
    assert "validated-decision-map" in views
    assert "validation-summary" in views, "the test must travel with the map"
    assert env["answer"]["validation"]["status"] in {"passed", "failed"}


@pytest.mark.parametrize("name", [PASSED, FAILED, HOLDOUT])
def test_every_fixture_payload_is_committed(name):
    """A fresh clone must render the lab with no backend running."""
    env = envelope(name)
    refs = [
        layer["data_ref"]
        for v in env["visuals"] for layer in (v.get("layers") or [])
        if layer.get("data_ref", {}).get("kind") == "result_data"
    ]
    assert refs, "fixture references no payloads"
    for ref in refs:
        suffix = ".geojson" if ref.get("media_type") == "application/geo+json" else ".json"
        path = FIXTURES / "data" / env["result_id"] / f"{ref['handle']}{suffix}"
        assert path.is_file(), f"missing payload {path.name} for {name}"
        assert path.stat().st_size > 0


def test_passed_hindcast_selects_places_and_withholds_observations():
    env = envelope(PASSED)
    val = env["answer"]["validation"]
    assert val["status"] == "passed"
    assert all(c["passed"] for c in val["checks"].values())
    layers = [l for v in env["visuals"] for l in (v.get("layers") or [])]
    # The producer separates fitting from withheld observations by style role,
    # not by evidence class — both are observed, so colour cannot carry it.
    roles = {l["layer_id"]: (l.get("style_hint") or {}).get("palette_role") for l in layers}
    assert "validation" in roles.values(), "no withheld-observation layer"
    observed = [l for l in layers if l.get("evidence_class") == "observed"]
    assert len({(l.get("style_hint") or {}).get("palette_role") for l in observed}) > 1
    # A budget selection exists and is flagged by a declared field.
    selected = [l for l in layers if (l.get("style_hint") or {}).get("selected_field")]
    assert selected, "no layer declares a selected_field"
    handle = selected[0]["data_ref"]["handle"]
    fc = json.loads((FIXTURES / "data" / env["result_id"] / f"{handle}.geojson").read_text())
    field = (selected[0]["style_hint"])["selected_field"]
    chosen = [f for f in fc["features"] if f["properties"].get(field)]
    assert chosen, "passed hindcast selected nothing"


def test_failed_hindcast_keeps_evidence_and_selects_nothing():
    """A failed test is a product: evidence stays, recommendation goes."""
    env = envelope(FAILED)
    val = env["answer"]["validation"]
    assert val["status"] == "failed"
    assert any(not c["passed"] for c in val["checks"].values()), "nothing actually failed"
    assert any(c["passed"] for c in val["checks"].values()), "fixture should show mixed checks"
    layers = [l for v in env["visuals"] for l in (v.get("layers") or [])]
    # The observed and withheld layers survive the failure.
    assert any((l.get("style_hint") or {}).get("palette_role") == "validation" for l in layers)
    assert sum(1 for l in layers if l.get("evidence_class") == "observed") >= 2
    # The producer emits no selected place. The consumer additionally refuses
    # to style one (see test_consumer_refuses_to_style_selection_without_pass).
    selected = [l for l in layers if (l.get("style_hint") or {}).get("selected_field")]
    for layer in selected:
        handle = layer["data_ref"]["handle"]
        fc = json.loads((FIXTURES / "data" / env["result_id"] / f"{handle}.geojson").read_text())
        field = layer["style_hint"]["selected_field"]
        assert not [f for f in fc["features"] if f["properties"].get(field)], \
            "a failed test must not select any place"


def test_spatial_holdout_withholds_whole_named_groups():
    env = envelope(HOLDOUT)
    val = env["answer"]["validation"]
    assert val["kind"] == "spatial-holdout"
    # Whole named units, not random neighbouring rows.
    blob = json.dumps(val).lower()
    assert "landscape" in blob or "group" in blob


# ---- the consumer treatment -------------------------------------------------

def read(*parts):
    return (ROOT.joinpath(*parts)).read_text(encoding="utf-8")


def test_consumer_refuses_to_style_selection_without_pass():
    """selectionAllowed gates on a passed status, and both map renderers honour
    the resulting suppressSelection hook."""
    mod = read("static/js/visual/visualDecisionMap.js")
    assert "export function selectionAllowed" in mod
    assert "v.status === 'passed'" in mod
    for renderer in ("static/js/visual/visualMap.js", "static/js/visual/visualLeaflet.js"):
        src = read(renderer)
        assert "suppressSelection" in src, f"{renderer} ignores the gate"
        assert "selected_field" in src
    # The hook must survive the renderVisual dispatch.
    assert "suppressSelection" in read("static/js/visual/visualRenderers.js")


def test_withheld_observations_are_distinguishable_without_colour():
    """Both renderers give the withheld-test layer its own mark (a crossed
    ring), because it shares an evidence class — and therefore a hue — with the
    observations used to fit."""
    svg = read("static/js/visual/visualMap.js")
    leaflet = read("static/js/visual/visualLeaflet.js")
    for src in (svg, leaflet):
        assert "palette_role === 'validation'" in src
    assert "viz-withheld-mark" in leaflet
    assert "'ring'" in svg  # legend swatch
    assert ".viz-legend-ring" in read("static/visual.css")


def test_validation_is_rendered_in_the_reading_flow_not_an_accordion():
    mod = read("static/js/visual/visualDecisionMap.js")
    assert "How this map was tested" in mod
    for host in ("static/js/visual/visualChat.js", "static/js/visual/visualStage.js"):
        src = read(host)
        assert "renderValidationPanel" in src, f"{host} never renders the test"
    # No <details>/summary wrapper around the panel.
    assert "<details" not in mod and "createElement('details')" not in mod
    # The stage must not leave the validation summary as a click-to-open card.
    stage = read("static/js/visual/visualStage.js")
    assert "v.view !== 'validation-summary'" in stage


def test_failed_state_says_plainly_that_nothing_is_recommended():
    mod = read("static/js/visual/visualDecisionMap.js")
    assert "no place is marked for action here" in mod
    assert "viz-validation-failnote" in mod


def test_maps_centre_is_catalogue_driven_and_waiting_cards_cannot_run():
    src = read("static/js/visual/visualMapsCentre.js")
    assert "decisionMaps()" in src, "the centre must read the producer catalogue"
    # Within the card builder, a run affordance exists only on the ready branch;
    # the waiting branch names the missing inputs instead.
    card_fn = src.split("function card(", 1)[1].split("\nfunction ", 1)[0]
    ready_branch, waiting_branch = card_fn.split("if (recipe.status === 'ready')", 1)[1].split("} else {", 1)
    assert "runRow(recipe" in ready_branch
    assert "runRow(" not in waiting_branch
    assert "eco-maps-run" not in waiting_branch
    assert "eco-maps-missing" in waiting_branch, "waiting cards must name what is missing"
    # Grouping comes from the producer's generic theme field, never a recipe id.
    assert "r.theme" in src or "recipe.theme" in src
    assert "recipe_id ===" not in src, "the centre must not dispatch on a recipe id"


def test_catalogue_fixture_covers_ready_and_waiting_recipes():
    cat = json.loads((FIXTURES / "decision-map-catalog.json").read_text(encoding="utf-8"))
    statuses = {r["status"] for r in cat["recipes"]}
    assert "ready" in statuses
    assert "awaiting-validation-data" in statuses
    waiting = [r for r in cat["recipes"] if r["status"] != "ready"]
    for r in waiting:
        missing = [i for i in r["required_inputs"] if i["status"] != "available"]
        assert missing, f"{r['recipe_id']} is not ready but names nothing missing"


def test_proxy_exposes_the_catalogue_route():
    routes = read("routes/visual_routes.py")
    assert '"/{endpoint_id}/decision-maps"' in routes
    assert '"/v1/decision-maps"' in routes


def test_lab_registers_the_decision_map_fixtures():
    lab = read("static/js/visual/visualLab.js")
    for name in (PASSED, FAILED, HOLDOUT):
        assert name in lab
