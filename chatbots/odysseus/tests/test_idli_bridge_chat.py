from routes.chat_routes import _idli_attachment_manifest, _idli_insight_event


class FakeUploadHandler:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def resolve_upload(self, upload_id, owner=None, auth_manager=None):
        self.calls.append((upload_id, owner, auth_manager))
        return self.result


def test_idli_attachment_manifest_uses_owner_aware_resolver(tmp_path):
    source = tmp_path / "sheet.xlsx"
    source.write_bytes(b"xlsx")
    auth = object()
    handler = FakeUploadHandler({
        "id": "abc.xlsx", "name": "Checklist.xlsx",
        "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "path": str(source),
    })

    result = _idli_attachment_manifest(handler, ["abc.xlsx"], "alice", auth)

    assert handler.calls == [("abc.xlsx", "alice", auth)]
    assert result == [{
        "id": "abc.xlsx", "name": "Checklist.xlsx",
        "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "path": str(source.resolve()),
    }]


def test_idli_attachment_manifest_drops_unauthorized_upload():
    handler = FakeUploadHandler(None)
    assert _idli_attachment_manifest(handler, ["secret.xlsx"], "alice") == []


def test_idli_insight_event_keeps_only_skill_name_status_and_audit_id():
    result = _idli_insight_event({
        "type": "insight_skill",
        "skill": "local-snake-inventory",
        "status": "done",
        "audit_id": "session-1/2",
        "command": "find /tmp/private",
        "output": "/tmp/private/file",
        "model": "private-backend",
    })
    assert result == {
        "type": "insight_skill",
        "skill": "local-snake-inventory",
        "status": "done",
        "audit_id": "session-1/2",
    }


def test_idli_insight_event_suppresses_progress_and_inspection_noise():
    assert _idli_insight_event({
        "type": "agent_step", "text": "I am checking files",
    }) is None


def test_idli_insight_event_keeps_sanitized_progress_milestone():
    assert _idli_insight_event({
        "type": "insight_progress", "phase": "read",
        "label": "Reading historical-fire-exposure", "command": "cat /tmp/private",
    }) == {
        "type": "insight_progress", "phase": "read",
        "label": "Reading historical-fire-exposure",
    }
    assert _idli_insight_event({
        "type": "tool_output", "kind": "command", "tool": "inspection",
        "command": "find /tmp/private", "output": "/tmp/private/file",
    }) is None


def test_idli_insight_event_sanitizes_legacy_skill_tool_event():
    assert _idli_insight_event({
        "type": "tool_output", "kind": "skill", "tool": "declared-site-centre",
        "command": "python /tmp/private/skill_call.py declared-site-centre",
        "output": "private rows", "exit_code": 0,
    }) == {
        "type": "insight_skill", "skill": "declared-site-centre", "status": "done",
    }
