from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_idli_insight_history_parser_strips_legacy_trace_and_extracts_skills():
    renderer = (ROOT / "static/js/chatRenderer.js").read_text(encoding="utf-8")
    assert "export function parseInsightResponse" in renderer
    assert "Codex CLI\\s*·\\s*native skill trace" in renderer
    assert "Why\\s*·\\s*\\d+\\s*skills?\\s*used" in renderer
    assert "Invoke skill:" in renderer
    assert "compactSkillPattern" in renderer
    assert "idli-insight:" in renderer
    assert "idli-skill:" in renderer
    assert "idli-progress:" in renderer
    assert "idli-actions:" in renderer
    assert "source.slice(0, legacy.index)" in renderer


def test_idli_insight_panel_uses_text_nodes_for_untrusted_skill_names():
    renderer = (ROOT / "static/js/chatRenderer.js").read_text(encoding="utf-8")
    assert "export function renderInsightTrace" in renderer
    assert "name.textContent = skill.name" in renderer
    assert "audit.textContent = `Audit ${normal.audit_id}`" in renderer
    assert "navigator.clipboard.writeText(normal.audit_id)" in renderer


def test_idli_insight_live_handler_uses_compact_event_not_generic_tool_cards():
    chat = (ROOT / "static/js/chat.js").read_text(encoding="utf-8")
    assert "json.type === 'insight_skill'" in chat
    assert "spinner.updateMessage(`Using ${skillName}`)" in chat
    assert "const compatMarkers" in chat
    assert ".matchAll(/<!--\\s*idli-(progress|skill|actions):" in chat
    assert "appendInsightActivity" in chat
    assert "chatRenderer.renderAskUserCard(payload)" in chat


def test_idli_insight_guided_actions_reuse_durable_choice_card():
    renderer = (ROOT / "static/js/chatRenderer.js").read_text(encoding="utf-8")
    routes = (ROOT / "routes/chat_routes.py").read_text(encoding="utf-8")
    assert "function _normaliseInsightActions" in renderer
    assert "metadata?.insight_actions" in renderer
    assert "renderAskUserCard(metadata.insight_actions" in renderer
    assert 'event_type == "insight_actions"' in routes
    assert '"type": "ask_user", "data": _bridge_insight_actions' in routes
    assert 'last_metrics["insight_actions"]' in routes


def test_idli_insight_model_request_is_explicit_and_file_backed():
    renderer = (ROOT / "static/js/chatRenderer.js").read_text(encoding="utf-8")
    assert "export function renderT4GCModelRequest" in renderer
    assert "Request this model from T4GC" in renderer
    assert "Use the request-model-from-t4gc skill" in renderer
    assert "response variable, candidate predictors" in renderer
    assert "measurable validation target" in renderer
    assert "send.click()" in renderer


def test_idli_insight_why_command_opens_latest_audit():
    commands = (ROOT / "static/js/slashCommands.js").read_text(encoding="utf-8")
    assert "async function _cmdWhy" in commands
    assert "document.querySelectorAll('.msg-assistant .insight-why')" in commands
    assert "usage: '/why'" in commands


def test_idli_insight_panel_has_mobile_layout():
    style = (ROOT / "static/style.css").read_text(encoding="utf-8")
    assert ".insight-why" in style
    assert ".insight-live-activity-log" in style
    assert ".insight-skill-result" in style
    assert ".insight-model-request-btn" in style
    assert ".ask-user-option {" in style
    assert "height: auto;" in style
    assert "@media (max-width: 600px)" in style
    assert ".insight-skill code { white-space: normal; overflow-wrap: anywhere; }" in style
