"""Permission grants: view, add, revoke, and move grants between scopes
(FR-6 + the standing half of FR-5 -- "future runs respect it
automatically").

Grants live in one of two files, chosen by `scope`: `"local"` (personal,
`.claude/settings.local.json`, not committed) or `"team"` (shared,
`.claude/settings.json`, committed -- the same file Claude Code's own
`hooks`/`permissions` keys live in, though this module never touches those
keys, only `permissionGrants`). `list_grants()` reads both files and tags
every grant with the scope it came from; `add_grant()` writes to whichever
file `scope` selects; `revoke_grant()`/`update_grant()` locate a grant by id
regardless of which file it's currently in (ids are server-generated
`uuid4` hex, so a collision across the two files is not a realistic
concern).

Targets are opaque identifiers (Design Notes): this module never checks a
granted file exists or a server is reachable -- only that the target is
non-empty after trimming and under a generous length cap.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from .models import GrantScope, PermissionGrant, PermissionGrantKind, PermissionGrantsList

_SCOPE_FILENAMES: dict[GrantScope, str] = {
    "local": "settings.local.json",
    "team": "settings.json",
}
_GRANTS_KEY = "permissionGrants"
_SCOPES: tuple[GrantScope, ...] = ("local", "team")

# Design Notes: "validate non-empty-after-trim + a generous max length,
# nothing more" -- targets are opaque identifiers (a file path or an MCP
# server name), never expected to legitimately approach this length.
MAX_TARGET_LENGTH = 4096


class PermissionGrantValidationError(ValueError):
    """An add/update-grant request's `target` failed validation (empty/whitespace-only or too long)."""


class PermissionGrantNotFoundError(LookupError):
    """A revoke/update request's `id` doesn't match any existing grant in either file."""


def _settings_path(claude_dir: Path, scope: GrantScope) -> Path:
    return claude_dir / _SCOPE_FILENAMES[scope]


def _read_settings(path: Path) -> dict[str, Any]:
    """Read a settings file as a dict, tolerating a missing or malformed file.

    A missing file (no `.claude/` yet, or this specific file doesn't exist)
    is "no grants yet" (I/O matrix) -- an empty dict, not an error. A
    malformed (non-JSON, or JSON that isn't an object) file is treated the
    same way rather than crashing; a genuine filesystem-level failure
    (permission denied, ...) is left unguarded here so it propagates to the
    gateway's global `@app.exception_handler(OSError)`, same as the rest of
    this app.
    """
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _write_settings(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _parse_grants(data: dict[str, Any], scope: GrantScope) -> list[PermissionGrant]:
    """Parse the `permissionGrants` list, tagging each entry with `scope`
    and skipping any entry that doesn't fit the real schema (defense in
    depth -- this module is the only writer, but a hand-edited file
    shouldn't crash reads)."""
    raw = data.get(_GRANTS_KEY)
    if not isinstance(raw, list):
        return []

    grants: list[PermissionGrant] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        try:
            grants.append(PermissionGrant.model_validate({**entry, "scope": scope}))
        except ValueError:
            continue
    return grants


def _dump_grants(grants: list[PermissionGrant]) -> list[dict[str, Any]]:
    """Serialize back to the on-disk shape -- `scope` is derived from which
    file a grant lives in, never itself persisted inside the entry."""
    return [g.model_dump(exclude={"scope"}) for g in grants]


def _find_grant(claude_dir: Path, grant_id: str) -> tuple[PermissionGrant, GrantScope] | tuple[None, None]:
    for scope in _SCOPES:
        grants = _parse_grants(_read_settings(_settings_path(claude_dir, scope)), scope)
        for grant in grants:
            if grant.id == grant_id:
                return grant, scope
    return None, None


def list_grants(claude_dir: Path) -> PermissionGrantsList:
    """FR-6: read every grant currently persisted, across both
    `settings.local.json` (personal) and `settings.json` (team) -- each
    tagged with which file it came from.

    Neither file existing yet -- empty list, friendly empty state (I/O
    matrix), never an error.
    """
    grants: list[PermissionGrant] = []
    for scope in _SCOPES:
        grants.extend(_parse_grants(_read_settings(_settings_path(claude_dir, scope)), scope))
    return PermissionGrantsList(grants=grants)


def add_grant(claude_dir: Path, kind: PermissionGrantKind, target: str, scope: GrantScope = "local") -> PermissionGrant:
    """FR-6: add a grant for `kind`+`target` to the file `scope` selects,
    idempotently within that file.

    Adding an already-present (same `kind`+`target`) grant *in that same
    scope* returns the existing grant unchanged -- no duplicate row, no
    write (I/O matrix). The same `kind`+`target` can independently exist in
    the other scope too -- a personal grant and a team grant are different,
    both-apply facts (matching how Claude Code's own real permission arrays
    merge rather than conflict across settings files), not a collision.
    Raises `PermissionGrantValidationError` for an empty/whitespace-only or
    too-long target; nothing is persisted in that case.
    """
    trimmed = target.strip()
    if not trimmed:
        raise PermissionGrantValidationError("target must not be empty or whitespace-only")
    if len(trimmed) > MAX_TARGET_LENGTH:
        raise PermissionGrantValidationError(f"target must be at most {MAX_TARGET_LENGTH} characters")

    path = _settings_path(claude_dir, scope)
    data = _read_settings(path)
    grants = _parse_grants(data, scope)

    for existing in grants:
        if existing.kind == kind and existing.target == trimmed:
            return existing

    new_grant = PermissionGrant(id=uuid.uuid4().hex, kind=kind, target=trimmed, scope=scope)
    grants.append(new_grant)
    data[_GRANTS_KEY] = _dump_grants(grants)
    _write_settings(path, data)
    return new_grant


def revoke_grant(claude_dir: Path, grant_id: str) -> None:
    """FR-6: remove one grant by id, regardless of which file (`local` or
    `team`) it currently lives in.

    Raises `PermissionGrantNotFoundError` if `grant_id` doesn't match any
    existing grant in either file (I/O matrix: "Revoke unknown/already-
    revoked id").
    """
    _current, scope = _find_grant(claude_dir, grant_id)
    if scope is None:
        raise PermissionGrantNotFoundError(f"No permission grant with id '{grant_id}'")

    path = _settings_path(claude_dir, scope)
    data = _read_settings(path)
    grants = [g for g in _parse_grants(data, scope) if g.id != grant_id]
    data[_GRANTS_KEY] = _dump_grants(grants)
    _write_settings(path, data)


def update_grant(
    claude_dir: Path,
    grant_id: str,
    *,
    kind: PermissionGrantKind | None = None,
    target: str | None = None,
    scope: GrantScope | None = None,
) -> PermissionGrant:
    """Edit an existing grant's `kind`/`target`, and/or move it between
    `local` and `team` scope -- regardless of which file it currently lives
    in. Only the provided fields change; omitted ones keep their current
    value.

    Moving to a scope that already has an identical `kind`+`target` grant
    merges into that existing grant (same idempotency rule as `add_grant`)
    rather than creating a duplicate -- the moved grant's own id is then
    dropped in favor of the pre-existing one, exactly as a redundant
    `add_grant` call would behave.

    Raises `PermissionGrantNotFoundError` if `grant_id` doesn't match any
    existing grant in either file. Raises `PermissionGrantValidationError`
    if the resulting target is empty/whitespace-only or too long.
    """
    current, current_scope = _find_grant(claude_dir, grant_id)
    if current is None or current_scope is None:
        raise PermissionGrantNotFoundError(f"No permission grant with id '{grant_id}'")

    new_kind = current.kind if kind is None else kind
    new_target = current.target if target is None else target.strip()
    new_scope = current_scope if scope is None else scope

    if not new_target:
        raise PermissionGrantValidationError("target must not be empty or whitespace-only")
    if len(new_target) > MAX_TARGET_LENGTH:
        raise PermissionGrantValidationError(f"target must be at most {MAX_TARGET_LENGTH} characters")

    if new_scope == current_scope:
        # In-place edit: a single read-modify-write on the one file involved.
        path = _settings_path(claude_dir, current_scope)
        data = _read_settings(path)
        grants = [g for g in _parse_grants(data, current_scope) if g.id != grant_id]

        for existing in grants:
            if existing.kind == new_kind and existing.target == new_target:
                data[_GRANTS_KEY] = _dump_grants(grants)
                _write_settings(path, data)
                return existing

        updated = PermissionGrant(id=grant_id, kind=new_kind, target=new_target, scope=new_scope)
        grants.append(updated)
        data[_GRANTS_KEY] = _dump_grants(grants)
        _write_settings(path, data)
        return updated

    # Moving between scopes: remove from the old file, insert into the new one.
    old_path = _settings_path(claude_dir, current_scope)
    old_data = _read_settings(old_path)
    old_grants = [g for g in _parse_grants(old_data, current_scope) if g.id != grant_id]
    old_data[_GRANTS_KEY] = _dump_grants(old_grants)
    _write_settings(old_path, old_data)

    new_path = _settings_path(claude_dir, new_scope)
    new_data = _read_settings(new_path)
    new_grants = _parse_grants(new_data, new_scope)

    for existing in new_grants:
        if existing.kind == new_kind and existing.target == new_target:
            return existing

    updated = PermissionGrant(id=grant_id, kind=new_kind, target=new_target, scope=new_scope)
    new_grants.append(updated)
    new_data[_GRANTS_KEY] = _dump_grants(new_grants)
    _write_settings(new_path, new_data)
    return updated
