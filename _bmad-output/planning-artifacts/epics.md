---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - _bmad-output/planning-artifacts/prds/prd-claude-wrapper-2026-08-30/prd.md
  - _bmad-output/planning-artifacts/architecture/architecture-claude-wrapper-2026-08-30/ARCHITECTURE-SPINE.md
  - _bmad-output/planning-artifacts/ux-designs/ux-claude-wrapper-2026-08-30/DESIGN.md
  - _bmad-output/planning-artifacts/ux-designs/ux-claude-wrapper-2026-08-30/EXPERIENCE.md
---

# Claude Wrapper - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for Claude Wrapper, decomposing the requirements from the PRD, Architecture spine, and UX design contract (DESIGN.md + EXPERIENCE.md) into implementable stories.

## Requirements Inventory

### Functional Requirements

FR-1: Natural-language settings update — user submits a natural-language configuration request; Settings Router classifies it into one of 8 `.claude/` target categories and produces a file_path/content/action.
FR-2: Settings change approval gate — no `.claude/` file is written until the user approves the proposed change's summary.
FR-3: Settings transparency on demand — user can view a full, current summary of everything configured in `.claude/` at any time.
FR-4: Pre-Flight Permission checklist — itemized per-agent checklist of files/MCP servers; each item approved/rejected individually (checkbox-style); a rejected item's agent proceeds without that resource, no re-planning, no block.
FR-5: Mid-run permission revoke with immediate cutoff — revoking a shared grant cuts off every agent currently using it immediately, not just one grant instance.
FR-6: Permission grant addition outside Pre-Flight — new grants available immediately without re-approving prior items.
FR-7: Task decomposition — Meta-Planner determines how many agents/subagents are needed and each one's responsibility, producing a structured DAG blueprint before execution.
FR-8: Per-agent context graph construction — a context graph (subtopic nodes, topical-closeness edges) built for the main orchestrator and every subagent; existing-repo runs include codebase files as nodes.
FR-9: Flight path selection — a route through an agent's context graph is selected, covering required context within token budget at the most efficient available route.
FR-10: Token/time cost prediction — per-agent and aggregate token/duration estimates, displayed before execution, baseline for the Post-Run Audit.
FR-11: Control-tower sequencing — the main orchestrator sequences subagent execution via explicit declared dependencies; applies uniformly to new and existing repos.
FR-12: Task list & summaries display — live list of main/subagent tasks, each with a DAG-graph button, stop/HITL control, and a conditional question button.
FR-13: Live DAG rendering — DAG graph showing context gained, files used, and MCP servers (FastMCP-generated vs. pre-provided).
FR-14: Real-time flight path tracking — flight path updates live, context node by context node.
FR-15: Real-time token/time telemetry — expected vs. actual metrics per agent and overall, updating live.
FR-16: Stop & Undo — immediately abort an in-flight agent's stream, terminate spawned processes, roll back to pre-interrupt checkpoint; discarded tokens tracked separately (see FR-22).
FR-17: Trouble notification with push-or-cancel — user notified when an agent hits trouble mid-execution, can push (redirect) or cancel (terminal).
FR-18: In-UI question response and live reasoning visibility — user answers a blocking question in free text in the UI; can also watch an agent's live reasoning trace independent of any open question.
FR-19: Expected vs. actual metrics summary — post-run comparison of time/tokens per agent and overall.
FR-20: Flight path replay — post-run view of the actual route taken, token usage highlighted per context node and per agent.
FR-21: Generated files changelog — post-run changelog of files created/modified/deleted, attributed to contributing agent(s).
FR-22: Cancelled tokens tracking — tokens from discarded/cancelled work tracked as their own Post-Run Audit line item, never folded into completed-work totals.
FR-23: On-the-fly MCP bridge synthesis — system identifies a missing external API capability during planning and generates a compliant MCP bridge for it.
FR-24: Pre-Flight approval for synthesized bridges — a synthesized bridge goes through the same Pre-Flight checklist as a pre-provided MCP server before use.
FR-25: Generated tool debugging (MCP Inspector) — user can test/debug a synthesized bridge before it executes against a real agent.
FR-26: Opt-in telemetry collection — user opts in (via Settings) to sharing anonymized run/outcome/delta telemetry that feeds the Success Metrics; off by default, allow-listed fields only.

### NonFunctional Requirements

NFR-1: Streaming latency — agent status, token telemetry, and flight-path updates reach the UI over WebSocket/SSE with a sub-second perceived delay.
NFR-2: Checkpoint durability — LangGraph checkpoints survive a backend crash/restart without corrupting or losing rollback ability (Redis AOF, `appendfsync everysec`; sub-second data-loss window accepted as residual risk).
NFR-3: Process cleanup guarantee — every spawned FastMCP process is terminated when its agent is cancelled, pushed past, the run ends, or the backend crashes and restarts (no orphaned processes; process-liveness is re-verified and re-spawned from the last checkpoint on restart, never reasserted against a stale PID).
NFR-4: Planning latency — context graph construction and flight path selection complete within a low-single-digit-second ceiling for a typical-size repo/task, owned by the Meta-Planner.
NFR-5: Cost visibility, not enforcement — v1 provides no hard token/dollar cap or warn-before-exceed threshold; live telemetry (FR-15) and Stop & Undo (FR-16) are the only guardrail.
NFR-6: Security boundary — the Permission Manager's approve/revoke flow (FR-4/5/6) is the entire v1 trust boundary; spawned processes (including synthesized bridges) get no additional OS-level sandboxing.

### Additional Requirements

- **No starter template specified.** Greenfield project; Epic 1 Story 1 should initialize a standard Next.js 16 frontend + Python/FastAPI backend project structure per the Architecture spine's Source Tree, rather than adopting an existing scaffold.
- **Design paradigm:** orchestrator-worker (supervisor) — one main orchestrator agent owns DAG dispatch/sequencing; every subagent is an independently checkpointed worker with no peer-to-peer coordination (AD-1).
- **Node data model:** unified `Node` entity (no context-node/execution-node schema split); every node in an agent's context graph carries both context fields and execution/telemetry fields, pre-provisioned at planning time; per-agent "execution node" is a computed rollup, never separately stored (AD-2).
- **Brain→Engine contract:** a pinned `DagBlueprint` Pydantic model is the sole handoff object between planning and execution; the Meta-Planner never writes to the checkpoint store; the Engine is the sole writer of any node's `status`; the node graph is closed after planning (no runtime node creation, including by Dynamic Tools) (AD-8).
- **Flight-path algorithm:** a constrained local search over an agent's context graph — hard coverage constraint, hard token-budget constraint, token-efficiency objective, operating over each node's local neighbor relations only (AD-7).
- **Node status enum:** `waiting_input | executing | trouble | completed | cancelled | failed`; only the Engine writes `status`; a worker signals trouble via interrupt, never a direct write; `trouble` is delivered as a status event, not the error envelope (AD-5).
- **Telemetry contract:** a single pinned `TelemetryEvent` Pydantic model shared by the backend emitter and the separate telemetry-collector service, with an explicit field allow-list (no `live_stream.thinking`, file contents, or prompts); emission is fire-and-forget, non-blocking, bounded timeout, no retry that can stall the Engine (AD-4).
- **Checkpoint data model:** LangGraph's native Redis checkpointer is the sole source of truth for replay/undo; node-level live fields are additionally mirrored to flat, directly-addressable Redis keys for Gateway reads; the Gateway never reads the checkpoint blob directly (AD-9).
- **Redis is a required local runtime dependency** (not SQLite) — a deliberate architecture-stage choice for v2 multi-user pub/sub headroom, run locally via Docker Compose or local install; still within v1/v2's fully-local deployment envelope.
- **Telemetry collector is a separate, self-hosted, minimal service** — never bundled into the local orchestration backend, never a third-party analytics provider; the one exception to "fully local" in the deployment envelope, and opt-in/off-by-default.
- **Naming/data conventions:** `snake_case` Python identifiers and JSON fields; `PascalCase` Pydantic models and TS types; human-readable `node_id` slugs (never opaque UUIDs), uniqueness enforced by the Engine; ISO 8601 UTC timestamps everywhere; a single error envelope shape (`error_code`, `message`, `node_id`) shared with the telemetry channel.
- **Stack pins (verified current 2026-08-30):** Next.js 16.3.x, @xyflow/react 12.11.x, FastAPI 0.141.x (pin `starlette>=1.0.1` for CVE-2026-48710), LangGraph (Python) 1.2.x, FastMCP (Python) 3.4.x (pin `>=3.4.5`), Pydantic 2.13.x, redis-py 8.x (RESP3 default), Redis 8.x (local instance).
- **FR-26 (opt-in telemetry) deferred to v2** — decided during Epic 1 story-writing, 2026-09-07: not worth building/shipping in v1. No story for it anywhere in this document. The PRD's Success Metrics (SM-1..5) will rely on local, single-user Post-Run Audit data only for v1; the aggregate/cross-user validation those metrics were designed for won't be possible until FR-26 ships in v2. The PRD itself (`prd.md`) still lists FR-26 as v1-scoped and has not been updated to reflect this — flag for reconciliation if/when the PRD is revisited.

### UX Design Requirements

UX-DR1: Implement the "Flight Tracker" color theme (warm, optimistic) with a full light/dark token set — bg, surface, accent, text1/text2, and 6 node-status colors (`waiting_input`/`executing`/`trouble`/`completed`/`cancelled`/`failed`) — as real, switchable modes, not a single fixed palette.
UX-DR2: System font stack for all UI text, including agent/node names (never rendered as code); monospace reserved strictly for literal file paths, `.env`/config filenames, and raw values — never for prose, labels, or names.
UX-DR3: Rounded shape system (8/16/20px radii on panels/cards, fully-rounded 999px pill chips/badges) and soft-shadow elevation tokens (`0 2px 8px rgba(0,0,0,.05)` for cards/nodes, `0 6px 24px rgba(45,156,219,.10)` for larger panels/drawers/overlays), applied consistently across all surfaces.
UX-DR4: Standard web accessibility floor (WCAG AA-ish contrast, full keyboard navigation, visible `:focus-visible` states) on every interactive element — no formal compliance audit required for v1.
UX-DR5: Purposeful, understated motion on node status changes and flight-path advancement — alive and responsive, never flashy. Specific timing/easing values are an open item (not locked this session); do not invent precise values without confirming.
UX-DR6: Information architecture — a primary linear spine (Intent Submission → Task List [planned] → Pre-Flight Permission checklist → [Task List (live) ⇄ DAG Canvas, peer views of the same live run] → Post-Run Audit → Full Flight Path Replay as a drill-down), two interrupt overlays hanging off the live step (Node Inspector for `trouble`, Question-Response for `waiting_input`, both returning to wherever the user was on close), and two persistent global entry points reachable from any state (Settings, Permission Manager's mid-run revoke) — these two are NOT steps in the linear spine.
UX-DR7: Task-list row component (used in both planned and live Task List states) — agent identity, one-line action summary, status badge, and an action cluster: view-graph (jump to DAG Canvas), stop (always available on any non-terminal agent), and a question badge visible only when that specific agent has an open question. Planned state renders dashed/no-shadow; live state renders solid with a status-tinted rail.
UX-DR8: Node-inspector-family drawer component — a shared right-docked slide-over shell used for two distinct framings: `trouble` (push-or-cancel decision UI) and `waiting_input` (question card + free-text response + Send, no cancel action). Both states always show a telemetry stat row and the agent's live reasoning ("thinking") trace, independent of whether a question is open.
UX-DR9: Pre-Flight Permission checklist row component — grouped per agent (not a flat list), each file/MCP item independently checkable (not all-or-nothing), sensitive files flagged distinctly, synthesized (FastMCP-generated) bridges labeled as their own distinct entry from pre-provided servers.
UX-DR10: Proposed-change card component (Settings) — target path, a category chip using exactly one of the real 8 `target_category` backend values (`team_instructions`/`local_instructions`/`settings.json`/`settings.local.json`/`rule`/`skill`/`command`/`agent` — never an invented label, never an MCP grant), an action badge (create/update/revoke), a plain-language summary, and a content preview, gated behind an explicit Approve & Apply / Reject pair — nothing written until approved.
UX-DR11: Replay context-node annotation component (Full Flight Path Replay) — same visual family as the live DAG Canvas node, explicitly reframed with a persistent "Replay" badge, solid non-pulsing route lines, and a reduced legend scoped to terminal states only; token usage shown per context node and per agent, nested consistently with Post-Run Audit's numbers.
UX-DR12: DAG Canvas connecting-line semantics — the live canvas's agent-to-agent connector lines render dependency/dispatch order (which agent releases which), NOT the context-node-level flight path (which is only made visually explicit in the Replay screen, UX-DR11). Do not wire the live canvas's lines to context-node/flight-path data.
UX-DR13: Usage & Privacy settings section — a third section in the Settings drawer (after "Add a rule/preference" and "Currently configured"): a single opt-in toggle (off by default), one line describing exactly what's shared if enabled (run counts, per-agent completion/cancellation outcome, estimated-vs-actual token/time deltas — never file contents, prompts, or reasoning text), and a read-only summary of what's been sent so far once enabled.
UX-DR14: Voice and tone standard — plain, grounded, factual copy across every surface; no hype language, no exclamation points, no marketing tone or celebratory/apologetic framing of agent outcomes. Warm register comes from color/shape (DESIGN.md), never copy tone.

**Known UX open items (do not invent answers during story-writing — confirm or defer instead):** exact keyboard shortcut vocabulary; responsive/smaller-viewport (tablet/mobile) breakpoint behavior; Settings' "pending / not yet applied" indicator exact hex value; precise motion timing/easing values (UX-DR5); the Permission Manager's mid-run-revoke screen has confirmed behavior (UX-DR6, shares the Pre-Flight checklist row pattern per UX-DR9) but no rendered visual mock.

### FR Coverage Map

FR-1: Epic 1 - Natural-language settings update
FR-2: Epic 1 - Settings change approval gate
FR-3: Epic 1 - Settings transparency on demand
FR-26: Deferred to v2 - Opt-in telemetry collection (decided during Epic 1 story-writing, 2026-09-07 — see Additional Requirements note)
FR-4: Epic 3 - Pre-Flight Permission checklist (moved from Epic 2 during Epic 2 story-writing, 2026-09-07 — approval and execution kickoff now live in the same epic, so "Approve & Run" no longer dead-ends before that epic exists)
FR-6: Epic 1 - Permission grant addition outside Pre-Flight (moved from Epic 2 during Epic 1 story-writing, 2026-09-07 — doesn't require a submitted task to exist)
FR-7: Epic 2 - Task decomposition
FR-8: Epic 2 - Per-agent context graph construction
FR-9: Epic 2 - Flight path selection
FR-10: Epic 2 - Token/time cost prediction
FR-23: Epic 4 - On-the-fly MCP bridge synthesis
FR-24: Epic 4 - Pre-Flight approval for synthesized bridges
FR-25: Epic 4 - Generated tool debugging (MCP Inspector)
FR-5: Epic 3 - Mid-run permission revoke with immediate cutoff (jointly owned with Epic 1 — see Epic 1's Story 1.4, which covers the base grant-state change; Epic 3 covers the live-agent cutoff mechanics specifically)
FR-11: Epic 3 - Control-tower sequencing
FR-12: Epic 3 - Task list & summaries display
FR-13: Epic 3 - Live DAG rendering
FR-14: Epic 3 - Real-time flight path tracking
FR-15: Epic 3 - Real-time token/time telemetry
FR-16: Epic 3 - Stop & Undo
FR-17: Epic 3 - Trouble notification with push-or-cancel
FR-18: Epic 3 - In-UI question response and live reasoning visibility
FR-19: Epic 5 - Expected vs. actual metrics summary
FR-20: Epic 5 - Flight path replay
FR-21: Epic 5 - Generated files changelog
FR-22: Epic 5 - Cancelled tokens tracking

### UX-DR Coverage Map

UX-DR1 (color theme), UX-DR2 (font/monospace rule), UX-DR3 (shape/elevation), UX-DR4 (accessibility floor), UX-DR5 (motion), UX-DR14 (voice/tone) — **Global, not story-specific.** These are implementation constraints that apply to every screen in every epic's stories, not standalone capabilities. Not cited per-story below; enforced across all UI work regardless of epic.
UX-DR6 (information architecture) — **Global structural constraint**, realized by the epic/story sequence itself: Settings + Permission Manager as persistent globals (Epic 1), the linear spine Pre-Flight → Live Run → Post-Run Audit → Replay (Epics 3 → 5).
UX-DR7 (task-list row): Story 3.2
UX-DR8 (node-inspector-family drawer, both framings): Stories 3.7, 3.8
UX-DR9 (Pre-Flight checklist row): Stories 3.1, 4.2
UX-DR10 (proposed-change card): Story 1.2
UX-DR11 (Replay context-node annotation): Story 5.2
UX-DR12 (DAG Canvas connecting-line semantics): Story 3.3
UX-DR13 (Usage & Privacy settings section): **Deferred to v2, alongside FR-26** — no story in v1 (see Additional Requirements note and FR-26 in the FR Coverage Map).

## Epic List

*Sequencing notes from Advanced Elicitation (Assumption Audit + Cascading Failure Simulation), applied 2026-08-30:*
- ***Epic 2 is the critical-path epic.*** *Every other epic (3, 4, 5) is cascade-blocked if Epic 2 slips or is under-built — it's the single point of failure for the whole product. Give it the most review rigor and schedule buffer of any epic in this list.*
- *NFR ownership is made explicit per epic below so none of the 6 cross-cutting NFRs silently fall through story-writing.*
- *The live-run epic stays merged (live visibility + live control as one epic) — confirmed deliberately, not just inherited from the UX's navigation grouping.*
- *That epic also absorbed Pre-Flight approval (FR-4) from Epic 2 during Epic 2 story-writing, 2026-09-07 — approval and execution kickoff are now one continuous flow within it, with no dead-end between them. Epic 2 remains the critical-path epic above: it's now a pure planning/estimate preview, but every downstream epic still depends entirely on its DAG blueprint, context graphs, and flight paths.*
- ***Epics 3 and 4 swapped, 2026-09-07*** *(during Epic 3 story-writing): Dynamic Tool Synthesis moved from 3rd to 4th, and Approve & Run a Task moved from 4th to 3rd. Reason: 2 of Dynamic Tool Synthesis's 3 FRs (FR-24, FR-25) turned out to depend on Approve & Run's Pre-Flight checklist UI and process-spawning capability — so Dynamic Tool Synthesis can no longer ship before that epic exists. Only FR-23 (bridge synthesis itself) is independent.*

### Epic 1: Project Configuration, Settings & Permissions
Configure `.claude/` via natural language, review current configuration, and manage standing file/MCP permission grants — all without ever running an agent. Fully standalone; the first surface any user touches.
**FRs covered:** FR-1, FR-2, FR-3, FR-6 (FR-5 jointly with Epic 3 — see FR Coverage Map; FR-26 deferred to v2 — see Additional Requirements note)
**NFRs owned:** none directly (NFR-6 security boundary is jointly owned with Epic 3/4 — see those epics).

### Epic 2: Plan a Task
Submit a plain-language intent and watch the Meta-Planner decompose it into agents with a context graph, flight path, and cost estimate — a full planning/estimate preview, nothing executes and nothing is gated yet.
**FRs covered:** FR-7, FR-8, FR-9, FR-10 (FR-4 moved to Epic 3, FR-6 moved to Epic 1 — see FR Coverage Map)
**NFRs owned:** NFR-4 (planning latency — context graph + flight path selection ceiling).
**Resolved during story-writing (2026-09-07):** the former "Approve & Run dead-end" open item no longer applies — Pre-Flight approval and execution kickoff both live in Epic 3 now, so there's no gap between approving and something visibly happening.

### Epic 3: Approve & Run a Task
Approve or reject file/MCP access per item on the planned run (Epic 2's output), then watch it actually execute — DAG canvas, live flight path, live telemetry, task list — plus full intervention: stop any agent, push-or-cancel one in trouble, answer a blocking question, revoke access mid-run. Pre-Flight approval and live execution are one epic because approving now leads directly into something visibly happening, with no dead-end. Sequenced ahead of Dynamic Tool Synthesis because 2 of that epic's 3 FRs depend on capabilities this epic builds (see Epic 4's cross-epic dependency note).
**FRs covered:** FR-4, FR-5, FR-11, FR-12, FR-13, FR-14, FR-15, FR-16, FR-17, FR-18
**NFRs owned:** NFR-1 (streaming latency); NFR-2 (checkpoint durability); NFR-3 (process cleanup guarantee, including the crash/restart case); NFR-5 (cost visibility); NFR-6 (security boundary, jointly with Epic 1/4 — Pre-Flight is now the primary enforcement point). Also builds the shared FastMCP process-spawning/lifecycle capability that Epic 4's FR-25 depends on, and the Pre-Flight checklist UI that Epic 4's FR-24 depends on.

### Epic 4: Dynamic Tool Synthesis
When a task needs an external API with no existing MCP server, the system generates a new bridge on the fly during planning — gated through the same Pre-Flight approval as everything else (Epic 3), with debugging support before it ever touches a real agent.
**FRs covered:** FR-23, FR-24, FR-25
**Cross-epic dependency:** FR-23 depends only on Epic 2 (Meta-Planner) and is fully independent. **FR-24 and FR-25 both depend on Epic 3** — FR-24 needs Epic 3's Pre-Flight checklist UI to exist (a synthesized bridge is just another item in that same checklist), and FR-25 (MCP Inspector debugging, `uv run mcp dev server.py`) needs the same FastMCP process-spawning/lifecycle capability (AD-6) that Epic 3 builds for real agent execution. This is why this epic was moved to sequence after Epic 3, 2026-09-07.
**NFRs owned:** NFR-6 (security boundary, jointly with Epic 1/3 — synthesized bridges get the same trust boundary as pre-provided servers, no exception).

### Epic 5: Post-Run Audit & Results
After a run completes: expected-vs-actual metrics, the full flight path replay, a changelog of files touched, and cancelled-token accounting kept structurally separate from completed work.
**FRs covered:** FR-19, FR-20, FR-21, FR-22
**NFRs owned:** none directly.
**Note:** FR-19/20/21 only need a *completed* run to exist (Epic 3's core loop) — they don't require Epic 3's cancellation path specifically. Only FR-22 (cancelled-token accounting) needs a *cancelled* run to have real data, i.e. needs Epic 3's Stop & Undo (FR-16) to have actually been exercised. FR-19/20/21 could theoretically be story-written and tested in parallel with the tail end of Epic 3; FR-22 cannot.

## Epic 1: Project Configuration, Settings & Permissions

Initialize the project, then configure `.claude/` via natural language, review current configuration, and manage standing file/MCP permission grants — all without ever running an agent. Fully standalone; the first surface any user touches.
**FRs covered:** FR-1, FR-2, FR-3, FR-6 (FR-5 jointly with Epic 3; FR-26 deferred to v2)

### Story 1.1: Initialize project structure

As a developer,
I want a working Next.js frontend and Python/FastAPI backend skeleton set up per the Architecture spine's source tree,
So that every following story has a real project to build on, instead of starting from nothing.

**Acceptance Criteria:**

**Given** an empty repository (greenfield — no starter template is used per the Architecture spine)
**When** initial project setup runs
**Then** a `frontend/` (Next.js 16.3.x) and `backend/` (FastAPI 0.141.x, with `brain/`, `engine/`, `dynamic_tools/`, `telemetry/` subpackages) directory structure exists, matching the Architecture spine's Source Tree
**And** the local Redis dependency (8.x, via Docker Compose or local install) is configured and reachable
**And** a bare `.claude/` directory is created if one doesn't already exist, ready for Story 1.2 to populate
**And** the Architecture spine's stack pins (Next.js 16.3.x, FastAPI 0.141.x with `starlette>=1.0.1`, LangGraph 1.2.x, FastMCP 3.4.5+, Pydantic 2.13.x, redis-py 8.x) are locked in the respective dependency manifests

### Story 1.2: Submit a natural-language settings request and approve the proposed change

As a developer,
I want to describe a configuration change in plain language and see exactly what it will write before it happens,
So that I never get silent config drift.

**Acceptance Criteria:**

**Given** an existing or newly-initialized `.claude/` directory (Story 1.1)
**When** I submit a natural-language request (e.g. "always use pytest, never commit `.env` files")
**Then** the system classifies it into one or more proposals, each rendered as a proposed-change card (UX-DR10) showing a real `target_category` (one of the 8 backend values), the target file path, the action (create/update/revoke), a plain-language summary, and a content preview
**And** nothing is written to `.claude/` until I press Approve & Apply
**And** pressing Reject discards the proposal with no files touched

### Story 1.3: View current `.claude/` configuration

As a developer,
I want to see everything currently configured in `.claude/` at a glance,
So that I have full visibility before making changes.

**Acceptance Criteria:**

**Given** I open Settings
**When** the panel loads
**Then** I see a current-state summary of existing rules, subagent personas, and permission grants
**And** the summary reflects the actual on-disk state of `.claude/`, never a cached snapshot

### Story 1.4: View and manage permission grants between runs

As a developer,
I want to see and change which files/MCP servers are currently granted, even when nothing is running,
So that I can review and tidy up access without needing an active task.

**Acceptance Criteria:**

**Given** I open the Permission Manager with no run active
**When** the panel loads
**Then** I see every currently granted file and MCP server, itemized by prior grant (not a flattened list)
**And** I can add a new grant directly, without re-approving any already-granted items
**And** I can revoke any existing grant, which updates the standing grant state immediately and applies to all future runs
**And** if no agent is currently using the revoked resource, no further action is needed — the grant is simply gone

**Out of scope for this story (Epic 3 dependency):** interrupting an agent that is *actively mid-stream using* the just-revoked resource. Until Epic 3's live-run infrastructure exists, revoking a grant while it's in active use updates the stored state but does not abort the in-progress agent — it will keep running on that resource until it finishes. True "immediate cutoff" (abort stream, terminate spawned process, same path as Stop & Undo) is Epic 3's FR-5 story, which extends this one.

**Epic 1 Summary:** 4 stories, FR-1/FR-2/FR-3/FR-6 covered, plus the base half of FR-5 (full mid-run cutoff completes in Epic 3) and the foundational project-initialization story (Story 1.1, no FR — carries the Architecture spine's greenfield setup requirement). No forward dependencies. FR-26 (opt-in telemetry) deferred to v2 — no story written for it in v1.

## Epic 2: Plan a Task

Submit a plain-language intent and watch the Meta-Planner decompose it into agents with a context graph, flight path, and cost estimate — a full planning/estimate preview, nothing executes and nothing is gated yet.
**FRs covered:** FR-7, FR-8, FR-9, FR-10

### Story 2.1: Decompose a task into agents

As a developer,
I want to hand off a plain-language task and see it broken into a concrete set of agents with responsibilities,
So that I know what will actually run before anything starts.

**Acceptance Criteria:**

**Given** I submit an intent for an existing or new codebase
**When** the Meta-Planner processes it
**Then** I see a list of proposed agents (main orchestrator + subagents), each with a one-line responsibility
**And** a structured DAG blueprint is produced from this decomposition

### Story 2.2: View each agent's context graph

As a developer,
I want to see the sources and topics each agent will draw from,
So that I can verify it's pulling from the right places before it runs.

**Acceptance Criteria:**

**Given** agents have been decomposed (Story 2.1)
**When** I view an agent
**Then** I see a context graph of subtopic nodes — sourced from MCP servers, local docs, existing codebase files (for existing-repo runs), and Claude's existing context — connected by topical closeness
**And** each node shows which source it came from

### Story 2.3: Review flight path and cost estimate

As a developer,
I want to see the route each agent will take through its context and the predicted token/time cost,
So that I can judge efficiency before approving anything.

**Acceptance Criteria:**

**Given** an agent's context graph exists (Story 2.2)
**When** flight path selection runs
**Then** I see the selected route overlaid on the graph — covering required context within the token budget, at the most efficient available route
**And** I see a per-agent and aggregate token/duration estimate before execution

**Epic 2 Summary:** 3 stories, all 4 in-scope FRs (FR-7, FR-8, FR-9, FR-10) covered, no forward dependencies. FR-4 (Pre-Flight approval) is deliberately not in this epic — it opens Epic 3 instead, where approval leads directly into execution.

## Epic 3: Approve & Run a Task

Approve or reject file/MCP access per item on the planned run, then watch it actually execute — DAG canvas, live flight path, live telemetry, task list — plus full intervention: stop any agent, push-or-cancel one in trouble, answer a blocking question, revoke access mid-run.
**FRs covered:** FR-4, FR-5, FR-11, FR-12, FR-13, FR-14, FR-15, FR-16, FR-17, FR-18

### Story 3.1: Approve Pre-Flight permissions and start a run

As a developer,
I want to approve or reject each file/MCP access individually and then have the run actually start,
So that I control exactly what happens before it happens.

**Acceptance Criteria:**

**Given** a planned run from Epic 2 (agents, context graphs, flight paths, cost estimates)
**When** I review the Pre-Flight checklist row-per-item (UX-DR9), grouped per agent, with sensitive files flagged distinctly
**Then** I can approve or reject each file/MCP item independently, and execution does not begin until every item has a decision
**And** once approved, the control tower begins sequencing subagent execution via each agent's explicit declared dependencies, applying uniformly whether this is a new or existing codebase
**And** an agent whose task depends on a rejected item proceeds without that resource — no re-planning, no hard block
**And** this is the entire v1 trust boundary (NFR-6) — no additional OS-level sandboxing exists beyond what's granted here

### Story 3.2: View the live task list

As a developer,
I want to see a live list of all agents and their status while a run is in progress,
So that I always know what's happening without digging into any one agent.

**Acceptance Criteria:**

**Given** a run is in progress (Story 3.1)
**When** I view the Task List
**Then** each agent (main orchestrator + subagents) shows as a task-list row (UX-DR7) with agent identity, a one-line action summary, and a status badge
**And** each row has an action cluster: view-graph (jump to that agent's DAG/context view), stop (always available on any non-terminal agent), and a question badge visible only when that agent has an open question
**And** status updates reach this view within NFR-1's sub-second perceived delay

### Story 3.3: View the live DAG canvas

As a developer,
I want to see the live DAG of all agents with what context/files/MCP servers each is using,
So that I can visually track the whole run at once.

**Acceptance Criteria:**

**Given** a run is in progress
**When** I open the DAG Canvas
**Then** agents appear as nodes connected by dependency/dispatch order (which agent releases which) — not context-node-level flight path (UX-DR12)
**And** each agent node shows context gained so far, files used, and MCP servers in use, with synthesized (FastMCP-generated) bridges labeled distinctly from pre-provided servers
**And** this view updates within NFR-1's sub-second latency

### Story 3.4: Track flight path live within an agent

As a developer,
I want to watch a single agent's flight path advance node by node as it actually executes,
So that I can see exactly where it is in its own context.

**Acceptance Criteria:**

**Given** an agent is executing (Story 3.1) and I've selected it (from Story 3.2's task list or Story 3.3's canvas)
**When** I view that agent's context graph (built in Epic 2)
**Then** its previously-selected flight path (Story 2.3) updates live, context node by context node, reflecting its current position and nodes already passed
**And** this updates within NFR-1's sub-second latency

### Story 3.5: View live token/time telemetry

As a developer,
I want to see expected-vs-actual token and time usage update live per agent and overall,
So that I can catch runaway cost or time before it's too late.

**Acceptance Criteria:**

**Given** a run is in progress
**When** I view telemetry for any agent or the run overall
**Then** I see the expected (from Story 2.3's estimate) vs. actual token count and elapsed time, updating live
**And** v1 provides no hard cap or warn-before-exceed threshold (NFR-5) — this live view plus Stop & Undo (Story 3.6) are the only cost guardrails

### Story 3.6: Stop and undo an agent

As a developer,
I want to immediately abort an agent and roll back its work,
So that I can cut my losses the moment something looks wrong.

**Acceptance Criteria:**

**Given** an agent is executing
**When** I press Stop on that agent
**Then** its in-flight stream is aborted immediately, any spawned processes it owns are terminated, and its state rolls back to its last pre-interrupt checkpoint
**And** tokens already spent on the aborted work are tracked separately as cancelled tokens (FR-22, Epic 5), never folded into completed-work totals
**And** checkpoint durability holds even across a backend crash/restart (NFR-2, Redis AOF), and every spawned process is confirmed terminated or re-verified on restart, never left orphaned (NFR-3)

### Story 3.7: Get notified of trouble, push or cancel

As a developer,
I want to be notified the moment an agent runs into trouble,
So that I can redirect it or cut it off before it wastes more time.

**Acceptance Criteria:**

**Given** an agent is executing
**When** it hits trouble mid-execution
**Then** I'm notified (status changes to `trouble`, delivered as a status event, not an error) and the node-inspector-family drawer (UX-DR8) opens in its trouble framing
**And** I can push it (give redirect/guidance to get it back on track) or cancel it (same terminal outcome as Story 3.6)
**And** the drawer always shows a telemetry stat row and the agent's live reasoning trace regardless of the trouble state

### Story 3.8: Answer a blocking question / watch live reasoning

As a developer,
I want to answer a question an agent is blocked on, and separately watch any agent's live reasoning at any time,
So that I stay unblocked and stay informed.

**Acceptance Criteria:**

**Given** an agent is waiting on my input
**When** it reaches `waiting_input` status
**Then** the same node-inspector-family drawer (UX-DR8) opens in its question framing — showing the question, a free-text response field, and Send (no cancel action in this framing)
**And** submitting my response unblocks the agent to continue
**And** I can open any agent's live reasoning ("thinking") trace at any time, independent of whether that agent currently has an open question

### Story 3.9: Revoke a permission mid-run with immediate cutoff

As a developer,
I want revoking a grant to immediately cut off every agent using it, not just stop future use,
So that access control actually means something during a live run.

**Acceptance Criteria:**

**Given** Story 1.4's standing grant view, now with a run active
**When** I revoke a grant that one or more agents are actively using
**Then** every agent currently using that resource is cut off immediately — same abort/cleanup path as Stop & Undo (Story 3.6)
**And** this extends Story 1.4, which already handles revoking a grant with no agent using it
**And** revoking one shared grant cuts off every agent using it, not just one instance of the grant

**Epic 3 Summary:** 9 stories, all 10 FRs (FR-4, FR-5, FR-11 through FR-18) covered, no forward dependencies.

## Epic 4: Dynamic Tool Synthesis

When a task needs an external API with no existing MCP server, the system generates a new bridge on the fly during planning — gated through the same Pre-Flight approval as everything else (Epic 3), with debugging support before it ever touches a real agent.
**FRs covered:** FR-23, FR-24, FR-25

### Story 4.1: Synthesize an MCP bridge for a missing capability

As a developer,
I want the system to generate a working MCP bridge when my task needs an external API with no existing server,
So that I don't have to hand-write one myself.

**Acceptance Criteria:**

**Given** the Meta-Planner identifies a task step needing external API access with no matching MCP server
**When** planning runs (Epic 2)
**Then** a compliant MCP bridge is generated wrapping that API

### Story 4.2: Approve a synthesized bridge through Pre-Flight

As a developer,
I want a synthesized bridge to go through the exact same approval gate as any other MCP server,
So that the system doesn't get a free pass just because it generated the tool itself.

**Acceptance Criteria:**

**Given** a synthesized bridge exists (Story 4.1)
**When** Epic 3's Pre-Flight checklist (UX-DR9) renders
**Then** the bridge appears as its own item, labeled distinctly from pre-provided servers
**And** it is approved or rejected the same way as any other item — no special treatment

### Story 4.3: Debug a synthesized bridge before it runs

As a developer,
I want to test a generated bridge against the MCP Inspector before any real agent touches it,
So that I catch a bad synthesis before it wastes a run.

**Acceptance Criteria:**

**Given** a synthesized bridge exists (Story 4.1)
**When** I run `uv run mcp dev server.py` against it
**Then** I can inspect and call its tools directly and confirm it behaves correctly
**And** this happens before Pre-Flight approval (Story 4.2), catching a bad synthesis before it's ever offered for approval

**Epic 4 Summary:** 3 stories, all 3 FRs (FR-23, FR-24, FR-25) covered. Story 4.1 is standalone (needs only Epic 2); Stories 4.2 and 4.3 both depend on Epic 3 capabilities (Pre-Flight checklist UI, FastMCP process-spawning) that exist by the time this epic is reached.

## Epic 5: Post-Run Audit & Results

After a run completes: expected-vs-actual metrics, the full flight path replay, a changelog of files touched, and cancelled-token accounting kept structurally separate from completed work.
**FRs covered:** FR-19, FR-20, FR-21, FR-22

### Story 5.1: View expected-vs-actual metrics summary

As a developer,
I want to see a summary comparing estimated vs. actual time/tokens per agent and overall after a run completes,
So that I can judge how accurate the planning was.

**Acceptance Criteria:**

**Given** a run has completed (Epic 3)
**When** I open the Post-Run Audit
**Then** I see, per agent and in aggregate, the estimated (Story 2.3) vs. actual time and token usage
**And** any discrepancy is shown clearly, as a delta or percentage over/under the estimate

### Story 5.2: Replay the full flight path

As a developer,
I want to replay the actual route each agent took through its context,
So that I can review exactly what happened, context node by context node.

**Acceptance Criteria:**

**Given** a run has completed
**When** I open Full Flight Path Replay for a given agent
**Then** I see the actual route taken, rendered as a Replay context-node annotation (UX-DR11) — same visual family as the live DAG Canvas node, reframed with a persistent "Replay" badge, solid non-pulsing route lines, and a reduced legend scoped to terminal states only
**And** token usage is shown per context node and per agent, nested consistently with Story 5.1's numbers

### Story 5.3: View the generated files changelog

As a developer,
I want to see every file created, modified, or deleted during a run, attributed to the responsible agent(s),
So that I know exactly what changed in my codebase.

**Acceptance Criteria:**

**Given** a run has completed
**When** I open the Post-Run Audit's changelog
**Then** I see every file created, modified, or deleted during the run, each attributed to its contributing agent(s)
**And** this reflects the actual on-disk state after the run, not a predicted or planned state

### Story 5.4: View cancelled tokens as a separate line item

As a developer,
I want tokens spent on cancelled or discarded work tracked separately from completed work,
So that my cost picture isn't distorted by aborted attempts.

**Acceptance Criteria:**

**Given** at least one agent was stopped or cancelled during the run (Epic 3's Stop & Undo)
**When** I view the Post-Run Audit
**Then** cancelled tokens appear as their own distinct line item, never folded into completed-work totals
**And** if no agent was cancelled during the run, this line item shows zero rather than being silently omitted from the UI

**Epic 5 Summary:** 4 stories, all 4 FRs (FR-19, FR-20, FR-21, FR-22) covered, no forward dependencies — all four are independent facets of the same Post-Run Audit screen.
