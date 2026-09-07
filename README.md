# Claude Wrapper

A web app that replaces the terminal for AI agent orchestration and hand-off.
See `_bmad-output/planning-artifacts/` for the PRD, Architecture spine, and
UX design specs that govern this build.

## Prerequisites

- Node.js (for `frontend/`)
- Python 3.12+ and [`uv`](https://docs.astral.sh/uv/) (for `backend/`)
- Docker + Docker Compose (for local Redis)

## 1. Start Redis

Redis will be used at runtime as the LangGraph checkpoint store (AD-9) once
that wiring lands in a later story — this story only provisions the local
service. Start it via Docker Compose before running the backend:

```bash
docker compose up -d redis
```

Verify it's up (if `redis-cli` isn't installed locally, run it inside the
container instead):

```bash
redis-cli -h localhost -p 6379 ping
# or: docker compose exec redis redis-cli ping
# -> PONG
```

To stop it:

```bash
docker compose down
```

## 2. Backend (FastAPI)

Install dependencies and run the dev server from `backend/`:

```bash
cd backend
uv sync
uv run uvicorn gateway.main:app --reload --port 8000
```

Verify it's up:

```bash
curl -sf localhost:8000/health
# -> {"status":"ok"}
```

## 3. Frontend (Next.js)

Install dependencies and run the dev server from `frontend/`:

```bash
cd frontend
npm install
npm run dev
```

Then open [http://localhost:3000](http://localhost:3000).

## Project layout

See the Architecture spine's Source Tree
(`_bmad-output/planning-artifacts/architecture/architecture-claude-wrapper-2026-08-30/ARCHITECTURE-SPINE.md`)
for the full, authoritative directory map. At a glance:

- `frontend/` — Next.js 16 app (TypeScript, App Router, Tailwind CSS)
- `backend/gateway/` — FastAPI app, WebSocket/SSE handlers
- `backend/brain/` — Settings Router + Meta-Planner (later stories)
- `backend/engine/` — LangGraph orchestrator/workers/checkpoint (later stories)
- `backend/dynamic_tools/` — FastMCP bridge synthesis (later stories)
- `backend/telemetry/` — opt-in usage telemetry emission (deferred to v2)
- `docker-compose.yml` — local Redis 8.x service
