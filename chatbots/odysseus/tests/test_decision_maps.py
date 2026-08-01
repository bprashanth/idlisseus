"""TR-VIS-0008 + IDL-REQ-0004 — validated decision maps and the Themes centre.

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


def test_themes_centre_runs_ready_and_partial_but_not_unready():
    """TR-VIS-0009: catalogue readiness is not validation. `ready` and `partial`
    both run — a partial returns measured evidence and the places worth
    checking. `awaiting-validation-data` and `blocked` stay readiness views."""
    src = read("static/js/visual/visualThemes.js")
    assert "decisionMaps()" in src, "the centre must read the producer catalogue"
    assert "RUNNABLE = new Set(['ready', 'partial'])" in src
    row = src.split("function themeRow(", 1)[1].split("\nfunction ", 1)[0]
    ready_branch, open_branch = row.split("if (RUNNABLE.has(recipe.status))", 1)[1].split("} else {", 1)
    assert "eco-theme-open" in ready_branch
    assert "eco-theme-open" not in open_branch
    assert "eco-theme-missing" in open_branch, "an unrunnable theme must say what is missing"
    # A partial is described as evidence, never as an admitted decision model.
    assert "It does not recommend action." in ready_branch
    assert "Evidence, not yet an answer" in src
    # Grouping comes from the producer's generic theme field, never a recipe id.
    assert "r.theme" in src or "recipe.theme" in src
    assert "recipe_id ===" not in src, "the centre must not dispatch on a recipe id"


def test_validation_priorities_are_requests_for_evidence_not_recommendations():
    """TR-VIS-0009: a validation priority survives a failed test (it is what
    would settle it) and never wears the selected-budget collar."""
    themes = read("static/js/visual/visualThemes.js")
    for renderer in ("static/js/visual/visualMap.js", "static/js/visual/visualLeaflet.js"):
        src = read(renderer)
        assert "validation_priority_field" in src, f"{renderer} ignores validation priorities"
        # Dashed, not the solid collar: distinguishable without colour.
        assert "dashArray" in src or "stroke-dasharray" in src
        # Never gated on suppressSelection — a failed test still asks for evidence.
        prio = src.split("validation_priority_field", 1)[1][:200]
        assert "suppressSelection" not in prio
    # Verbal as well as visual, in both renderers and under the map.
    assert "check or collect evidence here" in read("static/js/visual/visualMap.js")
    assert "check or collect evidence here" in read("static/js/visual/visualLeaflet.js")
    assert "not a recommendation" in themes


def test_themes_show_the_recurring_question_not_a_map_name():
    src = read("static/js/visual/visualThemes.js")
    row = src.split("function themeRow(", 1)[1].split("\nfunction ", 1)[0]
    # The heading is the producer's first question, with the recipe title only
    # as a fallback.
    assert "questions[0] || recipe.title" in row
    assert "eco-theme-alt" in row, "the other phrasings evidence that it recurs"


def test_solution_writeup_is_labelled_as_the_packs_own_words():
    """No author prose exists yet (IDL-REQ-0004); the consumer must not pass
    the pack's contract sentences off as somebody's analysis."""
    src = read("static/js/visual/visualThemes.js")
    assert "Author write-ups are not published by this pack yet." in src
    assert "eco-solution-src" in src
    # No byline is fabricated: nothing reads an author field that the contract
    # does not carry yet, and the credit line says where the words came from.
    assert ".author" not in src
    assert "Published in this site pack" in src


def test_open_in_chat_fills_the_composer_and_never_sends():
    shell = read("static/js/visual/visualShell.js")
    hook = shell.split("async function carryThemeIntoChat(", 1)[1].split("\n}\n", 1)[0]
    assert "input.value = seed" in hook
    assert "input.focus()" in hook
    # The reader presses send; nothing here does it for them.
    assert "keyboard" not in hook and ".submit(" not in hook


def test_author_declared_basemap_is_honoured_through_the_proxy():
    """IDL-REQ-0004: the publishing author's basemap survives, an unknown id
    degrades to the default, and tiles never leave the same-origin proxy."""
    leaflet = read("static/js/visual/visualLeaflet.js")
    assert "hooks.basemap" in leaflet
    assert "declared !== 'none'" in leaflet
    # Unknown ids fall through to the reader/default base rather than throwing.
    assert "if (BASES[declared])" in leaflet
    # Every basemap is proxied.
    assert "/api/visual/tiles/" in leaflet
    assert "https://" not in leaflet.split("const BASES", 1)[1].split("};", 1)[0]
    # The author's choice must not overwrite the reader's global preference.
    assert "!authored" in leaflet
    assert "basemap" in read("static/js/visual/visualRenderers.js")


def test_catalogue_fixture_matches_the_live_producer_shape():
    """TR-VIS-0009 asked for the superseded two-ready/five-waiting snapshot to
    be replaced by the current four-ready/three-partial catalogue."""
    cat = json.loads((FIXTURES / "decision-map-catalog.json").read_text(encoding="utf-8"))
    statuses = [r["status"] for r in cat["recipes"]]
    assert statuses.count("ready") == 4
    assert statuses.count("partial") == 3
    # Every recipe now carries a published field note.
    for r in cat["recipes"]:
        pa = r.get("published_answer")
        assert pa, f"{r['recipe_id']} has no published_answer"
        assert pa["publication"]["status"] == "published"
        assert pa.get("standfirst") and pa.get("recommendation")


def test_proxy_exposes_the_catalogue_route():
    routes = read("routes/visual_routes.py")
    assert '"/{endpoint_id}/decision-maps"' in routes
    assert '"/v1/decision-maps"' in routes


def test_lab_registers_the_decision_map_fixtures():
    lab = read("static/js/visual/visualLab.js")
    for name in (PASSED, FAILED, HOLDOUT):
        assert name in lab


def test_open_in_chat_carries_the_answer_not_just_the_question():
    """From a reading view the published answer travels into the conversation:
    the card renders from the marker, the facts behind it go into the
    transcript, and the composer opens naming the analysis — the assistant
    resolves a visual by identifier, so an unanchored "this" only earns a
    "which visual do you mean?"."""
    themes = read("static/js/visual/visualThemes.js")
    shell = read("static/js/visual/visualShell.js")
    # The briefing is producer text: method, test, sources with DOIs, basemap.
    brief = themes.split("function briefing(", 1)[1].split("\n}", 1)[0]
    for fact in ("recipe.decision", "product.modelled", "val.method", "source_versions",
                 "sv.doi", "Basemap", "limitations"):
        assert fact in brief, f"briefing omits {fact}"
    assert "not worked out in this conversation" in brief, "provenance must be stated"
    # It is added to the transcript AND persisted, so the next turn sees it.
    carry = shell.split("async function carryThemeIntoChat(", 1)[1].split("\n}\n", 1)[0]
    assert "idli-result:" in carry, "no marker means no card"
    assert "addMessage('assistant'" in carry
    assert "/message" in carry and "'POST'" in carry
    assert "materializePendingSession" in carry, "a pending chat has nowhere to store it"
    # The reader's question is never sent for them.
    assert "keyboard" not in carry and "submit" not in carry
    # From the index, only the question travels (nothing has run yet).
    assert "onOpenInChat({ question:" in themes


def test_published_field_note_replaces_the_assembled_writeup():
    """TR-VIS-0010: when the pack publishes an article, it is the answer — and
    it is bound to the arguments it was written about."""
    src = read("static/js/visual/visualThemes.js")
    assert "published_answer" in src
    # Only a published article is used, and only for its own arguments.
    pub = src.split("export function publishedAnswer(", 1)[1].split("\n}", 1)[0]
    assert "publication || {}).status !== 'published'" in pub
    assert "default_arguments" in pub, "a rerun must not reuse the default article"
    # The old assembly survives as the fallback for packs without one.
    assert "function renderAssembledWriteup(" in src
    assert "if (pa) renderFieldNote(" in src and "else renderAssembledWriteup(" in src
    note = src.split("function renderFieldNote(", 1)[1].split("\nconst ROLE_WORDS", 1)[0]
    # Producer order: what to do, where, measured, estimated, tested, why.
    for section in ("What to do now", "What was measured", "What was estimated",
                    "How the estimate was tested", "Why we are not giving stronger advice"):
        assert section in note, f"missing section: {section}"
    assert "est.name" in note and "est.plain_language" in note
    # Outcome is a word, and roles are generic wording only.
    assert "outcomeWords(test.outcome)" in note
    assert "ROLE_WORDS[spot.role]" in note
    # Prose is inserted as text; nothing is parsed as markup.
    assert "innerHTML" not in note
    # Contributors are shown only when supplied.
    assert "(pub.contributors || []).filter(Boolean)" in note


def test_named_locations_focus_the_map_without_recomputing():
    themes = read("static/js/visual/visualThemes.js")
    dm = read("static/js/visual/visualDecisionMap.js")
    assert "focusNamedLocation" in themes and "export function focusNamedLocation" in dm
    fn = dm.split("export function focusNamedLocation(", 1)[1].split("\n}", 1)[0]
    # Matches a producer id in any property: the key name is the pack's business.
    assert "Object.values" in fn
    # It pans and flashes; it never queries, recomputes or writes a value.
    assert "panTo" in fn
    for forbidden in ("query(", "fetch(", "setStyle({ fill"):
        assert forbidden not in fn, f"focus must not {forbidden}"
    # A missing id stays readable text rather than throwing.
    assert "if (!hit) return false" in fn
    assert "is-missing" in themes


def test_open_in_chat_carries_the_published_note_when_there_is_one():
    src = read("static/js/visual/visualThemes.js")
    assert "function publishedBriefing(" in src
    brief = src.split("function publishedBriefing(", 1)[1].split("\n}", 1)[0]
    for part in ("standfirst", "what_was_measured", "est.name", "test.plain_language",
                 "recommendation", "why_this_advice", "location_id", "result_id"):
        assert part in brief, f"briefing omits {part}"
    # The mechanical assembly is not used when an article exists.
    assert "if (pa) return publishedBriefing(pa, recipe, env);" in src
