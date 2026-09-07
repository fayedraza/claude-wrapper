"""Settings Router approval-gated write path (FR-2).

`apply_action()` is the only code in this app that touches `.claude/`. It is
called once per approved `SettingAction`, never for a rejected one and never
speculatively -- callers (the gateway) must not call this until the user has
pressed Approve & Apply on that exact previewed action.
"""

from __future__ import annotations

from pathlib import Path

from .models import SettingAction
from .router import SettingsPathError, compute_file_path


def resolve_display_path(claude_dir: Path, file_path: str) -> Path:
    """Resolve a `.claude/...`-relative display path back to an absolute path.

    `file_path` here is client-supplied (round-tripped from a `propose`
    response through the frontend), so it is re-validated independently of
    however it was originally computed -- never assume it is still the exact
    string `classify_request()` produced. Raises `SettingsPathError` if it
    doesn't start with the expected `.claude/` prefix or would resolve
    outside `claude_dir`.
    """
    claude_dir_resolved = claude_dir.resolve()
    prefix = f"{claude_dir.name}/"
    if not file_path.startswith(prefix):
        raise SettingsPathError(f"'{file_path}' is not a path under '{claude_dir.name}/'")

    relative = file_path[len(prefix) :]
    resolved = (claude_dir_resolved / relative).resolve()
    if resolved != claude_dir_resolved and claude_dir_resolved not in resolved.parents:
        raise SettingsPathError(f"'{file_path}' escapes control-center directory '{claude_dir_resolved}'")
    return resolved


def _verify_path_matches_category(claude_dir: Path, action: SettingAction, resolved: Path) -> None:
    """Re-derive the expected path from `action.target_category` and confirm it's
    exactly `resolved`.

    A client can send any in-bounds `file_path` paired with any
    `target_category` -- e.g. `target_category="rule"` with
    `file_path=".claude/CLAUDE.md"` -- which would otherwise bypass the
    deterministic category -> path mapping `classify_request()` enforces at
    propose time and let one category's approval overwrite an unrelated
    file. `resolved`'s own filename (for fixed categories this hint is
    ignored entirely; for named categories `compute_file_path` re-sanitizes
    it, so anything not already in canonical slug form also fails here) is
    fed back through the same deterministic mapping used at propose time; if
    that doesn't reproduce `resolved` exactly, the pairing is rejected.
    """
    expected = compute_file_path(claude_dir, action.target_category, resolved.stem)
    if expected != resolved:
        raise SettingsPathError(
            f"'{action.file_path}' does not match the expected path for target_category "
            f"'{action.target_category}' (expected something resolving to "
            f"'{expected}')"
        )


def apply_action(claude_dir: Path, action: SettingAction) -> Path:
    """Write, update, or revoke exactly the one file an approved action targets.

    Nothing else under `.claude/` is touched. Returns the absolute path
    written to or removed, for logging/response purposes.
    """
    target = resolve_display_path(claude_dir, action.file_path)
    _verify_path_matches_category(claude_dir, action, target)

    if action.action == "revoke":
        target.unlink(missing_ok=True)
        return target

    # create / update
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(action.content, encoding="utf-8")
    return target
