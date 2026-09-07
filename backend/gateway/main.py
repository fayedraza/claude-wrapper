"""FastAPI Gateway entrypoint.

Story 1.1 scaffolded a bare `/health` endpoint. Story 1.2 adds the Settings
Router surface (FR-1/FR-2): `POST /api/settings/propose` classifies a
natural-language request into proposed `.claude/` changes without writing
anything; `POST /api/settings/apply` writes exactly one approved change.
Story 1.3 adds `GET /api/settings/current` (FR-3): a strictly read-only
summary of what's already configured in `.claude/`, walked fresh on every
request. Story 1.4 adds the Permission Manager surface (FR-6 + the standing
half of FR-5): `GET/POST /api/permission-grants` and
`DELETE /api/permission-grants/{id}`, reading/writing only
`.claude/settings.local.json`. WebSocket/SSE handlers and Redis-mirror reads
(AD-9) are built in later stories -- see
`_bmad-output/planning-artifacts/architecture/architecture-claude-wrapper-2026-08-30/ARCHITECTURE-SPINE.md`.
"""

from pathlib import Path

import anthropic
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from brain.settings_router.apply import apply_action
from brain.settings_router.grants import (
    PermissionGrantNotFoundError,
    PermissionGrantValidationError,
    add_grant,
    list_grants,
    revoke_grant,
)
from brain.settings_router.models import (
    AddPermissionGrantRequest,
    CurrentConfiguration,
    PermissionGrant,
    PermissionGrantsList,
    SettingAction,
    SettingsRouterOutput,
)
from brain.settings_router.router import SettingsPathError, classify_request
from brain.settings_router.summary import get_current_configuration
from gateway.errors import ErrorEnvelope

app = FastAPI(title="Claude Wrapper Gateway", version="0.1.0")

# Local dev only (AD notes: no staging/production distinction in v1) -- the
# frontend dev server runs on a different origin (Next.js default :3000)
# than the gateway (:8000).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# backend/gateway/main.py -> parents[1] is backend/, parents[2] is the repo
# root, where the git-aware .claude/ control center Story 1.1 confirmed
# lives. Overridable so tests never point this at the real repo's .claude/.
DEFAULT_CLAUDE_DIR = Path(__file__).resolve().parents[2] / ".claude"


def get_claude_dir() -> Path:
    """FastAPI dependency for the `.claude/` control-center directory. Overridden in tests."""
    return DEFAULT_CLAUDE_DIR


def get_anthropic_client() -> anthropic.Anthropic:
    """FastAPI dependency for the Anthropic client (env-based auth). Overridden in tests
    so no test ever calls the live API."""
    return anthropic.Anthropic()


class ProposeRequest(BaseModel):
    request: str


@app.exception_handler(SettingsPathError)
async def handle_settings_path_error(request: Request, exc: SettingsPathError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=ErrorEnvelope(error_code="settings.invalid_path", message=str(exc)).model_dump(),
    )


@app.exception_handler(anthropic.AnthropicError)
async def handle_anthropic_error(request: Request, exc: anthropic.AnthropicError) -> JSONResponse:
    # Covers every anthropic.APIError subclass (rate limit, timeout, auth, ...) --
    # see router.classify_request for the one additional case normalized into this
    # family: the SDK's local credential-resolution failure (raised as a bare
    # TypeError, not an APIError, when no credentials can be resolved at all).
    return JSONResponse(
        status_code=502,
        content=ErrorEnvelope(error_code="settings.llm_error", message=str(exc)).model_dump(),
    )


@app.exception_handler(OSError)
async def handle_os_error(request: Request, exc: OSError) -> JSONResponse:
    # Filesystem failures during apply_action (permission denied, disk full, a
    # path colliding with an existing directory of the same name, filename too
    # long, ...) -- surface the same error envelope instead of a raw 500.
    return JSONResponse(
        status_code=500,
        content=ErrorEnvelope(error_code="settings.io_error", message=str(exc)).model_dump(),
    )


@app.exception_handler(PermissionGrantValidationError)
async def handle_permission_grant_validation_error(request: Request, exc: PermissionGrantValidationError) -> JSONResponse:
    # I/O matrix: "Add with empty/whitespace target -- Rejected, 400 envelope".
    return JSONResponse(
        status_code=400,
        content=ErrorEnvelope(error_code="permission_grants.invalid_target", message=str(exc)).model_dump(),
    )


@app.exception_handler(PermissionGrantNotFoundError)
async def handle_permission_grant_not_found_error(request: Request, exc: PermissionGrantNotFoundError) -> JSONResponse:
    # I/O matrix: "Revoke unknown/already-revoked id -- Error shown, list re-fetches", 404 envelope.
    return JSONResponse(
        status_code=404,
        content=ErrorEnvelope(error_code="permission_grants.not_found", message=str(exc)).model_dump(),
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/settings/propose", response_model=SettingsRouterOutput)
def propose_settings(
    payload: ProposeRequest,
    claude_dir: Path = Depends(get_claude_dir),
    client: anthropic.Anthropic = Depends(get_anthropic_client),
) -> SettingsRouterOutput:
    """FR-1: classify a natural-language request into proposed changes.

    Reads live on-disk `.claude/` state as context and never writes
    anything -- writing only happens via `/api/settings/apply` after
    explicit approval.
    """
    return classify_request(payload.request, claude_dir, client)


@app.get("/api/settings/current", response_model=CurrentConfiguration)
def current_configuration(claude_dir: Path = Depends(get_claude_dir)) -> CurrentConfiguration:
    """FR-3: read-only summary of what's already configured in `.claude/`.

    Walks live on-disk state fresh on every request (no cached snapshot) and
    never writes anything.
    """
    return get_current_configuration(claude_dir)


@app.post("/api/settings/apply")
def apply_settings(
    action: SettingAction,
    claude_dir: Path = Depends(get_claude_dir),
) -> dict[str, str]:
    """FR-2: write, update, or revoke exactly the one approved change.

    Only called after the user presses Approve & Apply on the exact
    previewed action; a rejected proposal never reaches this endpoint.
    """
    apply_action(claude_dir, action)
    return {"status": "applied", "file_path": action.file_path, "action": action.action}


@app.get("/api/permission-grants", response_model=PermissionGrantsList)
def get_permission_grants(claude_dir: Path = Depends(get_claude_dir)) -> PermissionGrantsList:
    """FR-6: list every grant currently persisted in `.claude/settings.local.json`.

    No grants yet -- an empty list, friendly empty state (I/O matrix), never
    an error.
    """
    return list_grants(claude_dir)


@app.post("/api/permission-grants", response_model=PermissionGrant)
def create_permission_grant(
    payload: AddPermissionGrantRequest,
    claude_dir: Path = Depends(get_claude_dir),
) -> PermissionGrant:
    """FR-6: add a grant anytime, no run required.

    Idempotent for an already-granted `kind`+`target` pair -- the existing
    grant is returned, not duplicated.
    """
    return add_grant(claude_dir, payload.kind, payload.target)


@app.delete("/api/permission-grants/{grant_id}")
def delete_permission_grant(
    grant_id: str,
    claude_dir: Path = Depends(get_claude_dir),
) -> dict[str, str]:
    """FR-6: revoke one grant by id, removing it from `.claude/settings.local.json`."""
    revoke_grant(claude_dir, grant_id)
    return {"status": "revoked", "id": grant_id}
