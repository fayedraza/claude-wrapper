"""Unit tests for `brain.settings_router.apply` (FR-2 approval-gated write)."""

import json
from pathlib import Path

import pytest

from brain.settings_router.apply import apply_action, resolve_display_path
from brain.settings_router.grants import add_grant, list_grants
from brain.settings_router.models import SettingAction
from brain.settings_router.router import SettingsPathError


def test_apply_action_creates_new_file(claude_dir: Path) -> None:
    action = SettingAction(
        target_category="rule",
        file_path=".claude/rules/testing.md",
        content="Always use pytest.",
        action="create",
    )

    written = apply_action(claude_dir, action)

    assert written == claude_dir / "rules" / "testing.md"
    assert written.read_text(encoding="utf-8") == "Always use pytest."


def test_apply_action_updates_existing_file(claude_dir: Path) -> None:
    (claude_dir / "CLAUDE.md").write_text("old content", encoding="utf-8")
    action = SettingAction(
        target_category="team_instructions",
        file_path=".claude/CLAUDE.md",
        content="new content",
        action="update",
    )

    apply_action(claude_dir, action)

    assert (claude_dir / "CLAUDE.md").read_text(encoding="utf-8") == "new content"


def test_apply_action_revoke_removes_file(claude_dir: Path) -> None:
    rules_dir = claude_dir / "rules"
    rules_dir.mkdir()
    (rules_dir / "testing.md").write_text("Always use pytest.", encoding="utf-8")
    action = SettingAction(
        target_category="rule",
        file_path=".claude/rules/testing.md",
        content="",
        action="revoke",
    )

    apply_action(claude_dir, action)

    assert not (rules_dir / "testing.md").exists()


def test_apply_action_revoke_is_idempotent_when_file_already_missing(claude_dir: Path) -> None:
    action = SettingAction(
        target_category="rule",
        file_path=".claude/rules/nonexistent.md",
        content="",
        action="revoke",
    )

    # Should not raise even though the file was never created.
    apply_action(claude_dir, action)


def test_apply_action_touches_only_its_own_target(claude_dir: Path) -> None:
    (claude_dir / "CLAUDE.md").write_text("untouched", encoding="utf-8")
    (claude_dir / "settings.json").write_text("{}", encoding="utf-8")
    action = SettingAction(
        target_category="rule",
        file_path=".claude/rules/testing.md",
        content="Always use pytest.",
        action="create",
    )

    apply_action(claude_dir, action)

    assert (claude_dir / "CLAUDE.md").read_text(encoding="utf-8") == "untouched"
    assert (claude_dir / "settings.json").read_text(encoding="utf-8") == "{}"


def test_apply_action_rejects_path_escaping_claude_dir(claude_dir: Path) -> None:
    action = SettingAction(
        target_category="rule",
        file_path=".claude/../../etc/passwd",
        content="pwned",
        action="create",
    )

    with pytest.raises(SettingsPathError):
        apply_action(claude_dir, action)

    assert list(claude_dir.iterdir()) == []


def test_apply_action_rejects_path_without_claude_prefix(claude_dir: Path) -> None:
    action = SettingAction(
        target_category="rule",
        file_path="/etc/passwd",
        content="pwned",
        action="create",
    )

    with pytest.raises(SettingsPathError):
        apply_action(claude_dir, action)


def test_resolve_display_path_round_trips_compute_file_path_output(claude_dir: Path) -> None:
    resolved = resolve_display_path(claude_dir, ".claude/agents/auth-scaffold-worker.md")
    assert resolved == claude_dir / "agents" / "auth-scaffold-worker.md"


def test_apply_action_rejects_target_category_that_does_not_match_file_path(claude_dir: Path) -> None:
    """A client pairing an in-bounds file_path with a mismatched target_category (e.g.
    claiming "rule" while pointing at CLAUDE.md) must be rejected, not accepted --
    otherwise it bypasses the deterministic category -> path mapping classify_request()
    enforces at propose time and could overwrite an unrelated file."""
    (claude_dir / "CLAUDE.md").write_text("original team instructions", encoding="utf-8")
    action = SettingAction(
        target_category="rule",
        file_path=".claude/CLAUDE.md",
        content="pwned",
        action="update",
    )

    with pytest.raises(SettingsPathError):
        apply_action(claude_dir, action)

    assert (claude_dir / "CLAUDE.md").read_text(encoding="utf-8") == "original team instructions"


def test_apply_action_rejects_settings_json_category_pointed_at_settings_local_json(claude_dir: Path) -> None:
    """Same category/path mismatch guard, exercised across the two fixed-name JSON categories."""
    action = SettingAction(
        target_category="settings.json",
        file_path=".claude/settings.local.json",
        content="{}",
        action="create",
    )

    with pytest.raises(SettingsPathError):
        apply_action(claude_dir, action)

    assert list(claude_dir.iterdir()) == []


def test_apply_action_preserves_permission_grants_on_unrelated_settings_local_json_change(claude_dir: Path) -> None:
    """Regression: grants.py (Story 1.4) persists `permissionGrants` in this
    same settings.local.json file, entirely independently of the Settings
    Router's propose/apply flow -- approving an unrelated change to that
    file (e.g. a permission/tool tweak) must not silently destroy it."""
    grant = add_grant(claude_dir, "file", "src/secrets.json")

    action = SettingAction(
        target_category="settings.local.json",
        file_path=".claude/settings.local.json",
        content=json.dumps({"someUnrelatedSetting": True}),
        action="update",
    )
    apply_action(claude_dir, action)

    remaining = list_grants(claude_dir).grants
    assert remaining == [grant]
    # The unrelated change was still applied.
    data = json.loads((claude_dir / "settings.local.json").read_text(encoding="utf-8"))
    assert data["someUnrelatedSetting"] is True


def test_apply_action_does_not_override_an_explicit_permission_grants_write(claude_dir: Path) -> None:
    """An approved settings.local.json change that explicitly defines
    `permissionGrants` itself is an intentional change to grants -- the old
    on-disk value must not be re-injected over it."""
    add_grant(claude_dir, "file", "src/old.json")

    new_grants = [{"id": "manual-1", "kind": "mcp", "target": "manual-server"}]
    action = SettingAction(
        target_category="settings.local.json",
        file_path=".claude/settings.local.json",
        content=json.dumps({"permissionGrants": new_grants}),
        action="update",
    )
    apply_action(claude_dir, action)

    data = json.loads((claude_dir / "settings.local.json").read_text(encoding="utf-8"))
    assert data["permissionGrants"] == new_grants


def test_apply_action_raises_os_error_on_filesystem_failure(claude_dir: Path) -> None:
    """A path that collides with an existing directory of the same name fails at the
    filesystem level (IsADirectoryError, a subclass of OSError) -- apply_action must
    let that propagate rather than silently succeeding or masking it."""
    target_dir = claude_dir / "rules" / "testing.md"
    target_dir.mkdir(parents=True)
    action = SettingAction(
        target_category="rule",
        file_path=".claude/rules/testing.md",
        content="Always use pytest.",
        action="create",
    )

    with pytest.raises(OSError):
        apply_action(claude_dir, action)
