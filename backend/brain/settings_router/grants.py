"""Permission grants: view, add, and revoke grants (FR-6 + the standing half
of FR-5 -- "future runs respect it automatically").

Boundaries: reads/writes go only to `.claude/settings.local.json`, never the
team-shared `settings.json` (Claude Code's own reserved file, out of scope --
see Design Notes). `list_grants`/`add_grant`/`revoke_grant` never even open
`settings.json`. `summary.py` is the one place that still reads grants from
both files for display purposes, unchanged from Story 1.3.

Targets are opaque identifiers (Design Notes): this module never checks a
granted file exists or a server is reachable -- only that the target is
non-empty after trimming and under a generous length cap.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from .models import PermissionGrant, PermissionGrantKind, PermissionGrantsList

_SETTINGS_LOCAL_FILENAME = "settings.local.json"
_GRANTS_KEY = "permissionGrants"

# Design Notes: "validate non-empty-after-trim + a generous max length,
# nothing more" -- targets are opaque identifiers (a file path or an MCP
# server name), never expected to legitimately approach this length.
MAX_TARGET_LENGTH = 4096


class PermissionGrantValidationError(ValueError):
    """An add-grant request's `target` failed validation (empty/whitespace-only or too long)."""


class PermissionGrantNotFoundError(LookupError):
    """A revoke request's `id` doesn't match any existing grant."""


def _settings_local_path(claude_dir: Path) -> Path:
    return claude_dir / _SETTINGS_LOCAL_FILENAME


def _read_settings_local(claude_dir: Path) -> dict[str, Any]:
    """Read `settings.local.json` as a dict, tolerating a missing or malformed file.

    A missing file (no `.claude/` yet, or `.claude/` exists but this file
    doesn't) is "no grants yet" (I/O matrix) -- an empty dict, not an error.
    A malformed (non-JSON, or JSON that isn't an object) file is treated the
    same way rather than crashing `list_grants`/`add_grant`/`revoke_grant`;
    a genuine filesystem-level failure (permission denied, ...) is left
    unguarded here so it propagates to the gateway's global
    `@app.exception_handler(OSError)`, same as the rest of this app.
    """
    path = _settings_local_path(claude_dir)
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _write_settings_local(claude_dir: Path, data: dict[str, Any]) -> None:
    claude_dir.mkdir(parents=True, exist_ok=True)
    _settings_local_path(claude_dir).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _parse_grants(data: dict[str, Any]) -> list[PermissionGrant]:
    """Parse the `permissionGrants` list, skipping any entry that doesn't fit
    the real schema (defense in depth -- this module is the only writer, but
    a hand-edited file shouldn't crash reads)."""
    raw = data.get(_GRANTS_KEY)
    if not isinstance(raw, list):
        return []

    grants: list[PermissionGrant] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        try:
            grants.append(PermissionGrant.model_validate(entry))
        except ValueError:
            continue
    return grants


def list_grants(claude_dir: Path) -> PermissionGrantsList:
    """FR-6: read every grant currently persisted in `settings.local.json`.

    No `.claude/` directory, no `settings.local.json`, or no `permissionGrants`
    key -- empty list, friendly empty state (I/O matrix), never an error.
    """
    return PermissionGrantsList(grants=_parse_grants(_read_settings_local(claude_dir)))


def add_grant(claude_dir: Path, kind: PermissionGrantKind, target: str) -> PermissionGrant:
    """FR-6: add a grant for `kind`+`target`, idempotently.

    Adding an already-present (same `kind`+`target`) grant returns the
    existing grant unchanged -- no duplicate row, no write (I/O matrix).
    Raises `PermissionGrantValidationError` for an empty/whitespace-only or
    too-long target; nothing is persisted in that case.
    """
    trimmed = target.strip()
    if not trimmed:
        raise PermissionGrantValidationError("target must not be empty or whitespace-only")
    if len(trimmed) > MAX_TARGET_LENGTH:
        raise PermissionGrantValidationError(f"target must be at most {MAX_TARGET_LENGTH} characters")

    data = _read_settings_local(claude_dir)
    grants = _parse_grants(data)

    for existing in grants:
        if existing.kind == kind and existing.target == trimmed:
            return existing

    new_grant = PermissionGrant(id=uuid.uuid4().hex, kind=kind, target=trimmed)
    grants.append(new_grant)
    data[_GRANTS_KEY] = [g.model_dump() for g in grants]
    _write_settings_local(claude_dir, data)
    return new_grant


def revoke_grant(claude_dir: Path, grant_id: str) -> None:
    """FR-6: remove one grant by id.

    Raises `PermissionGrantNotFoundError` if `grant_id` doesn't match any
    existing grant (I/O matrix: "Revoke unknown/already-revoked id").
    """
    data = _read_settings_local(claude_dir)
    grants = _parse_grants(data)

    remaining = [g for g in grants if g.id != grant_id]
    if len(remaining) == len(grants):
        raise PermissionGrantNotFoundError(f"No permission grant with id '{grant_id}'")

    data[_GRANTS_KEY] = [g.model_dump() for g in remaining]
    _write_settings_local(claude_dir, data)
