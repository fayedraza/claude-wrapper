"""Unit + API-level tests for `brain.settings_router.summary` (FR-3, I/O matrix)."""

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from brain.settings_router.summary import get_current_configuration
from gateway.main import app, get_claude_dir


# ---- .claude/ doesn't exist yet ------------------------------------------


def test_no_claude_dir_returns_empty_summary(tmp_path: Path) -> None:
    missing = tmp_path / ".claude"
    assert not missing.exists()

    result = get_current_configuration(missing)

    assert result.items == []


# ---- rules ----------------------------------------------------------------


def test_rule_item_uses_first_non_empty_line_with_heading_stripped(claude_dir: Path) -> None:
    rules_dir = claude_dir / "rules"
    rules_dir.mkdir()
    (rules_dir / "architecture.md").write_text(
        "\n\n# Prefer FastAPI dependency injection over global state\n\nMore detail here.\n",
        encoding="utf-8",
    )

    result = get_current_configuration(claude_dir)

    assert len(result.items) == 1
    item = result.items[0]
    assert item.kind == "rule"
    assert item.text == "Prefer FastAPI dependency injection over global state"
    assert item.path == ".claude/rules/architecture.md"


def test_rule_item_falls_back_to_filename_when_file_is_empty(claude_dir: Path) -> None:
    rules_dir = claude_dir / "rules"
    rules_dir.mkdir()
    (rules_dir / "empty-rule.md").write_text("", encoding="utf-8")

    result = get_current_configuration(claude_dir)

    assert result.items[0].text == "empty-rule"


def test_multiple_rules_are_all_listed_sorted(claude_dir: Path) -> None:
    rules_dir = claude_dir / "rules"
    rules_dir.mkdir()
    (rules_dir / "b-rule.md").write_text("Second rule text.", encoding="utf-8")
    (rules_dir / "a-rule.md").write_text("First rule text.", encoding="utf-8")

    result = get_current_configuration(claude_dir)

    assert [item.path for item in result.items] == [".claude/rules/a-rule.md", ".claude/rules/b-rule.md"]


def test_no_rules_dir_yields_no_rule_items(claude_dir: Path) -> None:
    result = get_current_configuration(claude_dir)
    assert not any(item.kind == "rule" for item in result.items)


# ---- agents -----------------------------------------------------------------


def test_agent_item_uses_frontmatter_name_and_description(claude_dir: Path) -> None:
    agents_dir = claude_dir / "agents"
    agents_dir.mkdir()
    (agents_dir / "auth-scaffold-worker.md").write_text(
        "---\n"
        "name: auth_scaffold_worker\n"
        "description: specialized in OAuth2/JWT implementation\n"
        "---\n\n"
        "# Auth Scaffold Worker\n\nBody content.\n",
        encoding="utf-8",
    )

    result = get_current_configuration(claude_dir)

    assert len(result.items) == 1
    item = result.items[0]
    assert item.kind == "agent"
    assert item.text == "auth_scaffold_worker: specialized in OAuth2/JWT implementation"
    assert item.path == ".claude/agents/auth-scaffold-worker.md"


def test_agent_item_without_frontmatter_falls_back_to_filename_and_first_line(claude_dir: Path) -> None:
    agents_dir = claude_dir / "agents"
    agents_dir.mkdir()
    (agents_dir / "plain-agent.md").write_text("Handles plain markdown personas.\n", encoding="utf-8")

    result = get_current_configuration(claude_dir)

    assert result.items[0].text == "plain-agent: Handles plain markdown personas."


def test_agent_item_with_incomplete_frontmatter_falls_back(claude_dir: Path) -> None:
    """Frontmatter present but missing `name` or `description` -- falls back
    rather than emitting a partial/broken "None: None" string."""
    agents_dir = claude_dir / "agents"
    agents_dir.mkdir()
    (agents_dir / "partial.md").write_text(
        "---\nname: partial_agent\n---\n\nFallback first line.\n",
        encoding="utf-8",
    )

    result = get_current_configuration(claude_dir)

    assert result.items[0].text == "partial: Fallback first line."


def test_agent_item_with_malformed_frontmatter_does_not_crash(claude_dir: Path) -> None:
    agents_dir = claude_dir / "agents"
    agents_dir.mkdir()
    (agents_dir / "broken.md").write_text(
        "---\nname: [unterminated\n---\nFallback text.\n",
        encoding="utf-8",
    )

    result = get_current_configuration(claude_dir)

    assert len(result.items) == 1
    assert result.items[0].kind == "agent"


def test_no_agents_dir_yields_no_agent_items(claude_dir: Path) -> None:
    result = get_current_configuration(claude_dir)
    assert not any(item.kind == "agent" for item in result.items)


def test_multiple_agents_are_all_listed_sorted(claude_dir: Path) -> None:
    agents_dir = claude_dir / "agents"
    agents_dir.mkdir()
    (agents_dir / "b-agent.md").write_text("Second agent.", encoding="utf-8")
    (agents_dir / "a-agent.md").write_text("First agent.", encoding="utf-8")

    result = get_current_configuration(claude_dir)

    assert [item.path for item in result.items] == [".claude/agents/a-agent.md", ".claude/agents/b-agent.md"]


# ---- permission grants ------------------------------------------------------


def test_no_permission_grants_key_yields_no_grant_rows(claude_dir: Path) -> None:
    """Today's reality: settings.json has no `permissionGrants` key (e.g. only
    a `hooks` block) -- the section is correctly empty, not an error."""
    (claude_dir / "settings.json").write_text(json.dumps({"hooks": {}}), encoding="utf-8")

    result = get_current_configuration(claude_dir)

    assert not any(item.kind == "mcp" for item in result.items)


def test_no_settings_json_at_all_yields_no_grant_rows(claude_dir: Path) -> None:
    result = get_current_configuration(claude_dir)
    assert not any(item.kind == "mcp" for item in result.items)


def test_permission_grants_present_are_rendered_as_mcp_rows(claude_dir: Path) -> None:
    (claude_dir / "settings.json").write_text(
        json.dumps({"permissionGrants": [{"text": "filesystem: read/write access to src/"}]}),
        encoding="utf-8",
    )

    result = get_current_configuration(claude_dir)

    grant_items = [item for item in result.items if item.kind == "mcp"]
    assert len(grant_items) == 1
    assert grant_items[0].text == "filesystem: read/write access to src/"
    assert grant_items[0].path == ".claude/settings.json"


def test_permission_grants_empty_list_yields_no_rows(claude_dir: Path) -> None:
    (claude_dir / "settings.json").write_text(json.dumps({"permissionGrants": []}), encoding="utf-8")

    result = get_current_configuration(claude_dir)

    assert not any(item.kind == "mcp" for item in result.items)


def test_permission_grants_checked_in_both_settings_files(claude_dir: Path) -> None:
    (claude_dir / "settings.json").write_text(
        json.dumps({"permissionGrants": [{"text": "team grant"}]}), encoding="utf-8"
    )
    (claude_dir / "settings.local.json").write_text(
        json.dumps({"permissionGrants": [{"text": "local grant"}]}), encoding="utf-8"
    )

    result = get_current_configuration(claude_dir)

    grant_texts = {item.text for item in result.items if item.kind == "mcp"}
    assert grant_texts == {"team grant", "local grant"}


def test_multiple_permission_grant_entries_are_all_rendered(claude_dir: Path) -> None:
    (claude_dir / "settings.json").write_text(
        json.dumps(
            {
                "permissionGrants": [
                    {"text": "filesystem: read/write access to src/"},
                    {"text": "network: outbound HTTPS only"},
                ]
            }
        ),
        encoding="utf-8",
    )

    result = get_current_configuration(claude_dir)

    grant_items = [item for item in result.items if item.kind == "mcp"]
    assert [item.text for item in grant_items] == [
        "filesystem: read/write access to src/",
        "network: outbound HTTPS only",
    ]
    assert all(item.path == ".claude/settings.json" for item in grant_items)


def test_malformed_settings_json_is_ignored_not_a_crash(claude_dir: Path) -> None:
    (claude_dir / "settings.json").write_text("{not valid json", encoding="utf-8")

    result = get_current_configuration(claude_dir)

    assert not any(item.kind == "mcp" for item in result.items)


@pytest.mark.skipif(os.name == "nt", reason="chmod-based permission denial isn't meaningful on Windows")
@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="running as root ignores permission bits, so this can't force a real PermissionError",
)
def test_get_current_configuration_propagates_real_directory_permission_error(claude_dir: Path) -> None:
    """A genuine, unmocked permission-denied `rules/` directory must raise --
    not be silently swallowed as "no rules configured" (which would misreport
    a real access problem as an empty, healthy state). This is what makes the
    gateway's global OSError handler reachable for this endpoint at all."""
    rules_dir = claude_dir / "rules"
    rules_dir.mkdir()
    (rules_dir / "testing.md").write_text("Always use pytest.", encoding="utf-8")

    original_mode = rules_dir.stat().st_mode
    os.chmod(rules_dir, 0o000)
    try:
        with pytest.raises(OSError):
            get_current_configuration(claude_dir)
    finally:
        os.chmod(rules_dir, original_mode)


def test_permission_grant_entry_without_known_fields_falls_back_to_generic_text(claude_dir: Path) -> None:
    """Never invent a permission-grant schema (Boundaries) -- an entry with no
    recognizable text/description/name still renders a row, not an error."""
    (claude_dir / "settings.json").write_text(
        json.dumps({"permissionGrants": [{"unknownField": "x"}]}), encoding="utf-8"
    )

    result = get_current_configuration(claude_dir)

    grant_items = [item for item in result.items if item.kind == "mcp"]
    assert len(grant_items) == 1
    assert grant_items[0].text == "Permission grant"


# ---- combined -----------------------------------------------------------


def test_rules_and_agents_and_grants_together(claude_dir: Path) -> None:
    (claude_dir / "rules").mkdir()
    (claude_dir / "rules" / "testing.md").write_text("Always use pytest.", encoding="utf-8")
    (claude_dir / "agents").mkdir()
    (claude_dir / "agents" / "worker.md").write_text("Does work.", encoding="utf-8")
    (claude_dir / "settings.json").write_text(
        json.dumps({"permissionGrants": [{"text": "grant one"}]}), encoding="utf-8"
    )

    result = get_current_configuration(claude_dir)

    kinds = sorted(item.kind for item in result.items)
    assert kinds == ["agent", "mcp", "rule"]


# ---- GET /api/settings/current (gateway wiring) --------------------------


@pytest.fixture
def api_client(claude_dir: Path) -> TestClient:
    app.dependency_overrides[get_claude_dir] = lambda: claude_dir
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_claude_dir, None)


def test_endpoint_returns_empty_items_for_fresh_claude_dir(api_client: TestClient) -> None:
    response = api_client.get("/api/settings/current")

    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_endpoint_reflects_live_state_without_caching(api_client: TestClient, claude_dir: Path) -> None:
    """No cached snapshot (Boundaries) -- a file written between two requests
    must show up on the second request without anything being restarted."""
    response = api_client.get("/api/settings/current")
    assert response.json() == {"items": []}

    (claude_dir / "rules").mkdir()
    (claude_dir / "rules" / "new-rule.md").write_text("A brand new rule.", encoding="utf-8")

    response = api_client.get("/api/settings/current")
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["path"] == ".claude/rules/new-rule.md"


def test_endpoint_never_writes_to_claude_dir(api_client: TestClient, claude_dir: Path) -> None:
    api_client.get("/api/settings/current")
    assert list(claude_dir.iterdir()) == []


def test_endpoint_returns_full_mixed_response_through_the_http_json_boundary(
    api_client: TestClient, claude_dir: Path
) -> None:
    """Exercises a rule + agent + mcp row together through the actual HTTP/JSON
    boundary -- the other endpoint tests above only cover the empty and
    single-item cases."""
    (claude_dir / "rules").mkdir()
    (claude_dir / "rules" / "testing.md").write_text("# Always use pytest\n", encoding="utf-8")
    (claude_dir / "agents").mkdir()
    (claude_dir / "agents" / "auth-worker.md").write_text(
        "---\nname: auth_worker\ndescription: handles OAuth2 flows\n---\n", encoding="utf-8"
    )
    (claude_dir / "settings.json").write_text(
        json.dumps({"permissionGrants": [{"text": "filesystem: read/write access to src/"}]}),
        encoding="utf-8",
    )

    response = api_client.get("/api/settings/current")

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 3
    by_kind = {item["kind"]: item for item in body["items"]}
    assert set(by_kind.keys()) == {"rule", "agent", "mcp"}
    assert by_kind["rule"] == {"kind": "rule", "text": "Always use pytest", "path": ".claude/rules/testing.md"}
    assert by_kind["agent"] == {
        "kind": "agent",
        "text": "auth_worker: handles OAuth2 flows",
        "path": ".claude/agents/auth-worker.md",
    }
    assert by_kind["mcp"] == {
        "kind": "mcp",
        "text": "filesystem: read/write access to src/",
        "path": ".claude/settings.json",
    }


@pytest.mark.skipif(os.name == "nt", reason="chmod-based permission denial isn't meaningful on Windows")
@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="running as root ignores permission bits, so this can't force a real PermissionError",
)
def test_endpoint_surfaces_error_envelope_on_real_filesystem_failure(
    api_client: TestClient, claude_dir: Path
) -> None:
    """A genuine OSError from `get_current_configuration()` (here: permission
    denied listing `rules/`) must be caught by the gateway's global
    `@app.exception_handler(OSError)` (shared with `/api/settings/apply`,
    see `test_apply_filesystem_failure_returns_error_envelope`) and surfaced
    as the app's error envelope, not propagate as a raw unhandled 500.

    Nothing here is mocked -- the directory is genuinely unreadable, and the
    permission is always restored (even on failure) so the test never leaves
    an unreadable directory behind."""
    rules_dir = claude_dir / "rules"
    rules_dir.mkdir()
    (rules_dir / "testing.md").write_text("Always use pytest.", encoding="utf-8")

    original_mode = rules_dir.stat().st_mode
    os.chmod(rules_dir, 0o000)
    try:
        response = api_client.get("/api/settings/current")

        assert response.status_code == 500
        body = response.json()
        assert set(body.keys()) == {"error_code", "message", "node_id"}
        assert body["error_code"] == "settings.io_error"
        assert body["node_id"] is None
    finally:
        os.chmod(rules_dir, original_mode)
