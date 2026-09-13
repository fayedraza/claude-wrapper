---
title: 'Story 2.1: Decompose a task into agents'
type: 'feature'
created: '2026-09-13'
status: 'done'
review_loop_iteration: 0
context: []
baseline_commit: '7e4842c928467c10fdefc9fb6d929c87baa010ad'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** A developer can't see how their plain-language task will be broken into agents before anything runs — only a black-box terminal hand-off exists today.

**Approach:** A Meta-Planner endpoint asks Claude to decompose a submitted intent into a main orchestrator plus subagents (one-line responsibility + dependency edges each), returned as a `DagBlueprint`, rendered as a list on the app's home page.

## Boundaries & Constraints

**Always:** `AgentSpec`/`DagBlueprint` live in `backend/brain/meta_planner/`, follow the Settings Router's LLM-call pattern exactly (`client.messages.parse(output_format=DagBlueprint)`). `node_id`s are sanitized and dedup-checked server-side (reuse `sanitize_slug`) — never trust the LLM's slug for uniqueness. Exactly one agent has `parent_id: null`; every other `parent_id`/`depends_on` entry resolves to a `node_id` in the same response. Endpoint is read-only: no `.claude/` write, no checkpoint store, nothing executes.

**Ask First:** None — a preview only; nothing executes or persists.

**Never:** No context graph, flight path, or cost estimate (Stories 2.2/2.3). No approve/reject affordance on the rendered list (that's Epic 3's Pre-Flight checklist). No execution of any kind.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Existing codebase | Non-empty intent; project root has files beyond `.claude/`/`.git` | `DagBlueprint`, 1 orchestrator + >=0 subagents, valid refs | N/A |
| New/empty codebase | Non-empty intent; no source files | Same shape, greenfield-scoped agents | N/A |
| Blank intent | `intent` is `""`/whitespace | 400, no LLM call | `MetaPlannerValidationError` -> `meta_planner.invalid_intent` |
| LLM fails / unparseable | API error, timeout, no creds, or `parsed_output is None` | 502 | `MetaPlannerLLMError` -> `meta_planner.llm_error` |

</frozen-after-approval>

## Code Map

- `backend/gateway/main.py:81-84,145-157` -- Depends pattern + `propose_settings` endpoint shape to mirror.
- `backend/brain/settings_router/router.py:20-21,178-223` -- `classify_request()`: constants, `client.messages.parse(output_format=...)`, error normalization, `parsed_output is None` check. Mirror for `decompose_task()`.
- `backend/brain/settings_router/router.py:95-108` (`sanitize_slug`) -- reuse directly for `node_id` slugs; adapt `_dedupe_resolved_path` (`router.py:226-254`) for collisions.
- `backend/brain/settings_router/models.py:32-59` -- model-as-`output_format`-and-`response_model` precedent; `Field(description=...)` is prompt content.
- `backend/tests/brain/settings_router/conftest.py` -- `FakeAnthropicClient`/`make_fake_client`; copy into `tests/brain/meta_planner/conftest.py`, swap `DagBlueprint` in.
- `backend/tests/conftest.py` -- shared `client: TestClient` fixture for the new gateway endpoint test.
- `frontend/lib/settings-api.ts:59-70` -- `API_BASE_URL`/`readErrorMessage()`; reuse, don't redefine.
- `frontend/components/settings/ProposedChangeCard.tsx` -- closest "list of proposed items" precedent.
- `frontend/app/page.tsx` (`<main>` block) -- placeholder paragraph to replace.

## Tasks & Acceptance

**Execution:**
- [x] `backend/brain/meta_planner/__init__.py` -- new package
- [x] `backend/brain/meta_planner/models.py` -- `AgentSpec` (`node_id`, `parent_id: str | None`, `responsibility`, `depends_on: list[str]`), `DagBlueprint` (`intent`, `agents: list[AgentSpec]`) -- Node/context-graph fields deferred to Story 2.2
- [x] `backend/brain/meta_planner/decompose.py` -- `decompose_task(intent, project_root, client) -> DagBlueprint`; raises `MetaPlannerValidationError(ValueError)` on blank intent, `MetaPlannerLLMError(anthropic.AnthropicError)` on LLM failure/empty output
- [x] `backend/gateway/main.py` -- `POST /api/meta-planner/decompose` + handlers for the two new error types (400 `meta_planner.invalid_intent`, 502 `meta_planner.llm_error`)
- [x] `backend/tests/brain/meta_planner/{conftest.py,test_decompose.py,test_gateway_endpoints.py}` -- happy path (existing + new codebase), blank intent, LLM failure, duplicate-slug dedup
- [x] `frontend/lib/meta-planner-api.ts` -- `decomposeTask(intent): Promise<DagBlueprint>`, mirrored TS types, reuses `readErrorMessage`
- [x] `frontend/components/task-list/ProposedAgentList.tsx` -- dashed-border, no-shadow row per agent (planned state, no status badge): identity + responsibility
- [x] `frontend/app/page.tsx` -- replace the placeholder `<main>` paragraph with an intent textarea, submit control, loading/error state, `ProposedAgentList`

**Acceptance Criteria:**
- Given a submitted intent, when decomposition succeeds, then the response has exactly one agent with `parent_id: null` and zero or more subagents whose `parent_id` references it.
- Given the response, when rendered, then each agent appears as a task-list row (dashed border, no shadow, no status badge) with identity + one-line responsibility.
- Given an agent's `depends_on` entry, when the blueprint is returned, then that `node_id` exists elsewhere in the same `agents` list (no dangling reference).

## Design Notes

`DagBlueprint` is intentionally minimal here — `intent` + `agents` only. Story 2.2 is expected to extend `AgentSpec` with a `nodes: list[Node]` field (the unified Node model), not replace this shape:

```json
{"intent": "add OAuth2 login", "agents": [
  {"node_id": "main_orchestrator", "parent_id": null, "responsibility": "Coordinate auth rollout", "depends_on": []},
  {"node_id": "auth_scaffold_worker", "parent_id": "main_orchestrator", "responsibility": "Add OAuth2/JWT middleware", "depends_on": []}
]}
```

## Verification

**Commands:**
- `cd backend && uv run pytest tests/brain/meta_planner` -- all pass
- `cd frontend && npm run lint && npm run build` -- no errors

**Manual checks (if no CLI):**
- `scripts/dev.sh`; submit an intent on the home page; confirm a dashed-border agent list renders, no console errors.

## Suggested Review Order

**LLM call and structured-output contract**

- Entry point: the endpoint that wires a submitted intent to the Meta-Planner.
  [`main.py:196`](../../backend/gateway/main.py#L196)

- The LLM call itself — mirrors Settings Router's `client.messages.parse(output_format=...)` pattern exactly.
  [`decompose.py:150`](../../backend/brain/meta_planner/decompose.py#L150)

- The structured-output schema Claude fills in and the route returns.
  [`models.py:21`](../../backend/brain/meta_planner/models.py#L21)

**Single-root invariant (post-review fix)**

- A `parent_id` that doesn't resolve to any `node_id` in the response now raises instead of silently becoming a second root.
  [`decompose.py:212`](../../backend/brain/meta_planner/decompose.py#L212)

- Explicit post-resolution check: exactly one agent must have `parent_id=null`, or the response is rejected.
  [`decompose.py:227`](../../backend/brain/meta_planner/decompose.py#L227)

**Secret-file exclusion (post-review fix)**

- Filename patterns excluded from the project-root context sent to Claude.
  [`decompose.py:40`](../../backend/brain/meta_planner/decompose.py#L40)

- Where the exclusion is applied during the directory walk.
  [`decompose.py:114`](../../backend/brain/meta_planner/decompose.py#L114)

**UI binding**

- Intent submission, loading/error/result state machine.
  [`page.tsx:32`](../../frontend/app/page.tsx#L32)

- Accessible label added for the intent textarea (post-review fix).
  [`page.tsx:89`](../../frontend/app/page.tsx#L89)

- Proposed-agent list rendering, including the empty-state message (post-review fix).
  [`ProposedAgentList.tsx:17`](../../frontend/components/task-list/ProposedAgentList.tsx#L17)

**Peripherals**

- Frontend API client mirroring the backend wire contract.
  [`meta-planner-api.ts:12`](../../frontend/lib/meta-planner-api.ts#L12)

- Exception handlers mapping the two new error types to the app-wide envelope.
  [`main.py:144`](../../backend/gateway/main.py#L144)

- pytest import-mode fix required once a second `test_gateway_endpoints.py` existed.
  [`pyproject.toml:35`](../../backend/pyproject.toml#L35)
