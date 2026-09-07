"""Settings Router approval-gated write path (FR-2).

`apply_action()` is the only code in this app that touches `.claude/`. It is
called once per approved `SettingAction`, never for a rejected one and never
speculatively -- callers (the gateway) must not call this until the user has
pressed Approve & Apply on that exact previewed action.
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import SettingAction
from .router import SettingsPathError, compute_file_path

# Story 1.4: grants.py persists permission grants under this same key in
# this same file (settings.local.json) -- see `_preserve_permission_grants`.
_PERMISSION_GRANTS_KEY = "permissionGrants"


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


def _preserve_permission_grants(existing_path: Path, new_content: str) -> str:
    """Re-inject an existing `permissionGrants` entry into an approved
    `settings.local.json` write, so it survives an unrelated change.

    `grants.py` (Story 1.4) persists permission grants under this same key
    in this same file, entirely independently of the Settings Router's
    propose/apply flow -- without this, approving any other
    `settings.local.json` change here (e.g. a permission/tool tweak) would
    silently clobber the whole file via `write_text`, destroying every grant
    with no error or warning.

    Only fires when the *existing* on-disk file already has a
    `permissionGrants` key. Returns `new_content` unchanged when: there's no
    existing file yet; the existing file isn't valid JSON (or isn't a JSON
    object) or has no `permissionGrants` key; `new_content` isn't valid JSON
    (or isn't a JSON object) -- this preservation only applies to the
    well-formed JSON documents this category expects; or `new_content`
    already explicitly defines `permissionGrants` itself (an intentional
    change to grants, e.g. Settings Router-driven, must not be overridden by
    the old value).
    """
    if not existing_path.is_file():
        return new_content

    try:
        existing_data = json.loads(existing_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return new_content
    if not isinstance(existing_data, dict) or _PERMISSION_GRANTS_KEY not in existing_data:
        return new_content

    try:
        new_data = json.loads(new_content)
    except json.JSONDecodeError:
        return new_content
    if not isinstance(new_data, dict) or _PERMISSION_GRANTS_KEY in new_data:
        return new_content

    new_data[_PERMISSION_GRANTS_KEY] = existing_data[_PERMISSION_GRANTS_KEY]
    return json.dumps(new_data, indent=2) + "\n"


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
    content = action.content
    if action.target_category == "settings.local.json":
        content = _preserve_permission_grants(target, content)
    target.write_text(content, encoding="utf-8")
    return target
