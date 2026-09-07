"""API-level tests for the `/api/settings/*` endpoints (FR-1/FR-2, I/O matrix).

Note on "Reject": rejecting a proposal has no backend endpoint at all --
the frontend simply discards the card and never calls `/api/settings/apply`.
That "no filesystem write on reject" behavior is therefore covered here only
indirectly, by every other test confirming that ONLY `/api/settings/apply`
ever touches `.claude/` (see `test_apply_never_touches_other_files` and the
propose tests below, none of which write anything).
"""

from pathlib import Path

import httpx2
import pytest
from anthropic import APIConnectionError
from fastapi.testclient import TestClient

from brain.settings_router.models import SettingAction, SettingsRouterOutput
from gateway.main import app, get_anthropic_client, get_claude_dir


@pytest.fixture
def api_client(claude_dir: Path) -> TestClient:
    app.dependency_overrides[get_claude_dir] = lambda: claude_dir
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_claude_dir, None)
        app.dependency_overrides.pop(get_anthropic_client, None)


@pytest.fixture
def mock_anthropic(make_fake_client):
    """Overrides the gateway's Anthropic dependency for the duration of one test."""

    def _mock(output: SettingsRouterOutput | None = None, error: Exception | None = None) -> None:
        app.dependency_overrides[get_anthropic_client] = lambda: make_fake_client(output=output, error=error)

    return _mock


# ---- POST /api/settings/propose -----------------------------------------


def test_propose_returns_one_card_per_action(api_client: TestClient, claude_dir: Path, mock_anthropic) -> None:
    mock_anthropic(
        output=SettingsRouterOutput(
            user_summary="Creates a rule file with your testing guidance.",
            updates=[
                SettingAction(
                    target_category="rule",
                    file_path="testing",
                    content="Always use pytest for test files.",
                    action="create",
                )
            ],
        )
    )

    response = api_client.post("/api/settings/propose", json={"request": "always use pytest"})

    assert response.status_code == 200
    body = response.json()
    assert body["user_summary"]
    assert len(body["updates"]) == 1
    card = body["updates"][0]
    assert card["target_category"] == "rule"
    assert card["file_path"] == ".claude/rules/testing.md"
    assert card["action"] == "create"
    assert card["content"] == "Always use pytest for test files."
    # Nothing written yet -- propose never touches .claude/.
    assert list(claude_dir.iterdir()) == []


def test_propose_multiple_actions_returns_multiple_cards(api_client: TestClient, mock_anthropic) -> None:
    mock_anthropic(
        output=SettingsRouterOutput(
            user_summary="Adds a testing rule and ignores .env in settings.",
            updates=[
                SettingAction(target_category="rule", file_path="testing", content="a", action="create"),
                SettingAction(target_category="settings.json", file_path="settings.json", content="{}", action="update"),
            ],
        )
    )

    response = api_client.post(
        "/api/settings/propose", json={"request": "always use pytest, never commit .env"}
    )

    assert response.status_code == 200
    assert len(response.json()["updates"]) == 2


def test_propose_no_op_request_returns_friendly_empty_state(api_client: TestClient, mock_anthropic) -> None:
    mock_anthropic(
        output=SettingsRouterOutput(user_summary="That's already the default -- nothing to change.", updates=[])
    )

    response = api_client.post("/api/settings/propose", json={"request": "be nice"})

    assert response.status_code == 200
    body = response.json()
    assert body["updates"] == []
    assert body["user_summary"]


def test_propose_llm_failure_returns_error_envelope(api_client: TestClient, claude_dir: Path, mock_anthropic) -> None:
    mock_anthropic(error=APIConnectionError(request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages")))

    response = api_client.post("/api/settings/propose", json={"request": "always use pytest"})

    assert response.status_code == 502
    body = response.json()
    assert set(body.keys()) == {"error_code", "message", "node_id"}
    assert body["node_id"] is None
    assert body["message"]
    # No partial writes on failure.
    assert list(claude_dir.iterdir()) == []


def test_propose_missing_credentials_returns_error_envelope(api_client: TestClient, claude_dir: Path, mock_anthropic) -> None:
    """No ANTHROPIC_API_KEY configured (the local-dev default) surfaces the same
    error envelope as any other LLM failure, not a raw 500 with no CORS headers."""
    mock_anthropic(error=TypeError("Could not resolve authentication method."))

    response = api_client.post("/api/settings/propose", json={"request": "always use pytest"})

    assert response.status_code == 502
    body = response.json()
    assert set(body.keys()) == {"error_code", "message", "node_id"}
    assert body["node_id"] is None
    assert list(claude_dir.iterdir()) == []


# ---- POST /api/settings/apply --------------------------------------------


def test_apply_writes_previewed_file_exactly(api_client: TestClient, claude_dir: Path) -> None:
    response = api_client.post(
        "/api/settings/apply",
        json={
            "target_category": "rule",
            "file_path": ".claude/rules/testing.md",
            "content": "Always use pytest for test files.",
            "action": "create",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "applied"
    written = claude_dir / "rules" / "testing.md"
    assert written.read_text(encoding="utf-8") == "Always use pytest for test files."


def test_apply_never_touches_other_files(api_client: TestClient, claude_dir: Path) -> None:
    (claude_dir / "CLAUDE.md").write_text("untouched", encoding="utf-8")

    api_client.post(
        "/api/settings/apply",
        json={
            "target_category": "rule",
            "file_path": ".claude/rules/testing.md",
            "content": "x",
            "action": "create",
        },
    )

    assert (claude_dir / "CLAUDE.md").read_text(encoding="utf-8") == "untouched"


def test_apply_rejects_path_escape_before_any_write(api_client: TestClient, claude_dir: Path) -> None:
    response = api_client.post(
        "/api/settings/apply",
        json={
            "target_category": "rule",
            "file_path": ".claude/../../etc/passwd",
            "content": "pwned",
            "action": "create",
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert set(body.keys()) == {"error_code", "message", "node_id"}
    assert body["node_id"] is None
    assert list(claude_dir.iterdir()) == []


def test_apply_rejects_category_path_mismatch(api_client: TestClient, claude_dir: Path) -> None:
    """A client pairing an in-bounds file_path with a mismatched target_category must
    be rejected end-to-end through the endpoint, not just at the apply_action() call site."""
    (claude_dir / "CLAUDE.md").write_text("original", encoding="utf-8")

    response = api_client.post(
        "/api/settings/apply",
        json={
            "target_category": "rule",
            "file_path": ".claude/CLAUDE.md",
            "content": "pwned",
            "action": "update",
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert set(body.keys()) == {"error_code", "message", "node_id"}
    assert body["node_id"] is None
    assert (claude_dir / "CLAUDE.md").read_text(encoding="utf-8") == "original"


def test_apply_filesystem_failure_returns_error_envelope(api_client: TestClient, claude_dir: Path) -> None:
    """A path colliding with an existing directory of the same name fails at the
    filesystem level -- the endpoint must surface the app's error envelope, not a
    raw unhandled 500."""
    (claude_dir / "rules" / "testing.md").mkdir(parents=True)

    response = api_client.post(
        "/api/settings/apply",
        json={
            "target_category": "rule",
            "file_path": ".claude/rules/testing.md",
            "content": "Always use pytest.",
            "action": "create",
        },
    )

    assert response.status_code == 500
    body = response.json()
    assert set(body.keys()) == {"error_code", "message", "node_id"}
    assert body["error_code"] == "settings.io_error"
    assert body["node_id"] is None


def test_propose_returns_error_envelope_when_parsed_output_is_none(
    api_client: TestClient, claude_dir: Path, mock_anthropic
) -> None:
    """`response.parsed_output` being None must surface as the app's error envelope
    (502), not a raw unhandled 500."""
    mock_anthropic(output=None)

    response = api_client.post("/api/settings/propose", json={"request": "always use pytest"})

    assert response.status_code == 502
    body = response.json()
    assert set(body.keys()) == {"error_code", "message", "node_id"}
    assert body["node_id"] is None
    assert list(claude_dir.iterdir()) == []
