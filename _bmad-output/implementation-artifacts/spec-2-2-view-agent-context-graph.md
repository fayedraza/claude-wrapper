---
title: 'Story 2.2: View each agent'\''s context graph'
type: 'feature'
created: '2026-09-13'
status: 'done'
review_loop_iteration: 0
context: []
baseline_commit: '515827bfc85aa8f916d10c6140741326217d33b2'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** After Story 2.1's agent list, a developer still can't tell what sources/topics each agent will actually draw from before it runs.

**Approach:** Extend the existing `decompose_task()` Claude call (one call, not one per agent) so each `AgentSpec` also carries a `nodes: list[Node]` context graph — subtopic nodes tagged with their source and connected to topically-related neighbors within that same agent. Render each agent's graph as an expandable list of cards (no new graph-rendering library — no UX mock exists for this screen yet; a real drawn graph is deferred).

## Boundaries & Constraints

**Always:** `Node` lives in `backend/brain/meta_planner/models.py`, added as `AgentSpec.nodes: list[Node]` — extends Story 2.1's shape, never replaces it. Context-graph generation folds into the same single `client.messages.parse(output_format=DagBlueprint)` call (per AD-8: one blueprint carries "the full Node set per agent") — not a second LLM call. Every agent, including the main orchestrator, gets a `nodes` list. `source` is exactly one of `mcp`, `local_docs`, `codebase_file`, `claude_context`; `codebase_file` only when the project snapshot has real source files; `mcp` is LLM-proposed only (no real MCP registry exists yet). Each agent's `node_id`s/`neighbors` are sanitized/deduped/remapped in their own per-agent namespace, mirroring Story 2.1's `sanitize_slug`/dedup/remap pattern.

**Ask First:** None — still a preview; nothing executes or persists.

**Never:** No flight path or cost estimate (Story 2.3). No real MCP discovery/connection. No `@xyflow/react` or drawn graph lines — v1 renders nodes as cards with neighbor tags (human decision this session, given no UX mock exists for this screen).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Existing codebase | Project root has real source files | Every agent's `nodes` is non-empty; at least one node has `source: codebase_file` with a real path as `source_ref` | N/A |
| New/empty codebase | No source files under project root | No node has `source: codebase_file`; other sources still allowed | N/A |
| Dangling neighbor reference | A node's `neighbors` entry doesn't match any `node_id` in that agent's own `nodes` | Entry dropped silently, not passed through raw | N/A |
| Duplicate node_id hints within one agent | Two nodes on the same agent sanitize to the same slug | Deduped (`-2`, `-3` suffixing); neighbor references remapped to the deduped slug | N/A |

</frozen-after-approval>

## Code Map

- `backend/brain/meta_planner/models.py:1-58` — `AgentSpec`/`DagBlueprint` (Story 2.1); add `Node` here, `nodes: list[Node] = []` on `AgentSpec`. Keep execution fields `Optional`, unset (AD-2: pre-provisioned, empty until the Engine writes them).
- `backend/brain/meta_planner/decompose.py:150-231` — two-pass sanitize/dedup/remap logic (`_dedupe_slug`, `sanitize_slug`, the `parent_id`/`depends_on` remap loop). Extend the same pattern per-agent for `Node.node_id`/`neighbors` — no second LLM call, no new exception type.
- `backend/brain/meta_planner/decompose.py:57-90` (SYSTEM_PROMPT) — extend with the four source types + rules above.
- `backend/tests/brain/meta_planner/conftest.py` — extend fixtures with `Node`-bearing `DagBlueprint` outputs.
- `frontend/lib/meta-planner-api.ts:12-25` — mirrors the Python models; add `Node`, `nodes: Node[]`.
- `frontend/components/task-list/ProposedAgentList.tsx:17-41` — static card per agent, no click target; add expand/collapse.

## Tasks & Acceptance

**Execution:**
- [x] `backend/brain/meta_planner/models.py` — add `Node` (`node_id`, `topic`, `source: Literal["mcp","local_docs","codebase_file","claude_context"]`, `source_ref`, `neighbors: list[str] = []`, plus unset `status`/`telemetry`/`live_stream`/`checkpoint_ref`); add `AgentSpec.nodes: list[Node] = []`
- [x] `backend/brain/meta_planner/decompose.py` — extend `SYSTEM_PROMPT` per Boundaries; extend the sanitize/dedup/remap pass to run per-agent over each agent's `nodes` (own namespace), dropping dangling `neighbors` entries
- [x] `backend/tests/brain/meta_planner/{test_decompose.py,test_gateway_endpoints.py}` — cover all 4 I/O matrix rows
- [x] `frontend/lib/meta-planner-api.ts` — add `Node` interface, extend `AgentSpec`
- [x] `frontend/components/task-list/ProposedAgentList.tsx` — clicking an agent card toggles inline expansion
- [x] `frontend/components/task-list/AgentContextGraph.tsx` (new) — one card per node: topic, a plain-text source label (e.g. "Codebase file: `path`"), neighbor topics as small tags

**Acceptance Criteria:**
- Given a decomposed task, when I view an agent, then I see its context graph of subtopic nodes, each showing which source it came from.
- Given two nodes on the same agent, when one lists the other as a neighbor, then that neighbor resolves to a real node on the same agent (no dangling reference reaches the response).
- Given a new/empty codebase, when agents are decomposed, then no node cites `source: codebase_file`.

## Design Notes

Per-agent node namespace, not global: `Node.node_id` only needs to be unique within its own agent's `nodes` list — AD-2 scopes "a node's own knowledge... to its own context content and its graph neighbors," never global run state, so cross-agent collisions are fine and expected (e.g. two agents can each have a node named `auth_docs`).

## Verification

**Commands:**
- `cd backend && uv run pytest tests/brain/meta_planner` — all pass
- `cd frontend && npm run lint && npm run build` — no errors

**Manual checks (if no CLI):**
- `scripts/dev.sh`; decompose a task; expand an agent card; confirm its context-graph nodes render with source labels.

## Suggested Review Order

**Node model and LLM contract**

- Entry point: the `Node` schema Claude fills in, including the `codebase_file` → non-empty `source_ref` validator (post-review fix).
  [`models.py:30`](../../backend/brain/meta_planner/models.py#L30)

- `AgentSpec.nodes` — the extension point Story 2.1 deliberately left.
  [`models.py:123`](../../backend/brain/meta_planner/models.py#L123)

- SYSTEM_PROMPT rules for the four source types and per-agent node_id/neighbor conventions.
  [`decompose.py:82`](../../backend/brain/meta_planner/decompose.py#L82)

**Per-agent sanitize/dedup/remap (post-review fixes)**

- `_resolve_agent_nodes`: first-occurrence-wins for duplicate raw node_ids, self-reference/duplicate-neighbor filtering, and forcing Engine-owned fields to `None`.
  [`decompose.py:176`](../../backend/brain/meta_planner/decompose.py#L176)

- Where it's wired into the existing per-agent loop.
  [`decompose.py:228`](../../backend/brain/meta_planner/decompose.py#L228)

**UI binding**

- Expand/collapse toggle, `aria-controls`, and the reset-on-new-result logic (post-review fix).
  [`ProposedAgentList.tsx:33`](../../frontend/components/task-list/ProposedAgentList.tsx#L33)

- Node rendering: source label fallback and nullish-nodes guard (post-review fixes).
  [`AgentContextGraph.tsx:37`](../../frontend/components/task-list/AgentContextGraph.tsx#L37)

**Peripherals**

- `ContextGraphNode` TS interface (renamed from `Node` to avoid shadowing the DOM global, post-review fix).
  [`meta-planner-api.ts:20`](../../frontend/lib/meta-planner-api.ts#L20)
