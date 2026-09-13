---
title: 'Story 2.3: Review flight path and cost estimate'
type: 'feature'
created: '2026-09-13'
status: 'done'
review_loop_iteration: 0
context: []
baseline_commit: '439d224353a0eaca648fbd62b7bae7406a4a6e7f'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Story 2.2's context graph shows every candidate topic an agent could draw from, but not which ones it actually needs, in what order, or at what cost — a developer still can't judge efficiency before approving anything.

**Approach:** The same `decompose_task()` call also has the LLM mark each `Node.required: bool` (essential vs. supplementary, per agent). A new pure-Python pass (`flight_path.py`, no second LLM call, per AD-7) then selects the flight path — exactly the required nodes, ordered via a local neighbor traversal — and computes a deterministic token/duration estimate per agent and in aggregate. Rendered by extending Story 2.2's card UI: a numbered badge per path node, plus cost/duration lines.

## Boundaries & Constraints

**Always:** `required` is LLM-proposed (semantic judgment), used as-is. `flight_path`/`estimated_tokens`/`estimated_duration_seconds` (per agent) and `aggregate_estimated_*` (top-level) are always server-computed in `flight_path.py`, never trusted from the LLM even though they exist in the same `output_format` schema (mirrors `node_id`'s "hint, always overwritten" precedent). Flight path = exactly the `required=true` nodes, ordered by a DFS over their own `neighbors` (AD-7: local relations only, no global lookahead). Token cost per node: real file size (`chars/4`) for a `codebase_file` node whose `source_ref` resolves to a real file under `project_root`; a flat constant otherwise. Duration = tokens / a throughput constant + a per-round-trip constant per required `mcp` node. Budget is informational only — the path always covers every required node regardless of cost.

**Ask First:** None — still a preview; nothing executes or persists.

**Never:** No React Flow/drawn route lines (extend the existing card UI instead — human decision this session). No dropping required nodes to fit a budget. No second LLM call for routing or cost.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Mixed required/optional nodes | Agent has some `required=true`, some `required=false` nodes | `flight_path` lists only the required `node_id`s, ordered via neighbor traversal; `estimated_tokens` sums only those | N/A |
| Required codebase_file node, real file | `source_ref` resolves to a real file under `project_root` | Token cost = that file's real size / 4 | N/A |
| Required codebase_file node, missing/hallucinated path | `source_ref` doesn't resolve to a real file | Falls back to the flat default cost, no error | N/A |
| No required nodes | Every node on an agent has `required=false` (or `nodes` is empty) | `flight_path` is `[]`, `estimated_tokens`/`estimated_duration_seconds` are `0` | N/A |

</frozen-after-approval>

## Code Map

- `backend/brain/meta_planner/models.py:41` (`Node.node_id`) — add `required: bool` alongside it.
- `backend/brain/meta_planner/models.py:92-134` (`AgentSpec`) — add `flight_path: list[str] = []`, `estimated_tokens: int = 0`, `estimated_duration_seconds: float = 0.0`.
- `backend/brain/meta_planner/models.py:135` (`DagBlueprint`) — add `aggregate_estimated_tokens: int = 0`, `aggregate_estimated_duration_seconds: float = 0.0`.
- `backend/brain/meta_planner/decompose.py:176-226` (`_resolve_agent_nodes`) — `model_copy(update=...)` style to mirror in the new module.
- `backend/brain/meta_planner/decompose.py:228` (`decompose_task`) — call the new pass per agent after `_resolve_agent_nodes`; set aggregate fields before the final `model_copy`.
- `frontend/lib/meta-planner-api.ts` — mirror the new fields.
- `frontend/components/task-list/AgentContextGraph.tsx` — numbered badge per `flight_path` node.
- `frontend/components/task-list/ProposedAgentList.tsx` — per-agent cost/duration line + one aggregate line above the list.

## Tasks & Acceptance

**Execution:**
- [x] `backend/brain/meta_planner/models.py` — add `Node.required: bool`; add `AgentSpec.flight_path`/`estimated_tokens`/`estimated_duration_seconds`; add `DagBlueprint.aggregate_estimated_*`
- [x] `backend/brain/meta_planner/flight_path.py` (new) — `select_flight_path(agent, project_root) -> AgentSpec`: filters to `required` nodes, orders via DFS over `neighbors`, computes per-node cost (real file size or flat constant) and duration (throughput + mcp round-trip constant), returns the agent with those three fields set
- [x] `backend/brain/meta_planner/decompose.py` — extend `SYSTEM_PROMPT` for `required` (and note the computed fields are ignored); call `select_flight_path` per agent in `decompose_task`; set the two aggregate fields
- [x] `backend/tests/brain/meta_planner/test_flight_path.py` (new) — cover all 4 I/O matrix rows
- [x] `backend/tests/brain/meta_planner/test_decompose.py`/`test_gateway_endpoints.py` — cover aggregate sum correctness end-to-end
- [x] `frontend/lib/meta-planner-api.ts` — mirror new fields
- [x] `frontend/components/task-list/AgentContextGraph.tsx` — numbered badge per flight-path node
- [x] `frontend/components/task-list/ProposedAgentList.tsx` — per-agent cost/duration line; one aggregate line above the list

**Acceptance Criteria:**
- Given an agent's context graph, when the flight path is computed, then it covers every `required` node and no others, ordered via that agent's own neighbor relations.
- Given a computed flight path, when rendered, then each path node shows its position and the agent shows its token/duration estimate, visible without needing to expand its card.
- Given all agents' estimates, when the list renders, then one aggregate token/duration total is shown, equal to the sum of every agent's own estimate.

## Design Notes

No separate "budget" number is introduced: since only required nodes are ever included and optional nodes are never added (they can only increase cost, never reduce it under a pure token-minimization objective), the computed estimate *is* the budget — there's nothing left to enforce or reconcile.

## Verification

**Commands:**
- `cd backend && uv run pytest tests/brain/meta_planner` — all pass
- `cd frontend && npm run lint && npm run build` — no errors

**Manual checks (if no CLI):**
- `scripts/dev.sh`; decompose a task; confirm each agent shows a cost/duration line and an aggregate total, and expanding a card shows numbered badges on its flight-path nodes.

## Suggested Review Order

**Node model and LLM contract**

- `Node.required` — mandatory (no default), the one LLM-judged field in this story.
  [`models.py:77`](../../backend/brain/meta_planner/models.py#L77)

- `AgentSpec.flight_path`/`estimated_tokens`/`estimated_duration_seconds` and `DagBlueprint.aggregate_estimated_*` — all server-computed, round-trip harmlessly through the same schema.
  [`models.py:145`](../../backend/brain/meta_planner/models.py#L145)

**Flight path selection and cost estimate (the new algorithm)**

- Entry point: `select_flight_path`, called per agent after node resolution.
  [`flight_path.py:146`](../../backend/brain/meta_planner/flight_path.py#L146)

- Iterative DFS ordering over required nodes' local neighbor edges (post-review fix: no recursion).
  [`flight_path.py:111`](../../backend/brain/meta_planner/flight_path.py#L111)

- Per-node cost: real file size with a size cap and ceiling division (post-review fixes), flat constant otherwise.
  [`flight_path.py:84`](../../backend/brain/meta_planner/flight_path.py#L84)

- Path-traversal guard on `source_ref`, broadened to catch symlink loops/null bytes (post-review fix).
  [`flight_path.py:54`](../../backend/brain/meta_planner/flight_path.py#L54)

- Where it's wired into `decompose_task`, plus the aggregate sum.
  [`decompose.py:332`](../../backend/brain/meta_planner/decompose.py#L332)

**UI binding**

- Per-agent and aggregate cost/duration lines, with defensive fallbacks (post-review fix).
  [`ProposedAgentList.tsx:118`](../../frontend/components/task-list/ProposedAgentList.tsx#L118)

- Numbered flight-path badge per node.
  [`AgentContextGraph.tsx:46`](../../frontend/components/task-list/AgentContextGraph.tsx#L46)
