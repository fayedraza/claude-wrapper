"""Unit tests for `brain.settings_router.router` (FR-1 classification)."""

from pathlib import Path

import httpx2
import pytest
from anthropic import APIConnectionError

from brain.settings_router.models import SettingAction, SettingsRouterOutput
from brain.settings_router.router import (
    SettingsPathError,
    classify_request,
    compute_file_path,
    display_path,
    sanitize_slug,
)


# ---- sanitize_slug ----------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Always Use Pytest", "always-use-pytest"),
        ("testing.md", "testing"),
        ("rules/testing.md", "testing"),
        ("../../etc/passwd", "passwd"),
        ("a\\b\\c.md", "c"),
        ("", "unnamed"),
        ("....", "unnamed"),
    ],
)
def test_sanitize_slug(raw: str, expected: str) -> None:
    assert sanitize_slug(raw) == expected


def test_sanitize_slug_never_contains_path_separators_or_dotdot() -> None:
    for raw in ["../../../etc/passwd", "a/b/../../c", "..\\..\\windows", "///", ".."]:
        slug = sanitize_slug(raw)
        assert "/" not in slug
        assert "\\" not in slug
        assert ".." not in slug


# ---- compute_file_path -------------------------------------------------


def test_compute_file_path_team_instructions(claude_dir: Path) -> None:
    path = compute_file_path(claude_dir, "team_instructions", "ignored")
    assert path == claude_dir / "CLAUDE.md"


def test_compute_file_path_local_instructions(claude_dir: Path) -> None:
    path = compute_file_path(claude_dir, "local_instructions", "ignored")
    assert path == claude_dir / "CLAUDE.local.md"


def test_compute_file_path_settings_json(claude_dir: Path) -> None:
    path = compute_file_path(claude_dir, "settings.json", "ignored")
    assert path == claude_dir / "settings.json"


def test_compute_file_path_settings_local_json(claude_dir: Path) -> None:
    path = compute_file_path(claude_dir, "settings.local.json", "ignored")
    assert path == claude_dir / "settings.local.json"


def test_compute_file_path_rule(claude_dir: Path) -> None:
    path = compute_file_path(claude_dir, "rule", "Testing Rule")
    assert path == claude_dir / "rules" / "testing-rule.md"


def test_compute_file_path_skill_nests_under_its_own_slug_dir(claude_dir: Path) -> None:
    path = compute_file_path(claude_dir, "skill", "pdf-export")
    assert path == claude_dir / "skills" / "pdf-export" / "pdf-export.md"


def test_compute_file_path_command(claude_dir: Path) -> None:
    path = compute_file_path(claude_dir, "command", "deploy")
    assert path == claude_dir / "commands" / "deploy.md"


def test_compute_file_path_agent(claude_dir: Path) -> None:
    path = compute_file_path(claude_dir, "agent", "auth_scaffold_worker")
    assert path == claude_dir / "agents" / "auth-scaffold-worker.md"


def test_compute_file_path_ignores_llm_supplied_directories(claude_dir: Path) -> None:
    """The LLM's hint may contain path separators; only its final segment (as a slug) is used."""
    path = compute_file_path(claude_dir, "rule", "../../etc/passwd")
    assert path == claude_dir / "rules" / "passwd.md"
    assert claude_dir in path.parents


def test_display_path_round_trips(claude_dir: Path) -> None:
    resolved = compute_file_path(claude_dir, "rule", "testing")
    assert display_path(claude_dir, resolved) == ".claude/rules/testing.md"


# ---- classify_request ---------------------------------------------------


def test_classify_request_single_action(claude_dir: Path, make_fake_client) -> None:
    fake_output = SettingsRouterOutput(
        user_summary="Creates a rule file with your testing guidance.",
        updates=[
            SettingAction(
                target_category="rule",
                file_path="testing.md",  # LLM's hint -- must not be trusted verbatim
                content="Always use pytest for test files.",
                action="create",
            )
        ],
    )
    client = make_fake_client(output=fake_output)

    result = classify_request("always use pytest", claude_dir, client)

    assert len(result.updates) == 1
    action = result.updates[0]
    assert action.target_category == "rule"
    assert action.file_path == ".claude/rules/testing.md"
    assert action.action == "create"
    assert action.content == "Always use pytest for test files."
    assert result.user_summary


def test_classify_request_multiple_actions(claude_dir: Path, make_fake_client) -> None:
    fake_output = SettingsRouterOutput(
        user_summary="Adds a testing rule and ignores .env in settings.",
        updates=[
            SettingAction(
                target_category="rule",
                file_path="testing",
                content="Always use pytest.",
                action="create",
            ),
            SettingAction(
                target_category="settings.json",
                file_path="settings.json",
                content='{"ignoredFiles": [".env"]}',
                action="update",
            ),
        ],
    )
    client = make_fake_client(output=fake_output)

    result = classify_request("always use pytest, never commit .env", claude_dir, client)

    assert len(result.updates) == 2
    assert result.updates[0].file_path == ".claude/rules/testing.md"
    assert result.updates[1].file_path == ".claude/settings.json"


def test_classify_request_no_op_returns_empty_updates_with_explanation(claude_dir: Path, make_fake_client) -> None:
    fake_output = SettingsRouterOutput(
        user_summary="That's already the default behavior -- nothing to change.",
        updates=[],
    )
    client = make_fake_client(output=fake_output)

    result = classify_request("be helpful", claude_dir, client)

    assert result.updates == []
    assert result.user_summary


def test_classify_request_propagates_llm_failure_without_writing(claude_dir: Path, make_fake_client) -> None:
    error = APIConnectionError(request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"))
    client = make_fake_client(error=error)

    with pytest.raises(APIConnectionError):
        classify_request("always use pytest", claude_dir, client)

    # Nothing should exist under .claude/ -- classify_request never writes.
    assert list(claude_dir.iterdir()) == []


def test_classify_request_rejects_target_category_that_would_escape_claude_dir(
    claude_dir: Path, monkeypatch: pytest.MonkeyPatch, make_fake_client
) -> None:
    """Defense in depth: even if a future bug widened what reaches compute_file_path,
    classify_request must not silently accept an escaping path."""
    import brain.settings_router.router as router_module

    def _escaping_compute_file_path(claude_dir_arg, target_category, file_path_hint):
        raise SettingsPathError("simulated escape")

    monkeypatch.setattr(router_module, "compute_file_path", _escaping_compute_file_path)

    fake_output = SettingsRouterOutput(
        user_summary="x",
        updates=[SettingAction(target_category="rule", file_path="x", content="x", action="create")],
    )
    client = make_fake_client(output=fake_output)

    with pytest.raises(SettingsPathError):
        classify_request("x", claude_dir, client)


def test_classify_request_normalizes_credential_resolution_type_error(claude_dir: Path, make_fake_client) -> None:
    """anthropic's SDK raises a bare TypeError (not an APIError) when it can't resolve
    any credentials at all -- classify_request must normalize it into the
    anthropic.AnthropicError family so the gateway only needs one handler."""
    import anthropic

    error = TypeError("Could not resolve authentication method. Expected one of api_key, auth_token, ...")
    client = make_fake_client(error=error)

    with pytest.raises(anthropic.AnthropicError):
        classify_request("always use pytest", claude_dir, client)

    assert list(claude_dir.iterdir()) == []


def test_classify_request_raises_when_parsed_output_is_none(claude_dir: Path, make_fake_client) -> None:
    """`ParsedMessage.parsed_output` is Optional -- reachable on truncation, a refusal,
    or any response that isn't parseable text, not just a type-checker artifact.
    classify_request must raise a clean error instead of an AttributeError."""
    import anthropic

    client = make_fake_client(output=None)  # simulates response.parsed_output is None

    with pytest.raises(anthropic.AnthropicError):
        classify_request("always use pytest", claude_dir, client)

    assert list(claude_dir.iterdir()) == []


def test_classify_request_disambiguates_colliding_resolved_paths(claude_dir: Path, make_fake_client) -> None:
    """Two updates that would otherwise sanitize to the same path (e.g. two unnamed
    `rule` actions) must resolve to distinct file_paths -- otherwise approving both
    would silently let the second overwrite the first with no warning shown anywhere."""
    fake_output = SettingsRouterOutput(
        user_summary="Adds two rules.",
        updates=[
            SettingAction(target_category="rule", file_path="", content="first", action="create"),
            SettingAction(target_category="rule", file_path="", content="second", action="create"),
        ],
    )
    client = make_fake_client(output=fake_output)

    result = classify_request("add two rules", claude_dir, client)

    paths = [update.file_path for update in result.updates]
    assert len(paths) == len(set(paths)), f"expected distinct paths, got {paths}"
    assert paths[0] == ".claude/rules/unnamed.md"
    assert paths[1] == ".claude/rules/unnamed-2.md"


def test_classify_request_does_not_disambiguate_fixed_category_collisions(claude_dir: Path, make_fake_client) -> None:
    """A fixed-path category (e.g. two `team_instructions` edits) has nowhere else to
    go -- it's two edits to the same singleton file, not a naming accident, so both
    keep the same path rather than being (incorrectly) renamed."""
    fake_output = SettingsRouterOutput(
        user_summary="Two edits to CLAUDE.md.",
        updates=[
            SettingAction(target_category="team_instructions", file_path="ignored", content="a", action="update"),
            SettingAction(target_category="team_instructions", file_path="ignored", content="b", action="update"),
        ],
    )
    client = make_fake_client(output=fake_output)

    result = classify_request("x", claude_dir, client)

    assert [u.file_path for u in result.updates] == [".claude/CLAUDE.md", ".claude/CLAUDE.md"]
