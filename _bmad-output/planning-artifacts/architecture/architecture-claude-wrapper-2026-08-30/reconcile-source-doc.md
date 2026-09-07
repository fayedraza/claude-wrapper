# Reconciliation: Source Architecture Doc vs. ARCHITECTURE-SPINE.md

**Source:** `docs/claude_wrapper_system_architecture_and_plan.md` (+ `docs/images/technical-architecture-diagram.png`, `docs/images/user-journey-flow.png`)
**Spine:** `_bmad-output/planning-artifacts/architecture/architecture-claude-wrapper-2026-08-30/ARCHITECTURE-SPINE.md`
**Date:** 2026-08-30

## Verdict

The spine faithfully preserves the source doc's structural shape and gives its two Pydantic
schemas real homes. **One genuine gap found**: FastMCP process termination-on-abort has no
explicit invariant. Everything else checked is either preserved, or a legitimate/labeled
refinement of something the source left open.

---

## 1. Three pillars + component diagram shape — PRESERVED

Confirmed against the rendered `technical-architecture-diagram.png`: Frontend → FastAPI Gateway
→ The Brain → The Engine → Dynamic Tools, with Engine ↔ SQLite/Redis, and the whole backend
reading/writing settings + deploying to the local environment.

The spine's Structural Seed mermaid diagram reproduces this exact chain: `GW --> Brain -->|DAG
blueprint| Engine`, `Engine <-->|checkpoint read/write| Redis`, `Engine -->|missing API
identified| Tools -->|mounts bridge| MCP`. The source tree mirrors it 1:1
(`backend/gateway/`, `backend/brain/{settings_router,meta_planner}/`,
`backend/engine/{orchestrator,workers,checkpoint}/`, `backend/dynamic_tools/`).

The spine goes further and splits Brain into `settings_router/` + `meta_planner/`, and Engine
into `orchestrator/` + `workers/` + `checkpoint/`. This is a legitimate refinement (the source
doc named these as sub-responsibilities in prose already, e.g. "Meta-Planner & Settings
Router"), not a restructuring that drops anything.

One note: the source diagram draws "Reads/writes settings," "Injects isolated context," and
"Deploys servers to" as arrows from the whole backend box collectively, not attributed to one
sub-component. The spine assigns "reads/writes settings" to Brain specifically and "mounts
bridge" to Tools specifically. That's a reasonable disambiguation of something the source left
imprecise, not a contradiction.

## 2. SQLite-or-Redis → Redis — DELIBERATE, STATED (not a gap)

The source doc leaves this as "SQLite or Redis" (Section 7 stack table). The spine resolves it
to Redis explicitly and repeatedly, not silently:
- Stack table: `redis-py 8.x`, `Redis — locally-run instance (server), required as a runtime
  dependency for checkpoint persistence — not a hosted/managed service`
- Structural Seed diagram: `Redis[(Redis<br/>checkpoint persistence)]`
- Source tree: `checkpoint/  # Redis-backed checkpointer`
- Deployment & Environments section: names Redis as part of the local v1 topology
- State & cross-cutting convention row: "All state mutation goes through LangGraph's
  checkpointer (Redis, ...)"

This is a resolved decision, stated in five separate places — correctly not flagged as a gap.

**Minor internal-consistency note (not a source-doc contradiction):** the State & cross-cutting
convention row reads "...checkpointer (Redis, AD below)" — there is no invariant below that name
this decision (AD-1 through AD-6 don't contain a Redis-selection rule); this appears to be a
dangling cross-reference within the spine itself, not a source-doc reconciliation issue. Worth a
copyedit pass, not counted in the gap total.

## 3. Pydantic schemas (SS6.1 node telemetry, SS6.2 SettingAction/SettingsRouterOutput) — GIVEN REAL HOMES

- `SettingAction` / `SettingsRouterOutput` (source §6.2): explicitly named in the source tree —
  `backend/brain/settings_router/  # FR-1-FR-3: SettingAction / SettingsRouterOutput (Pydantic)`.
  Not just gestured at — named by class name, in the exact directory.
- Node telemetry schema (source §6.1, the `config`/`telemetry`/`live_stream` unified node JSON):
  AD-2 ("Unified Node model") codifies this as an actual architectural rule (one entity, both
  context-graph and execution fields on the same record, pre-provisioned at planning time). It's
  homed in `backend/engine/workers/` and `backend/engine/checkpoint/`, and the frontend side is
  named field-by-field: `frontend/components/node-inspector/  # slide-over drawer:
  live_stream.thinking, config, telemetry`. This is a stronger treatment than the source gave it
  — the spine also resolves an ambiguity the PRD's adversarial review caught (context-node vs.
  execution-node split), which AD-2 exists specifically to prevent.

One evolution to flag as intentional, not silent: AD-5 adds `trouble` and `cancelled` to the
`status` enum, versus the source's 4-value enum (`waiting_input | executing | completed |
failed`). This is explicitly tagged `[ADOPTED from PRD §10/OQ-2]` — a traceable upstream
resolution, not an unstated deviation.

## 4. Phase 2 MCP Inspector workflow (`uv run mcp dev server.py` / `fastmcp dev server.py`) — ACCOUNTED FOR

The spine has no roadmap/phases section (reasonable — a spine documents structural invariants,
not delivery sequencing; the source's Phase 1-5 roadmap is a planning artifact, not an
architectural one). But the specific capability the question is about — where the MCP Inspector
debugging workflow plugs into the dynamic-tools component — does get an explicit line in the
source tree:

`backend/dynamic_tools/  # FR-23-25: FastMCP bridge synthesis + MCP Inspector hookup`

That's a real, if brief, acknowledgment that MCP Inspector wiring lives alongside bridge
synthesis in the same module. It doesn't specify a mechanism (e.g., a dev-only endpoint that
shells out to `fastmcp dev`), but the question only asked whether the spine accounts for
where/how this would be wired in "even briefly" — it does.

## 5. "Isolated agent access" language / AD-6 — NO NEW CONTRADICTION

Source doc (§6, Dynamic Tools pillar): FastMCP bridges are mounted "locally for isolated agent
access" — ambiguous prose that could read as OS-level sandboxing.

AD-6 resolves this explicitly and is tagged `[ADOPTED from PRD §9]`, meaning the ambiguity was
already disambiguated upstream in the PRD, and the spine is just carrying that resolution
forward: "'Isolated' means logically scoped to the requesting agent (a process is only ever
accessed by the agent that spawned it), not OS-sandboxed. The Permission Manager's approve/revoke
flow ... is the entire v1 trust boundary." This is consistent with AD-1 (orchestrator owns
dispatch) and with the source's Permission Manager feature description. No new contradiction
introduced at the architecture stage.

## 6. Gap found: FastMCP process termination-on-abort has no explicit invariant

The source doc states this behavior twice, as a specific, testable requirement:
- Features table (Human-in-the-Loop & Undo row): "...terminate spawned FastMCP processes, and
  roll back the node to its pre-interrupt state."
- User Flow step E: "Any ephemeral FastMCP tool processes spawned during the aborted step are
  gracefully terminated over stdio/SSE to prevent orphan processes."

The spine's capability map ties HITL/Undo (FR-16–FR-17) to `backend/engine/orchestrator/`,
`backend/engine/checkpoint/`, governed by AD-1, AD-5, AD-6 — but none of those invariants state
a rule about terminating FastMCP child processes when a HITL abort/rollback occurs. AD-6 covers
process *isolation* (who can access a spawned process), not process *lifecycle on abort*. AD-5
covers the `trouble`/terminal status enum, not process cleanup. The behavior is inferable from
directory layout (`dynamic_tools/` does bridge synthesis, `engine/orchestrator/` does HITL
interrupts) but isn't codified as an explicit rule anywhere, unlike every other cross-cutting
behavior in the source doc (which each got an AD or a convention-table row).

**Recommendation:** either fold a line into AD-1 or AD-6 ("on HITL abort/rollback, the
orchestrator terminates any FastMCP processes spawned by the interrupted node's subtree to
prevent orphans") or add it to the Consistency Conventions table under state/cross-cutting.

---

## Summary

- **Gaps: 1** (FastMCP process termination on HITL abort — no explicit invariant, only
  inferable from directory structure).
- **Confirmed preserved, not restructured:** three-pillar component shape and diagram flow.
- **Confirmed deliberate, not silent:** SQLite-or-Redis resolved to Redis, stated in 5 places.
- **Confirmed real homes, not gestures:** both Pydantic schemas (SettingAction/
  SettingsRouterOutput and the unified node schema via AD-2) land in named directories/files.
- **Confirmed accounted for:** MCP Inspector hookup gets an explicit source-tree line.
- **Confirmed no new contradiction:** AD-6's "isolated agent access" reading matches the PRD's
  upstream resolution.
- **Minor, non-blocking:** a dangling "(Redis, AD below)" cross-reference in the spine's own
  Consistency Conventions table — a copyedit issue, not a source-doc reconciliation issue.
