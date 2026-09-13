# Epic 2 Context: Plan a Task

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

After a developer submits a plain-language intent, the Meta-Planner decomposes it into a concrete set of agents, builds a per-agent context graph, selects a token-efficient route through that graph (the "flight path"), and predicts token/time cost — all before anything executes and before any file/MCP access is gated. This is the product's core differentiator: it replaces an opaque terminal hand-off with a visible, inspectable plan the developer can judge for correctness and efficiency before committing to a run. Epic 2 is the critical-path epic — every downstream epic (Approve & Run, Dynamic Tool Synthesis, Post-Run Audit) depends entirely on the DAG blueprint, context graphs, and flight paths it produces, so correctness here matters more than in any other epic.

## Stories

- Story 2.1: Decompose a task into agents
- Story 2.2: View each agent's context graph
- Story 2.3: Review flight path and cost estimate

## Requirements & Constraints

- Task decomposition must determine agent/subagent count and each one's specific, non-overlapping responsibility, and emit a structured DAG blueprint before any execution begins.
- A context graph must be built for the main orchestrator and every subagent: subtopic nodes drawn from MCP servers, local docs, existing Claude context, and (existing-repo runs only) the codebase's own files, connected by topical closeness. New-repo runs have no codebase nodes. Each node must show which source it came from.
- Flight path selection must choose, per agent, a route through its context graph that (a) covers the context required for its task — a hard constraint, (b) stays within the agent's predicted token budget — a hard constraint, and (c) is the most token-efficient route available subject to (a) and (b).
- Token/time cost must be predicted per agent and in aggregate, based on system prompt length, assigned workspace files, and anticipated tool round-trips, and displayed before execution starts. This estimate is the fixed baseline the Post-Run Audit (Epic 5) later compares actuals against — it intentionally does not account for push-loop iterations or cancelled work, a known source of estimate error.
- Planning latency (context graph construction + flight path selection) must complete within a low-single-digit-second ceiling for a typical-size repo/task, owned by the Meta-Planner — this epic's one directly-owned NFR (NFR-4).
- Out of scope for this epic: Pre-Flight approval/gating of the files and MCP servers surfaced here (moved to Epic 3, since approval now leads directly into execution kickoff), and anything execution-related (nothing actually runs yet).

## Technical Decisions

- Everything in this epic lives in `backend/brain/meta_planner/` and is emitted as a single pinned `DagBlueprint` Pydantic model — the sole handoff object to the Engine (Epic 3). The Meta-Planner never writes to the checkpoint store; it only returns this blueprint. `node_id` slug uniqueness is validated by the Engine at ingestion, not assumed here.
- Dependency edges between subagents are explicit and declared by the Meta-Planner at planning time (not inferred later from runtime behavior), applying uniformly whether the repo is new or existing.
- Node model: a single unified `Node` entity (no separate context-node/execution-node schema). Every node the Meta-Planner produces carries both context fields (topic, source reference, neighbor relations) — populated now — and execution fields (`status`, `telemetry`, `live_stream`, checkpoint reference) — left empty, to be written later exclusively by the Engine. The node graph is closed after planning: this epic's output is the complete, final set of nodes for the run; nothing (including later dynamic-tool synthesis) creates a new node at runtime.
- Flight-path selection is a constrained local search over each node's local neighbor relations only (no global lookahead required): hard coverage constraint, hard token-budget constraint, then optimize for token efficiency.
- Naming conventions: `snake_case` Python identifiers/JSON fields, `PascalCase` Pydantic models, human-readable `node_id` slugs (never opaque UUIDs, e.g. `auth_scaffold_worker`), ISO 8601 UTC timestamps.
- Stack pins relevant to this epic's backend work: FastAPI 0.141.x (`starlette>=1.0.1`), LangGraph 1.2.x, Pydantic 2.13.x — decomposition/graph/flight-path/estimate logic itself is plain Python/Pydantic within `meta_planner/`, no LangGraph execution happens in this epic.

## UX & Interaction Patterns

- Information architecture position: Intent Submission -> Task List (planned) -> [this epic's output feeds] Pre-Flight Permission checklist (Epic 3). This epic covers everything between submitting an intent and reaching that checklist.
- Task List (planned state): each agent renders as a task-list row — agent name (plain system font, never monospace) plus a one-line responsibility summary. Planned-state rows render dashed-border, no-shadow (visually distinct from live rows, which are solid with a status-tinted rail) since nothing has started yet and no status badge is yet meaningful.
- Context graph and flight path are rendered visually (DAG Canvas visual family) before execution starts: each node shows its source; the selected flight path is overlaid on the graph. Per-agent and aggregate token/duration estimates are shown alongside.
- The DAG Canvas's agent-to-agent connector lines represent dependency/dispatch order only — they are a distinct concept from the context-node-level flight path shown within a single agent's graph. Do not conflate the two when rendering this epic's views.
- Voice/tone: plain, factual copy (e.g. "This starts planning only — nothing executes yet."), no hype or marketing language, no exclamation points.
- Global styling constraints (color theme, shape/elevation, accessibility floor, motion) apply here as everywhere but are not epic-specific; see the shared design tokens if implementing visual components.

## Cross-Story Dependencies

- Story 2.2 depends on Story 2.1's agent list existing first (a context graph is built per already-decomposed agent).
- Story 2.3 depends on Story 2.2's context graph existing first (flight path is a route through that graph).
- Epic 2's output (DAG blueprint, context graphs, flight paths, cost estimates) is a hard prerequisite for all of Epic 3 (Pre-Flight checklist and execution), Epic 4 (dynamic tool synthesis happens during this epic's planning phase), and Epic 5 (Post-Run Audit compares against this epic's estimates and replays this epic's flight paths).
