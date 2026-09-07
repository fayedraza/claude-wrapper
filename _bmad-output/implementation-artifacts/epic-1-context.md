# Epic 1 Context: Project Configuration, Settings & Permissions

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Stand up the project itself, then let a developer configure `.claude/` via natural language, review its current state, and manage standing file/MCP permission grants — all without ever running an agent. This is the first surface any user touches, fully standalone from every other epic.

## Stories

- Story 1.1: Initialize project structure
- Story 1.2: Submit a natural-language settings request and approve the proposed change
- Story 1.3: View current `.claude/` configuration
- Story 1.4: View and manage permission grants between runs

## Requirements & Constraints

- Configuration requests are classified into one of exactly 8 `target_category` values: `team_instructions`, `local_instructions`, `settings.json`, `settings.local.json`, `rule`, `skill`, `command`, `agent`. Never invent a category label, and an MCP grant is never a `target_category` — it belongs to the permission-grant model, not Settings.
- Nothing is ever written to `.claude/` without an explicit approval step; a rejection touches no files.
- The current-configuration view must reflect actual on-disk state, never a cached snapshot.
- Permission grants (files/MCP servers) can be viewed and modified independent of any run being active; adding a new grant never requires re-approving prior ones.
- Opt-in usage telemetry (originally scoped here) is explicitly deferred to v2 — do not build it.

## Technical Decisions

- Greenfield project, no starter template. Source tree per the Architecture spine: `frontend/` (Next.js) and `backend/` with `brain/`, `engine/`, `dynamic_tools/`, `telemetry/` subpackages.
- Stack pins: Next.js 16.3.x, FastAPI 0.141.x (pin `starlette>=1.0.1`), LangGraph (Python) 1.2.x, FastMCP (Python) 3.4.5+, Pydantic 2.13.x, redis-py 8.x (RESP3 default). Redis 8.x is a required local runtime dependency (not SQLite), run via Docker Compose or local install.
- Naming conventions: `snake_case` for Python identifiers and JSON fields; `PascalCase` for Pydantic models and TS types; human-readable `node_id` slugs, never opaque UUIDs; ISO 8601 UTC timestamps everywhere; a single error envelope shape (`error_code`, `message`, `node_id`).

## UX & Interaction Patterns

- "Flight Tracker" color theme, implemented as real switchable light/dark modes, not a single fixed palette.
- System font stack for all UI text; monospace reserved strictly for literal file paths, config filenames, and raw values — never for prose or labels.
- Rounded shape system (8/16/20px radii, 999px pill chips) with soft-shadow elevation tokens, applied consistently.
- Accessibility floor: WCAG AA-ish contrast, full keyboard navigation, visible `:focus-visible` states on every interactive element.
- Proposed-change card component (used for the settings-approval story): target path, a category chip using one of the 8 real `target_category` values, an action badge (create/update/revoke), a plain-language summary, a content preview, gated behind explicit Approve & Apply / Reject.
- Voice and tone: plain, grounded, factual copy — no hype language, no exclamation points, no celebratory/apologetic framing.

## Cross-Story Dependencies

- Story 1.1 is the prerequisite for everything else in this epic — it creates the bare `.claude/` directory that Story 1.2 populates.
- Story 1.4 (permission grants) only covers the standing grant-state change. The "immediately cut off a live agent using a just-revoked resource" behavior is out of scope here and is built later, in a different epic, as an extension of this story.
