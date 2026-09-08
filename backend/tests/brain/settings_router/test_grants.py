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
    update_grant,
)
from gateway.main import app, get_claude_dir


def _settings_local(claude_dir: Path) -> dict:
    return json.loads((claude_dir / "settings.local.json").read_text(encoding="utf-8"))


def _settings_team(claude_dir: Path) -> dict:
    return json.loads((claude_dir / "settings.json").read_text(encoding="utf-8"))


# ---- list_grants ------------------------------------------------------------


def test_no_claude_dir_yields_empty_grants_list(tmp_path: Path) -> None:
    missing = tmp_path / ".claude"
    assert not missing.exists()

    result = list_grants(missing)

    assert result.grants == []


def test_no_settings_files_yields_empty_grants_list(claude_dir: Path) -> None:
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


def test_list_grants_reads_team_scoped_entries_from_settings_json(claude_dir: Path) -> None:
    """`settings.json` (team scope) is a real, first-class source of grants --
    not just settings.local.json."""
    (claude_dir / "settings.json").write_text(
        json.dumps({"permissionGrants": [{"id": "x", "kind": "mcp", "target": "team-server"}]}),
        encoding="utf-8",
    )

    result = list_grants(claude_dir)

    assert len(result.grants) == 1
    assert result.grants[0].scope == "team"
    assert result.grants[0].target == "team-server"


def test_list_grants_combines_both_scopes_and_tags_each(claude_dir: Path) -> None:
    (claude_dir / "settings.json").write_text(
        json.dumps({"permissionGrants": [{"id": "t1", "kind": "mcp", "target": "team-server"}]}),
        encoding="utf-8",
    )
    (claude_dir / "settings.local.json").write_text(
        json.dumps({"permissionGrants": [{"id": "l1", "kind": "file", "target": "src/secrets.json"}]}),
        encoding="utf-8",
    )

    result = list_grants(claude_dir)

    by_scope = {g.scope: g for g in result.grants}
    assert len(result.grants) == 2
    assert by_scope["team"].target == "team-server"
    assert by_scope["local"].target == "src/secrets.json"


# ---- add_grant ----------------------------------------------------------------


def test_add_grant_creates_new_row_with_generated_id(claude_dir: Path) -> None:
    grant = add_grant(claude_dir, "file", "src/config/secrets.json")

    assert grant.id
    assert grant.kind == "file"
    assert grant.target == "src/config/secrets.json"
    assert grant.scope == "local"

    result = list_grants(claude_dir)
    assert result.grants == [grant]


def test_add_grant_defaults_to_local_scope_and_persists_to_settings_local_json_only(claude_dir: Path) -> None:
    add_grant(claude_dir, "mcp", "filesystem-mcp")

    assert not (claude_dir / "settings.json").exists()
    data = _settings_local(claude_dir)
    assert len(data["permissionGrants"]) == 1
    assert data["permissionGrants"][0]["kind"] == "mcp"
    assert data["permissionGrants"][0]["target"] == "filesystem-mcp"
    # scope is derived from which file the entry lives in, never persisted
    # inside the entry itself.
    assert "scope" not in data["permissionGrants"][0]


def test_add_grant_with_team_scope_writes_to_settings_json(claude_dir: Path) -> None:
    grant = add_grant(claude_dir, "file", "src/secrets.json", scope="team")

    assert grant.scope == "team"
    assert not (claude_dir / "settings.local.json").exists()
    data = _settings_team(claude_dir)
    assert data["permissionGrants"] == [{"id": grant.id, "kind": "file", "target": "src/secrets.json"}]


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


def test_add_grant_preserves_other_keys_in_settings_json(claude_dir: Path) -> None:
    """Boundaries: this app never touches Claude Code's own reserved keys
    (e.g. `hooks`) when writing a team-scoped grant into settings.json."""
    (claude_dir / "settings.json").write_text(json.dumps({"hooks": {"PreToolUse": []}}), encoding="utf-8")

    add_grant(claude_dir, "file", "a.txt", scope="team")

    data = _settings_team(claude_dir)
    assert data["hooks"] == {"PreToolUse": []}
    assert len(data["permissionGrants"]) == 1


def test_add_already_granted_resource_is_idempotent_within_same_scope(claude_dir: Path) -> None:
    first = add_grant(claude_dir, "file", "src/secrets.json")
    second = add_grant(claude_dir, "file", "src/secrets.json")

    assert second == first
    result = list_grants(claude_dir)
    assert len(result.grants) == 1


def test_add_same_kind_and_target_in_different_scopes_is_not_deduped(claude_dir: Path) -> None:
    """A personal grant and a team grant for the same resource are two
    independent, both-apply facts -- not a collision -- matching how
    Claude Code's own real permission arrays merge rather than conflict
    across settings files."""
    local_grant = add_grant(claude_dir, "file", "src/secrets.json", scope="local")
    team_grant = add_grant(claude_dir, "file", "src/secrets.json", scope="team")

    assert local_grant.id != team_grant.id
    result = list_grants(claude_dir)
    assert len(result.grants) == 2


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


def test_add_grant_with_default_local_scope_never_touches_or_creates_settings_json(claude_dir: Path) -> None:
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


# ---- revoke_grant -------------------------------------------------------------


def test_revoke_existing_local_grant_removes_it_from_list_and_file(claude_dir: Path) -> None:
    grant = add_grant(claude_dir, "file", "a.txt")
    add_grant(claude_dir, "mcp", "some-server")

    revoke_grant(claude_dir, grant.id)

    result = list_grants(claude_dir)
    assert grant.id not in {g.id for g in result.grants}
    assert len(result.grants) == 1
    data = _settings_local(claude_dir)
    assert grant.id not in {g["id"] for g in data["permissionGrants"]}


def test_revoke_existing_team_grant_removes_it_from_settings_json(claude_dir: Path) -> None:
    grant = add_grant(claude_dir, "file", "a.txt", scope="team")

    revoke_grant(claude_dir, grant.id)

    result = list_grants(claude_dir)
    assert result.grants == []
    data = _settings_team(claude_dir)
    assert data["permissionGrants"] == []


def test_revoke_finds_the_grant_regardless_of_which_scope_it_is_in(claude_dir: Path) -> None:
    """The same revoke call works whether the grant is local or team --
    callers never need to know which file a grant lives in."""
    local_grant = add_grant(claude_dir, "file", "local.txt", scope="local")
    team_grant = add_grant(claude_dir, "file", "team.txt", scope="team")

    revoke_grant(claude_dir, team_grant.id)
    revoke_grant(claude_dir, local_grant.id)

    assert list_grants(claude_dir).grants == []


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


def test_revoke_grant_with_no_settings_files_raises_not_found(claude_dir: Path) -> None:
    with pytest.raises(PermissionGrantNotFoundError):
        revoke_grant(claude_dir, "anything")


# ---- update_grant ---------------------------------------------------------------


def test_update_grant_edits_target_in_place(claude_dir: Path) -> None:
    grant = add_grant(claude_dir, "file", "old.txt")

    updated = update_grant(claude_dir, grant.id, target="new.txt")

    assert updated.id == grant.id
    assert updated.target == "new.txt"
    assert updated.scope == "local"
    result = list_grants(claude_dir)
    assert len(result.grants) == 1
    assert result.grants[0].target == "new.txt"


def test_update_grant_edits_kind_in_place(claude_dir: Path) -> None:
    grant = add_grant(claude_dir, "file", "ambiguous-name")

    updated = update_grant(claude_dir, grant.id, kind="mcp")

    assert updated.kind == "mcp"
    assert updated.target == "ambiguous-name"


def test_update_grant_moves_from_local_to_team(claude_dir: Path) -> None:
    grant = add_grant(claude_dir, "file", "a.txt", scope="local")

    updated = update_grant(claude_dir, grant.id, scope="team")

    assert updated.id == grant.id
    assert updated.scope == "team"
    assert _settings_local(claude_dir)["permissionGrants"] == []
    assert _settings_team(claude_dir)["permissionGrants"] == [{"id": grant.id, "kind": "file", "target": "a.txt"}]


def test_update_grant_moves_from_team_to_local(claude_dir: Path) -> None:
    grant = add_grant(claude_dir, "file", "a.txt", scope="team")

    updated = update_grant(claude_dir, grant.id, scope="local")

    assert updated.scope == "local"
    assert _settings_team(claude_dir)["permissionGrants"] == []
    assert _settings_local(claude_dir)["permissionGrants"] == [{"id": grant.id, "kind": "file", "target": "a.txt"}]


def test_update_grant_moving_onto_an_identical_existing_grant_merges_instead_of_duplicating(claude_dir: Path) -> None:
    """Same idempotency rule as add_grant: moving a grant to a scope that
    already has the same kind+target merges into the existing one rather
    than creating a duplicate."""
    moving = add_grant(claude_dir, "file", "shared.txt", scope="local")
    destination = add_grant(claude_dir, "file", "shared.txt", scope="team")

    result = update_grant(claude_dir, moving.id, scope="team")

    assert result.id == destination.id
    all_grants = list_grants(claude_dir).grants
    assert len(all_grants) == 1
    assert all_grants[0].id == destination.id


def test_update_grant_preserves_other_grants_in_the_same_file(claude_dir: Path) -> None:
    grant = add_grant(claude_dir, "file", "a.txt")
    other = add_grant(claude_dir, "mcp", "some-server")

    update_grant(claude_dir, grant.id, target="b.txt")

    remaining = {g.id: g for g in list_grants(claude_dir).grants}
    assert remaining[other.id].target == "some-server"
    assert remaining[grant.id].target == "b.txt"


def test_update_grant_unknown_id_raises_not_found(claude_dir: Path) -> None:
    with pytest.raises(PermissionGrantNotFoundError):
        update_grant(claude_dir, "does-not-exist", target="anything")


@pytest.mark.parametrize("target", ["", "   "])
def test_update_grant_rejects_empty_or_whitespace_target(claude_dir: Path, target: str) -> None:
    grant = add_grant(claude_dir, "file", "a.txt")

    with pytest.raises(PermissionGrantValidationError):
        update_grant(claude_dir, grant.id, target=target)

    # Original grant untouched on rejection.
    assert list_grants(claude_dir).grants == [grant]


def test_update_grant_rejects_target_over_max_length(claude_dir: Path) -> None:
    grant = add_grant(claude_dir, "file", "a.txt")
    too_long = "a" * (MAX_TARGET_LENGTH + 1)

    with pytest.raises(PermissionGrantValidationError):
        update_grant(claude_dir, grant.id, target=too_long)

    assert list_grants(claude_dir).grants == [grant]


def test_update_grant_with_no_fields_is_a_no_op(claude_dir: Path) -> None:
    grant = add_grant(claude_dir, "file", "a.txt")

    updated = update_grant(claude_dir, grant.id)

    assert updated == grant


# ---- API-level: GET/POST/PATCH/DELETE /api/permission-grants -----------------


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
    assert body["scope"] == "local"
    assert body["id"]

    get_response = api_client.get("/api/permission-grants")
    assert get_response.json()["grants"] == [body]


def test_post_endpoint_with_team_scope_writes_to_settings_json(api_client: TestClient, claude_dir: Path) -> None:
    response = api_client.post(
        "/api/permission-grants", json={"kind": "mcp", "target": "team-server", "scope": "team"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["scope"] == "team"
    assert _settings_team(claude_dir)["permissionGrants"][0]["target"] == "team-server"


def test_post_endpoint_is_idempotent_for_same_kind_target_and_scope(api_client: TestClient) -> None:
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


def test_patch_endpoint_updates_target(api_client: TestClient) -> None:
    created = api_client.post("/api/permission-grants", json={"kind": "file", "target": "old.txt"}).json()

    response = api_client.patch(f"/api/permission-grants/{created['id']}", json={"target": "new.txt"})

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["target"] == "new.txt"


def test_patch_endpoint_moves_scope(api_client: TestClient, claude_dir: Path) -> None:
    created = api_client.post("/api/permission-grants", json={"kind": "file", "target": "a.txt"}).json()
    assert created["scope"] == "local"

    response = api_client.patch(f"/api/permission-grants/{created['id']}", json={"scope": "team"})

    assert response.status_code == 200
    assert response.json()["scope"] == "team"
    assert _settings_team(claude_dir)["permissionGrants"][0]["id"] == created["id"]


def test_patch_endpoint_unknown_id_returns_404_envelope(api_client: TestClient) -> None:
    response = api_client.patch("/api/permission-grants/does-not-exist", json={"target": "anything"})

    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "permission_grants.not_found"


def test_patch_endpoint_rejects_empty_target_with_400_envelope(api_client: TestClient) -> None:
    created = api_client.post("/api/permission-grants", json={"kind": "file", "target": "a.txt"}).json()

    response = api_client.patch(f"/api/permission-grants/{created['id']}", json={"target": "   "})

    assert response.status_code == 400
    assert response.json()["error_code"] == "permission_grants.invalid_target"


def test_delete_endpoint_revokes_grant(api_client: TestClient, claude_dir: Path) -> None:
    created = api_client.post("/api/permission-grants", json={"kind": "file", "target": "a.txt"}).json()

    response = api_client.delete(f"/api/permission-grants/{created['id']}")

    assert response.status_code == 200
    assert api_client.get("/api/permission-grants").json()["grants"] == []


def test_delete_endpoint_revokes_team_scoped_grant(api_client: TestClient, claude_dir: Path) -> None:
    created = api_client.post(
        "/api/permission-grants", json={"kind": "file", "target": "a.txt", "scope": "team"}
    ).json()

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


def test_endpoints_with_default_local_scope_never_touch_settings_json(api_client: TestClient, claude_dir: Path) -> None:
    (claude_dir / "settings.json").write_text(json.dumps({"hooks": {}}), encoding="utf-8")
    original = (claude_dir / "settings.json").read_text(encoding="utf-8")

    created = api_client.post("/api/permission-grants", json={"kind": "file", "target": "a.txt"}).json()
    api_client.get("/api/permission-grants")
    api_client.patch(f"/api/permission-grants/{created['id']}", json={"target": "b.txt"})
    api_client.delete(f"/api/permission-grants/{created['id']}")

    assert (claude_dir / "settings.json").read_text(encoding="utf-8") == original
