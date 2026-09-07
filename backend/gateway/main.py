"""FastAPI Gateway entrypoint.

Scaffolding only (Story 1.1): a bootable app with a `/health` endpoint.
WebSocket/SSE handlers and Redis-mirror reads (AD-9) are built in later
stories — see `_bmad-output/planning-artifacts/architecture/architecture-claude-wrapper-2026-08-30/ARCHITECTURE-SPINE.md`.
"""

from fastapi import FastAPI

app = FastAPI(title="Claude Wrapper Gateway", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
