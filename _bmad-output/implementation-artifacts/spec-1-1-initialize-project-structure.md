---
title: 'Story 1.1: Initialize project structure'
type: 'chore'
created: '2026-09-07'
status: 'done'
review_loop_iteration: 0
context: []
baseline_commit: 'fb4ee7af92ab99c83efb4e706efb2071d96168dd'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The project has no code yet — only planning artifacts and BMad tooling exist, so no story in any epic has anything to build on.

**Approach:** Scaffold a Next.js 16.3.x frontend and FastAPI 0.141.x backend matching the Architecture spine's exact source tree, with Redis 8.x running locally and every stack-pin dependency locked, so every following story starts from a real, working project.

## Boundaries & Constraints

**Always:** Match the Architecture spine's Source Tree exactly (directory names and nesting). Pin every dependency to the Architecture spine's Stack table verbatim (Next.js 16.3.x, FastAPI 0.141.x with `starlette>=1.0.1`, LangGraph 1.2.x, FastMCP 3.4.5+, Pydantic 2.13.x, redis-py 8.x). Use `uv` for Python dependency management. Frontend uses TypeScript, App Router, and Tailwind CSS, with DESIGN.md's tokens (light/dark colors, spacing scale, 8/16/20/999px radii) wired into the Tailwind theme. Redis runs via Docker Compose.

**Ask First:** None anticipated — CSS approach and dependency manager were already decided before this spec.

**Never:** Implement any feature logic (Settings Router, Meta-Planner, Engine, Dynamic Tools, telemetry emission) or any UI beyond the default scaffolded page — this story is scaffolding only. Never scaffold `telemetry-collector/` or add logic to `backend/telemetry/` — FR-26 is deferred to v2. Never pre-build the deeper subpackages later epics own (`brain/meta_planner/`, `engine/orchestrator/`, `engine/workers/`, `engine/checkpoint/`, `frontend/components/canvas/` `/task-list/` `/node-inspector/`) — only Epic 1's own subpackages get real content now.

</frozen-after-approval>

## Code Map

- `frontend/` -- new Next.js 16.3.x app (TypeScript, App Router, Tailwind CSS)
- `frontend/tailwind.config.ts` -- DESIGN.md tokens wired as theme extensions
- `backend/pyproject.toml` -- uv-managed manifest pinning all Architecture spine stack versions
- `backend/gateway/main.py` -- FastAPI app entrypoint with a `/health` endpoint
- `backend/brain/__init__.py`, `backend/engine/__init__.py`, `backend/dynamic_tools/__init__.py`, `backend/telemetry/__init__.py` -- empty placeholder packages matching the Architecture spine's source tree, owned by later epics
- `docker-compose.yml` -- local Redis 8.x service definition
- `.claude/` -- already exists (BMad tooling); confirm present, no action needed

## Tasks & Acceptance

**Execution:**
- [x] `frontend/` -- scaffold Next.js 16.3.x app (TypeScript, App Router, Tailwind CSS) -- gives every frontend story a real app to add to
- [x] `frontend/tailwind.config.ts` -- wire DESIGN.md's light/dark color, spacing, and radius tokens into the Tailwind theme -- makes design tokens available without re-deriving them per component
- [x] `backend/pyproject.toml` -- create uv-managed Python project, pin all Architecture spine stack versions -- locks dependency versions before any backend story starts
- [x] `backend/gateway/main.py` -- minimal FastAPI 0.141.x app with a `/health` endpoint, `starlette>=1.0.1` pinned -- gives the backend a bootable entrypoint
- [x] `backend/brain/__init__.py`, `backend/engine/__init__.py`, `backend/dynamic_tools/__init__.py`, `backend/telemetry/__init__.py` -- empty placeholder packages -- reserves the Architecture spine's structure without building ahead of need
- [x] `docker-compose.yml` -- define a local Redis 8.x service on the default port -- satisfies AD-9's required local Redis dependency
- [x] `README.md` -- document `docker compose up`, frontend/backend install, and both dev-server start commands -- onboarding for Story 1.2

**Acceptance Criteria:**
- Given a clean checkout of this branch, when I run the frontend's dev server, then it boots without error and serves the default page
- Given a clean checkout of this branch, when I run the backend's dev server and hit `/health`, then it returns a 200 response
- Given `docker compose up` for Redis, when I connect with `redis-cli ping`, then it responds `PONG`
- Given the Architecture spine's Source Tree, when I compare it to the scaffolded directories, then `frontend/`, `backend/gateway/`, `backend/brain/`, `backend/engine/`, `backend/dynamic_tools/`, `backend/telemetry/` all exist and match
- Given the Architecture spine's Stack table, when I inspect `frontend/package.json` and `backend/pyproject.toml`, then every pinned version matches exactly

## Spec Change Log

- **Triggering finding:** verification-gap review flagged the Verification section's dependency-version-check command as broken — `langgraph.__version__` does not exist (LangGraph exposes no `__version__` attribute), so the command throws `AttributeError` and, because Python evaluates all `print()` arguments before the call, masks verification of all six pinned packages, not just langgraph.
- **What was amended:** the Verification section's version-check command, swapped from `pkg.__version__` attribute access to `importlib.metadata.version("pkg")` for all six packages uniformly.
- **Known-bad state avoided:** treating this as a full `bad_spec` loopback (reverting and re-deriving all of Story 1.1's already-verified, working scaffolding) purely to fix one broken diagnostic command — pure waste, since every one of the six pinned packages installed correctly and was already independently verified via `importlib.metadata` by both the implementation subagent and the verification-gap reviewer.
- **KEEP:** the scaffolded `frontend/`, `backend/` trees, `docker-compose.yml`, and all dependency pins are correct as implemented and must not be regenerated.

## Verification

**Commands:**
- `cd frontend && npm run build` -- expected: succeeds with no errors
- `cd backend && uv run uvicorn gateway.main:app --port 8000` then `curl -sf localhost:8000/health` -- expected: 200 response
- `docker compose up -d redis && redis-cli ping` -- expected: `PONG`
- `uv run python -c "import importlib.metadata as m; [print(p, m.version(p)) for p in ('fastapi','starlette','langgraph','fastmcp','pydantic','redis')]"` -- expected: versions match the pins above (langgraph has no `__version__` attribute, so `importlib.metadata.version()` is used for all six packages for consistency)

## Suggested Review Order

**Backend entrypoint & dependency pins**

- Entry point: bootable FastAPI app with the version now recorded on the app object itself.
  [`main.py:10`](../../backend/gateway/main.py#L10)

- Health endpoint later stories and this story's own verification both depend on.
  [`main.py:13`](../../backend/gateway/main.py#L13)

- Every Architecture-spine stack pin locked in one place before any backend story starts.
  [`pyproject.toml:6`](../../backend/pyproject.toml#L6)

**Frontend design-token wiring**

- DESIGN.md's full color palette (light + dark) extended into Tailwind's theme.
  [`tailwind.config.ts:22`](../../frontend/tailwind.config.ts#L22)

- Spacing scale namespaced under `space-` to avoid silently overriding Tailwind's default numeric scale.
  [`tailwind.config.ts:71`](../../frontend/tailwind.config.ts#L71)

- `background`/`foreground` CSS vars now resolve to DESIGN.md's `bg`/`text1` tokens instead of stock placeholders.
  [`globals.css:5`](../../frontend/app/globals.css#L5)

- Body now applies the DESIGN.md system-font stack via `font-sans`, replacing the unused Geist webfont wiring.
  [`globals.css:24`](../../frontend/app/globals.css#L24)

- Geist font loading removed since DESIGN.md specifies a system font stack, not a webfont.
  [`layout.tsx:1`](../../frontend/app/layout.tsx#L1)

**Local Redis service**

- AD-9's required AOF persistence mode, now with a restart policy and healthcheck grace period.
  [`docker-compose.yml:9`](../../docker-compose.yml#L9)

**Peripherals**

- Onboarding docs corrected to not overclaim Redis is wired in yet, plus teardown and container-exec fallback instructions.
  [`README.md:15`](../../README.md#L15)

- `engines` field pins the minimum Node version the scaffolded Next.js 16 app expects.
  [`package.json:5`](../../frontend/package.json#L5)
