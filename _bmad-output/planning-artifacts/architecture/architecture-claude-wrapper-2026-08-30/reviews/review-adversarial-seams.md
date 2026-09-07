---
name: 'Adversarial Seam Review — Claude Wrapper Architecture Spine'
type: review
target: _bmad-output/planning-artifacts/architecture/architecture-claude-wrapper-2026-08-30/ARCHITECTURE-SPINE.md
method: 'construct two spine-faithful builders per seam; report where they build incompatibly'
created: '2026-08-30'
verdict: 'FAIL — 11 findings; spine needs new/tightened ADs before two independent builders (human or agent) can be trusted to interoperate'
---

# Adversarial Seam Review — Claude Wrapper Architecture Spine

Mandate: construct two units one level down that each obey every AD to the letter yet still build incompatibly. Each finding below names two concrete, spine-legal implementations that clash when combined, and proposes the tightening that closes the hole.

## Finding 1 — AD-2 vs. Consistency Conventions: who actually writes the first `status` value?

AD-2 says execution fields are "pre-provisioned on every candidate node in the graph **at planning time**" — planning-time is the Meta-Planner's phase (`backend/brain/meta_planner/`). The Consistency Conventions table says "**Only the orchestrator** (AD-1) may transition a node's `status`." Nothing states whether the very first `status` write (e.g. `waiting_input`) counts as a "transition" owned by the orchestrator, or as "provisioning" owned by the planner.

- **Builder A** reads AD-2 literally: Meta-Planner constructs fully-populated `Node` objects (status included) and writes them straight into Redis via the checkpointer as part of emitting the DAG blueprint. The Brain→Engine handoff is "here is a graph that already exists in the store."
- **Builder B** reads the Conventions row literally: Meta-Planner emits only topology + dependency edges (its job per AD-3); the Engine is the sole writer of any `Node.status`, including the initial value, when it ingests the blueprint. The Brain→Engine handoff is "here is a topology; you instantiate it."

Combined: the Engine's ingestion code (built to Builder B's contract, expecting bare topology) receives Meta-Planner's output (built to Builder A's contract, expecting to write nothing) and either double-writes the initial checkpoint (race/duplicate) or errors on missing required fields the other side assumed it would supply. There is no pinned schema for the "DAG blueprint" object itself, so this isn't just a naming disagreement — it's two different node-creation code paths.

**Close with:** a tightened AD-2 (or new AD) that names the single writer of a node's *first* status value and states explicitly whether Meta-Planner may touch the checkpointer at all, plus a Pydantic contract for the DAG-blueprint handoff object.

## Finding 2 — AD-1/AD-3 handoff mechanism: push vs. poll for "A completed, release B"

AD-1 bans subagent-to-subagent coordination; AD-3 requires the Engine to know when A "completed" before releasing B. The *mechanism* for that signal is unpinned.

- **Builder A** implements it poll-based: worker A finishes, writes `status=completed` to Redis via the checkpointer, and the Engine's LangGraph conditional-edge logic polls/reads node statuses from Redis to decide when to dispatch B.
- **Builder B** implements it push-based: worker A's completion fires a callback/event onto an internal channel the orchestrator subscribes to; the orchestrator dispatches B on receipt of the event, independent of when (or whether) Redis has been durably updated yet.

Both are spine-legal ("routes through the orchestrator," no A→B contact). But if different subsystems in the same codebase pick different models (e.g. main DAG sequencing goes poll-based per Builder A, while HITL/undo interrupts in `engine/orchestrator/` go push-based per Builder B), you get two concurrency models sharing one Redis store: a worker can push an event before its checkpoint write lands, causing double-dispatch of B, or a poll loop can treat a not-yet-flushed write as authoritative and never see the completion at all.

**Close with:** an AD pinning the exact signal (e.g. "completion is signaled solely by a durable `status=completed` checkpoint write; the orchestrator's dispatch loop reacts only to checkpoint state changes, never to in-process events, and never dispatches before the write is confirmed").

## Finding 3 — Convention "only orchestrator transitions status" vs. AD-5 `trouble` self-report

The Conventions row bans a worker from writing "another node's state" — implying by omission a worker *may* write its own node's non-status state. But AD-5's `trouble` is a `status` value, and FR-17's push-or-cancel flow requires *someone* to flip status to `trouble` mid-execution, presumably triggered by the worker hitting the problem.

- **Builder A**: the worker, on error, writes `status=trouble` directly to its own node (reasoning: "own node" is exempt from the "never writes another node's state" ban; only cross-node writes are forbidden).
- **Builder B**: the worker never writes `status` at all (reasoning: "only the orchestrator may transition status" is unconditional); instead it raises/interrupts, and the orchestrator is the one that observes the interrupt and performs the actual `status=trouble` write.

These are different code paths with different failure semantics. If a downstream consumer (e.g. Post-Run Audit, which per the Capability Map is "governed by AD-2, Data/formats convention") assumes a single writer of record for status transitions (for its audit trail / "who changed what" log), Builder A's direct-write breaks that invariant outright. Worse, if the orchestrator (per Finding 2's poll-based path) is concurrently polling and also writes to the same node's status field around the same time a Builder-A worker self-writes `trouble`, you get a lost-update race on the same Redis key.

**Close with:** an explicit carve-out in AD-5 or the Conventions table: "a worker may never write `status` directly, even on its own node; it signals trouble via [named interrupt mechanism], and the orchestrator performs the actual transition" (or the inverse, if self-write is intended) — plus a stated rule that no two writers may target the same node's status concurrently.

## Finding 4 — AD-4: no pinned event schema between backend emitter and collector

AD-4 fixes telemetry as a separate service and says "analytics-only," but no event contract is pinned between `backend/telemetry/` (client) and `telemetry-collector/` (server) — two components explicitly called out in the Source Tree as having "own deploy lifecycle," i.e. likely built/versioned independently.

- **Builder A** emits raw internal shape: `{event_type, node_id, timestamp, payload: {...}}`, reusing (a subset of) the execution-node telemetry contract from PRD §10 directly — including possibly `live_stream.thinking` fragments if not explicitly excluded.
- **Builder B** emits an anonymized, aggregate analytics shape: `{event, ts, props: {...}}` (Segment/PostHog convention), deliberately stripped of node identifiers and free-text content since this is "opt-in" data leaving the machine.

Combined: the collector (built by whoever owns `telemetry-collector/`) will parse one shape and reject or silently mis-record the other. Worse, Builder A's approach creates an unaddressed privacy hazard — nothing in AD-4 states what fields are *forbidden* from leaving the machine (e.g. agent thinking text, file paths, repo contents), only that the service is "analytics-only."

**Close with:** a pinned event schema (even a minimal Pydantic model) shared by both `backend/telemetry/` and `telemetry-collector/`, plus an explicit allow-list of fields permitted to leave the local machine.

## Finding 5 — Redis checkpoint data model is underspecified at the invariant level

The Stack table says "Redis... required as a runtime dependency for checkpoint persistence," and the source tree names `engine/checkpoint/` as "Redis-backed checkpointer" — implying LangGraph's native checkpointer (e.g. `langgraph-checkpoint-redis`), which serializes entire graph state as opaque blobs keyed by `thread_id`/checkpoint id. But the Conventions table and Structural Seed also imply individual node fields (`status`, `telemetry`, `live_stream`) need to be independently readable for the WS/SSE live-update path (FR-13–15) and by the Gateway.

- **Builder A** uses LangGraph's native Redis checkpointer as-is: full graph state opaque-serialized per checkpoint; no component reads individual node fields directly from Redis without deserializing and replaying LangGraph's own format.
- **Builder B** stores Node records as individually addressable Redis structures (e.g. `node:{run_id}:{node_id}` hashes) so the Gateway can cheaply read/stream single-node status without touching LangGraph's checkpoint API at all.

These are incompatible data models. Builder B's approach bypasses LangGraph's replay/undo semantics — breaking FR-17 Undo, which needs actual checkpoint replay, not ad hoc key reads. Builder A's approach leaves the Gateway with no way to serve live per-node status over WS/SSE without reimplementing LangGraph's deserialization in the Gateway. If the Engine team builds A and the Gateway team builds B's assumed read path, the live-update feature has no data source.

**Close with:** an AD (or tightened AD-2) naming the exact Redis key/shape contract — e.g. "the LangGraph native checkpointer is the source of truth for replay/undo; node-level live fields are *additionally* mirrored to a flat, directly-addressable key on every write, and the Gateway reads only the mirror, never the checkpoint blob."

## Finding 6 — Is the node graph closed at planning time, or extensible at runtime?

AD-2 pre-provisions execution state on "every candidate node ... at planning time." Dynamic Tools (FR-23–25) can synthesize new MCP bridges at runtime. Nothing states whether a runtime-synthesized capability can ever manifest as a *new* graph node (with its own execution-state record) or whether the full node set must be enumerable by the Meta-Planner up front.

- **Builder A** treats the graph as closed after planning: the Engine has no node-creation code path at all, only status-transition paths; Dynamic Tools output is treated as a tool attached to an existing node, never a new node.
- **Builder B** treats the graph as extensible: when Dynamic Tools synthesizes something unplanned, the Engine inserts a new Node record at runtime with freshly-provisioned execution fields (contradicting AD-2's "at planning time, not allocated lazily" framing, but arguably necessary).

If the checkpoint schema/serialization is built assuming a fixed-size node table (Builder A), Builder B's runtime insertion either crashes validation or gets silently dropped, and the UI never reflects the new work.

**Close with:** an explicit statement of whether the node set is closed after planning (with dynamic-tool discoveries always attached to a pre-existing node) or whether AD-2's "pre-provisioned" language is compatible with a bounded/documented late-node-creation path.

## Finding 7 — Human-readable slug `node_id`s: no pinned uniqueness authority

Naming convention: `node_id`s are human-readable slugs (e.g. `auth_scaffold_worker`), "unique within a run, stable for the run's lifetime" — but no component is named as the enforcement authority, and slug generation from natural-language task decomposition is collision-prone (two similar subtasks both wanting `auth_scaffold_worker`).

- **Builder A**: Meta-Planner disambiguates at generation time (numeric suffix on internally-detected collision) and treats its output as pre-validated.
- **Builder B**: the Engine validates/deduplicates on blueprint ingestion, assuming Meta-Planner output is not to be trusted.

If both assume the *other* is the enforcement point, neither validates, and a collision silently reaches Redis — two nodes sharing one key, telemetry/undo/audit now ambiguous between them.

**Close with:** name the single collision-enforcement owner explicitly (likely the Engine, as the sole checkpoint writer per Finding 1's resolution).

## Finding 8 — `trouble` delivery channel: status event or error envelope?

The error envelope `{error_code, message, node_id: str | null}` and node telemetry share the same WS/SSE channel. AD-5's `trouble` is a `status` enum value, non-terminal/recoverable — but it's also plausibly "a problem," which is what the error envelope exists for.

- **Builder A** (backend): surfaces trouble as an error-envelope event (`error_code: "NODE_TROUBLE"`, `node_id` set); frontend's push-or-cancel modal watches the error channel.
- **Builder B** (backend): surfaces trouble purely as an ordinary node-status update (`status: "trouble"` in the telemetry stream), reasoning that non-terminal states aren't "errors."

If the frontend (built by a third party reading only the Conventions table) wires its push-or-cancel UI to one of these and the backend emits the other, FR-17's entire UI trigger never fires — a dead end for a named FR.

**Close with:** state explicitly which channel/shape carries a `trouble` transition (recommend: status event only, error envelope reserved for `failed`/terminal-adjacent conditions), or state both must be emitted together with which one is authoritative.

## Finding 9 — AD-6 process ownership vs. "no in-memory-only state" convention

AD-6 requires "a process is only ever accessed by the agent that spawned it" — this requires *some* ownership-tracking state. The Conventions table separately requires "no component holds in-memory-only state that survives a restart." OS process handles/PIDs are not meaningfully checkpointable (they don't survive restart, and PIDs get reused by the OS).

- **Builder A** keeps process→agent ownership purely in-memory in the Engine (fast, correct pre-restart, but silently violates the "no in-memory-only state" convention and loses all ownership info on crash/restart — an orphaned FastMCP process could then be logically "unowned").
- **Builder B** tries to honor the convention literally and persists PID + owner into Redis via the checkpointer; after a restart, this record is used to reassert ownership over "the same" PID — except the OS may have already reassigned that PID to an unrelated process, giving Builder B's Engine control-adjacent access to a process it never spawned, precisely what AD-6 forbids.

**Close with:** an explicit exception in the Conventions table for process-liveness state (in-memory only, by design, with a documented "on restart, treat all previously-spawned processes as dead and re-verify/re-spawn" rule) so neither builder is forced into an AD-6 violation.

## Finding 10 — AD-4 delivery semantics: synchronous-blocking vs. fire-and-forget

AD-4 says telemetry "never executes agent work," and the Structural Seed's dashed arrow suggests best-effort. But nothing pins whether emission is synchronous (with retry) or async/best-effort, and the emitter (`backend/telemetry/`) sits inside the same process as the Engine.

- **Builder A** implements a synchronous HTTP POST per event with retry/backoff (treats telemetry as "should eventually be reliable"), which can stall the Engine's dispatch loop if the opt-in collector is unreachable or slow — directly undermining AD-4's intent even though it doesn't literally violate the Rule text ("analytics-only, never executes agent work" says nothing about blocking).
- **Builder B** implements fire-and-forget with no retry, silently dropping events on any failure.

These produce different reliability guarantees for the same "opt-in events" promise, and Builder A's version can turn an optional, off-by-default feature into a latency/availability risk for core orchestration — a hole the current Rule text doesn't foreclose.

**Close with:** tighten AD-4's Rule to state emission is non-blocking/fire-and-forget with a bounded timeout and no retry that can stall the Engine.

## Finding 11 (spine-level) — No pinned wire contract for the Brain→Engine "DAG blueprint"

Underlying Findings 1, 6, and 7: the Structural Seed diagram shows `Brain -->|DAG blueprint| Engine` as a single arrow, but no Pydantic model or schema is named for that object anywhere in the spine (contrast with FR-1–3's `SettingAction`/`SettingsRouterOutput`, which *are* named). Every other cross-component boundary in the spine that matters (Settings Router, error envelope, telemetry contract) gets an explicit shape; this one — arguably the most load-bearing handoff in the whole system, since AD-1, AD-2, and AD-3 all depend on it — does not. That absence is what makes Findings 1, 6, and 7 possible at all: two builders each write valid Python that never actually compiles together at this seam.

**Close with:** name and pin a `DagBlueprint`/`NodeSpec` Pydantic contract in the spine itself, at the same level of specificity as `SettingsRouterOutput`.

---

## Summary Table

| # | AD(s) implicated | Nature of clash |
| --- | --- | --- |
| 1 | AD-2, Conventions | Two different owners of initial node-creation write |
| 2 | AD-1, AD-3 | Poll-based vs. push-based completion signaling |
| 3 | AD-5, Conventions | Worker self-writes status vs. orchestrator-only writes |
| 4 | AD-4 | No shared telemetry event schema; privacy leak risk |
| 5 | Stack (Redis), AD-2 | Opaque LangGraph blob vs. flat addressable keys |
| 6 | AD-2, FR-23–25 | Closed vs. extensible node graph at runtime |
| 7 | Conventions (naming) | No pinned slug-collision enforcement owner |
| 8 | AD-5, Conventions (errors) | `trouble` via status event vs. error envelope |
| 9 | AD-6, Conventions | Process ownership state vs. "no in-memory-only state" |
| 10 | AD-4 | Blocking vs. fire-and-forget telemetry emission |
| 11 | AD-1/2/3 (spine-level) | No pinned Brain→Engine blueprint wire contract |
