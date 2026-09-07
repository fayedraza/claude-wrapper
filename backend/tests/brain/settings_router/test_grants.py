"""Unit + API-level tests for `brain.settings_router.grants` (FR-6, I/O matrix)."""

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from brain.settings_router.grants import (
    MAX_TARGET_LENGTH,
    PermissionGrantNotFoundError,
    PermissionGrantValidationError,
    add_grant,
    list_grants,
    revoke_grant,
)
from gateway.main import app, get_claude_dir


def _settings_local(claude_dir: Path) -> dict:
    return json.loads((claude_dir / "settings.local.json").read_text(encoding="utf-8"))


# ---- list_grants ----------------------------------------------------------


def test_no_claude_dir_yields_empty_grants_list(tmp_path: Path) -> None:
    missing = tmp_path / ".claude"
    assert not missing.exists()

    result = list_grants(missing)

    assert result.grants == []


def test_no_settings_local_file_yields_empty_grants_list(claude_dir: Path) -> None:
    result = list_grants(claude_dir)
    assert result.grants == []


def test_settings_local_without_permission_grants_key_yields_empty_list(claude_dir: Path) -> None:
    (claude_dir / "settings.local.json").write_text(json.dumps({"other": "thing"}), encoding="utf-8")

    result = list_grants(claude_dir)

    assert result.grants == []


def test_malformed_settings_local_json_yields_empty_list_not_a_crash(claude_dir: Path) -> None:
    (claude_dir / "settings.local.json").write_text("{not valid json", encoding="utf-8")

    result = list_grants(claude_dir)

    assert result.grants == []


@pytest.mark.skipif(os.name == "nt", reason="chmod-based permission denial isn't meaningful on Windows")
@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="running as root ignores permission bits, so this can't force a real PermissionError",
)
def test_list_grants_propagates_real_permission_error(claude_dir: Path) -> None:
    """A genuine, unmocked permission-denied `settings.local.json` must raise --
    not be silently swallowed as "no grants" (I/O matrix: "Fetch fails"). This
    is what makes the gateway's global OSError handler reachable at all,
    mirroring test_summary.py's equivalent test for the rules/agents reader."""
    settings_local = claude_dir / "settings.local.json"
    settings_local.write_text(json.dumps({"permissionGrants": []}), encoding="utf-8")

    original_mode = settings_local.stat().st_mode
    os.chmod(settings_local, 0o000)
    try:
        with pytest.raises(OSError):
            list_grants(claude_dir)
    finally:
        os.chmod(settings_local, original_mode)


def test_list_grants_never_reads_settings_json(claude_dir: Path) -> None:
    """Boundaries: reads/writes go only to settings.local.json, never the
    team-shared settings.json."""
    (claude_dir / "settings.json").write_text(
        json.dumps({"permissionGrants": [{"id": "x", "kind": "mcp", "target": "should-not-appear"}]}),
        encoding="utf-8",
    )

    result = list_grants(claude_dir)

    assert result.grants == []


# ---- add_grant --------------------------------------------------------------


def test_add_grant_creates_new_row_with_generated_id(claude_dir: Path) -> None:
    grant = add_grant(claude_dir, "file", "src/config/secrets.json")

    assert grant.id
    assert grant.kind == "file"
    assert grant.target == "src/config/secrets.json"

    result = list_grants(claude_dir)
    assert result.grants == [grant]


def test_add_grant_persists_to_settings_local_json_only(claude_dir: Path) -> None:
    add_grant(claude_dir, "mcp", "filesystem-mcp")

    assert not (claude_dir / "settings.json").exists()
    data = _settings_local(claude_dir)
    assert len(data["permissionGrants"]) == 1
    assert data["permissionGrants"][0]["kind"] == "mcp"
    assert data["permissionGrants"][0]["target"] == "filesystem-mcp"


def test_add_grant_creates_claude_dir_if_missing(tmp_path: Path) -> None:
    missing = tmp_path / ".claude"
    assert not missing.exists()

    add_grant(missing, "file", "a.txt")

    assert missing.is_dir()
    assert (missing / "settings.local.json").is_file()


def test_add_grant_preserves_other_keys_in_settings_local_json(claude_dir: Path) -> None:
    (claude_dir / "settings.local.json").write_text(json.dumps({"someOtherKey": "value"}), encoding="utf-8")

    add_grant(claude_dir, "file", "a.txt")

    data = _settings_local(claude_dir)
    assert data["someOtherKey"] == "value"
    assert len(data["permissionGrants"]) == 1


def test_add_already_granted_resource_is_idempotent(claude_dir: Path) -> None:
    first = add_grant(claude_dir, "file", "src/secrets.json")
    second = add_grant(claude_dir, "file", "src/secrets.json")

    assert second == first
    result = list_grants(claude_dir)
    assert len(result.grants) == 1


def test_add_same_target_different_kind_is_not_deduped(claude_dir: Path) -> None:
    """kind+target together identify a grant -- same target string under a
    different kind is a distinct resource."""
    add_grant(claude_dir, "file", "shared-name")
    add_grant(claude_dir, "mcp", "shared-name")

    result = list_grants(claude_dir)
    assert len(result.grants) == 2


def test_add_grant_with_leading_trailing_whitespace_is_trimmed(claude_dir: Path) -> None:
    grant = add_grant(claude_dir, "file", "  src/secrets.json  ")
    assert grant.target == "src/secrets.json"


@pytest.mark.parametrize("target", ["", "   ", "\t\n"])
def test_add_grant_rejects_empty_or_whitespace_target(claude_dir: Path, target: str) -> None:
    with pytest.raises(PermissionGrantValidationError):
        add_grant(claude_dir, "file", target)

    # Nothing persisted on rejection.
    assert not (claude_dir / "settings.local.json").exists()


def test_add_grant_rejects_target_over_max_length(claude_dir: Path) -> None:
    too_long = "a" * (MAX_TARGET_LENGTH + 1)

    with pytest.raises(PermissionGrantValidationError):
        add_grant(claude_dir, "file", too_long)

    assert not (claude_dir / "settings.local.json").exists()


def test_add_grant_accepts_target_at_max_length(claude_dir: Path) -> None:
    exactly_max = "a" * MAX_TARGET_LENGTH
    grant = add_grant(claude_dir, "file", exactly_max)
    assert grant.target == exactly_max


def test_add_grant_never_touches_or_creates_settings_json(claude_dir: Path) -> None:
    (claude_dir / "settings.json").write_text(json.dumps({"hooks": {}}), encoding="utf-8")
    original = (claude_dir / "settings.json").read_text(encoding="utf-8")

    add_grant(claude_dir, "file", "a.txt")

    assert (claude_dir / "settings.json").read_text(encoding="utf-8") == original


def test_add_grant_skips_malformed_entries_when_checking_for_duplicates(claude_dir: Path) -> None:
    """A hand-edited settings.local.json with a malformed entry shouldn't
    crash add_grant -- it should just be ignored for dedupe purposes."""
    (claude_dir / "settings.local.json").write_text(
        json.dumps({"permissionGrants": [{"unexpected": "shape"}, "not even a dict"]}), encoding="utf-8"
    )

    grant = add_grant(claude_dir, "file", "a.txt")

    assert grant.target == "a.txt"


# ---- revoke_grant -----------------------------------------------------------


def test_revoke_existing_grant_removes_it_from_list_and_file(claude_dir: Path) -> None:
    grant = add_grant(claude_dir, "file", "a.txt")
    add_grant(claude_dir, "mcp", "some-server")

    revoke_grant(claude_dir, grant.id)

    result = list_grants(claude_dir)
    assert grant.id not in {g.id for g in result.grants}
    assert len(result.grants) == 1
    data = _settings_local(claude_dir)
    assert grant.id not in {g["id"] for g in data["permissionGrants"]}


def test_revoke_unknown_id_raises_not_found(claude_dir: Path) -> None:
    add_grant(claude_dir, "file", "a.txt")

    with pytest.raises(PermissionGrantNotFoundError):
        revoke_grant(claude_dir, "does-not-exist")

    # Existing grant untouched.
    assert len(list_grants(claude_dir).grants) == 1


def test_revoke_already_revoked_id_raises_not_found(claude_dir: Path) -> None:
    grant = add_grant(claude_dir, "file", "a.txt")
    revoke_grant(claude_dir, grant.id)

    with pytest.raises(PermissionGrantNotFoundError):
        revoke_grant(claude_dir, grant.id)


def test_revoke_grant_with_no_settings_local_file_raises_not_found(claude_dir: Path) -> None:
    with pytest.raises(PermissionGrantNotFoundError):
        revoke_grant(claude_dir, "anything")


# ---- API-level: GET/POST/DELETE /api/permission-grants ----------------------


@pytest.fixture
def api_client(claude_dir: Path) -> TestClient:
    app.dependency_overrides[get_claude_dir] = lambda: claude_dir
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_claude_dir, None)


def test_get_endpoint_returns_friendly_empty_state(api_client: TestClient) -> None:
    response = api_client.get("/api/permission-grants")

    assert response.status_code == 200
    assert response.json() == {"grants": []}


def test_post_endpoint_adds_grant_and_returns_it(api_client: TestClient, claude_dir: Path) -> None:
    response = api_client.post("/api/permission-grants", json={"kind": "file", "target": "src/secrets.json"})

    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "file"
    assert body["target"] == "src/secrets.json"
    assert body["id"]

    get_response = api_client.get("/api/permission-grants")
    assert get_response.json()["grants"] == [body]


def test_post_endpoint_is_idempotent_for_same_kind_and_target(api_client: TestClient) -> None:
    first = api_client.post("/api/permission-grants", json={"kind": "mcp", "target": "filesystem-mcp"})
    second = api_client.post("/api/permission-grants", json={"kind": "mcp", "target": "filesystem-mcp"})

    assert first.json() == second.json()
    listed = api_client.get("/api/permission-grants").json()["grants"]
    assert len(listed) == 1


def test_post_endpoint_rejects_empty_target_with_400_envelope(api_client: TestClient, claude_dir: Path) -> None:
    response = api_client.post("/api/permission-grants", json={"kind": "file", "target": "   "})

    assert response.status_code == 400
    body = response.json()
    assert set(body.keys()) == {"error_code", "message", "node_id"}
    assert body["error_code"] == "permission_grants.invalid_target"
    assert body["node_id"] is None
    assert not (claude_dir / "settings.local.json").exists()


def test_post_endpoint_rejects_target_over_max_length_with_400_envelope(
    api_client: TestClient, claude_dir: Path
) -> None:
    too_long = "a" * (MAX_TARGET_LENGTH + 1)

    response = api_client.post("/api/permission-grants", json={"kind": "file", "target": too_long})

    assert response.status_code == 400
    body = response.json()
    assert set(body.keys()) == {"error_code", "message", "node_id"}
    assert body["error_code"] == "permission_grants.invalid_target"
    assert body["node_id"] is None
    assert not (claude_dir / "settings.local.json").exists()


def test_delete_endpoint_revokes_grant(api_client: TestClient, claude_dir: Path) -> None:
    created = api_client.post("/api/permission-grants", json={"kind": "file", "target": "a.txt"}).json()

    response = api_client.delete(f"/api/permission-grants/{created['id']}")

    assert response.status_code == 200
    assert api_client.get("/api/permission-grants").json()["grants"] == []


def test_delete_endpoint_unknown_id_returns_404_envelope(api_client: TestClient) -> None:
    response = api_client.delete("/api/permission-grants/does-not-exist")

    assert response.status_code == 404
    body = response.json()
    assert set(body.keys()) == {"error_code", "message", "node_id"}
    assert body["error_code"] == "permission_grants.not_found"
    assert body["node_id"] is None


@pytest.mark.skipif(os.name == "nt", reason="chmod-based permission denial isn't meaningful on Windows")
@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="running as root ignores permission bits, so this can't force a real PermissionError",
)
def test_get_endpoint_surfaces_error_envelope_on_real_filesystem_failure(
    api_client: TestClient, claude_dir: Path
) -> None:
    """A genuine OSError from `list_grants()` (here: permission denied reading
    `settings.local.json`) must be caught by the gateway's global
    `@app.exception_handler(OSError)` and surfaced as the app's error
    envelope, not propagate as a raw unhandled 500. Nothing here is mocked,
    and the permission is always restored (even on failure)."""
    settings_local = claude_dir / "settings.local.json"
    settings_local.write_text(json.dumps({"permissionGrants": []}), encoding="utf-8")

    original_mode = settings_local.stat().st_mode
    os.chmod(settings_local, 0o000)
    try:
        response = api_client.get("/api/permission-grants")

        assert response.status_code == 500
        body = response.json()
        assert set(body.keys()) == {"error_code", "message", "node_id"}
        assert body["error_code"] == "settings.io_error"
        assert body["node_id"] is None
    finally:
        os.chmod(settings_local, original_mode)


def test_endpoints_never_touch_settings_json(api_client: TestClient, claude_dir: Path) -> None:
    (claude_dir / "settings.json").write_text(json.dumps({"hooks": {}}), encoding="utf-8")
    original = (claude_dir / "settings.json").read_text(encoding="utf-8")

    created = api_client.post("/api/permission-grants", json={"kind": "file", "target": "a.txt"}).json()
    api_client.get("/api/permission-grants")
    api_client.delete(f"/api/permission-grants/{created['id']}")

    assert (claude_dir / "settings.json").read_text(encoding="utf-8") == original
