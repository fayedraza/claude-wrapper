---
title: Claude Wrapper PRD
status: final
created: 2026-08-30
updated: 2026-08-30
---

# PRD: Claude Wrapper

## 0. Document Purpose

This PRD is the working reference for the PM, the architecture and UX skills that follow it, and the epics/stories that will drive development. It works backward from a finalized technical architecture (`docs/claude_wrapper_system_architecture_and_plan.md`) to define product requirements — capabilities and their FRs, not implementation. Terms defined in the Glossary (§3) are used verbatim throughout; features are grouped (§4) with globally numbered FRs so downstream artifacts (epics, tickets) have stable references. Mechanism-level detail (the flight path routing algorithm, control-tower sequencing internals) and UX-specific depth (aesthetic direction) that don't belong in a requirements document live in `addendum.md` alongside this file.

## 1. Vision

Claude Wrapper replaces the terminal for AI agent orchestration and hand-off — not for general shell use, and not the IDE. Git, test runners, debugging, and ad hoc scripts stay wherever the developer already runs them; what moves out of the terminal specifically is the back-and-forth of directing and questioning Claude's agents. Setup happens in plain language: developers describe the rules, permissions, and subagent personas they want, and the Settings Router maps that intent into a git-aware `.claude/` control center — which Claude can explain back in full whenever the user asks what's actually configured.

From there, developers submit intent and see a live graph of the plan: which subagents will run, and for the main orchestrator agent and every subagent alike, the specific context sources (MCP servers, local docs, existing Claude context) it draws from, plus the route through that context — the "flight path" — that the Meta-Planner picked to cover what's needed without burning tokens on irrelevant material. Before anything executes, the user approves exactly which files and MCP servers each agent can touch, and can add or revoke that access at any time.

While it runs, token and context usage stream live against the estimate, so cost drift is visible the moment it happens instead of only at the end — the user still has to watch and act (via Stop & Undo) if a run trends expensive, since v1 sets no automatic spending cap. When a subagent needs a decision, the platform pauses and asks in the UI — no terminal round-trip — and a bad turn can be undone via checkpoint rollback that cancels the live stream and cleans up any spawned processes, not just abandoned mid-thought.

After the run, the Post-Run Audit replays the actual path against the planned one with real token/time deltas, turning every run into evidence for scoping the next prompt better. The IDE remains the source of truth for the resulting files and commands — Claude Wrapper owns the agent conversation, not the codebase.

## 2. Target User

### 2.1 Jobs To Be Done

- *When I hand off a coding task to an agent, I want the system to work out how many agents/subagents the task needs and what each one is responsible for, so I don't have to manually break down the work or babysit a single monolithic agent.*
- *When those agents run, I want their context sources matched to only what each one actually needs and the token/time cost predicted up front and tracked live, so I have real-time visibility into cost as it happens instead of finding out after the fact.*
- *While a run is in progress, I want to see what each agent is doing, answer it directly when it's blocked, and kill any agent I decide isn't needed, so a bad plan doesn't run to completion on autopilot.*

### 2.2 Non-Users (v1)

- Teams needing concurrent, shared multi-user sessions on a single run — deferred to v2 (§6.2).
- Anyone wanting a non-Claude model — out of scope permanently (§5).
- Anyone wanting a managed/cloud-hosted deployment instead of running locally — deferred to v3 (§6.2).
- Developers who want an agent tool to replace their IDE, not just their terminal — Claude Wrapper is explicitly a companion to the IDE (§5).

### 2.3 Key User Journeys

- **UJ-1. Dana hands off a feature and watches the plan take shape.**
  - **Persona + context:** Dana, a backend-leaning developer, tired of babysitting a single agent's raw terminal output.
  - **Entry state (existing repo):** `.claude/` already configured from a prior session; Dana opens Claude Wrapper against this existing repo.
  - **Entry state (new repo):** no `.claude/` yet — the Settings Router creates it fresh as part of Initialization.
  - **Path:**
    1. Dana types her intent in plain language (e.g. "add OAuth2 login with JWT").
    2. The Meta-Planner determines how many agents/subagents are needed and what each is responsible for. The main orchestrator agent acts as "control tower" for every run, existing repo or new: it starts one agent's task and holds dependent subagents in a waiting state until it's safe to release them, rather than firing everything at once.
    3. For each agent, the system gathers candidate sources — MCP servers, local docs, existing Claude context, and (for an existing repo) the codebase's own files — and renders a graph of context nodes connected by topical closeness, plus a predicted token/time cost per agent.
    4. Dana reviews and approves the Pre-Flight Permission checklist (files + MCP servers each agent would touch).
    5. Execution starts; one subagent hits `waiting_input` and asks a question inline, which Dana answers directly in the UI, the way she'd type into a terminal.
    6. Dana decides a subagent's task is unnecessary and cancels that "flight" — it terminates cleanly without corrupting agents that depend on it.
  - **Climax:** the run completes and Dana sees the generated/changed files directly in her IDE — proof the work actually landed.
  - **Resolution:** the Post-Run Audit shows, per agent, time and tokens used against the original estimate, plus the full flight path graph of the route actually taken.
  - **Edge case:** Dana cancels a subagent mid-run ("flight cancelled") — the platform must terminate it cleanly (no orphaned FastMCP process) without corrupting the state of dependent agents.

- **UJ-2. Dana updates a project rule mid-project via Settings.**
  - **Persona + context:** Dana, mid-project, wants a standing rule enforced going forward without hand-editing `.claude/` files herself.
  - **Entry state:** Dana opens the Settings panel.
  - **Path:** Dana types a natural-language change (e.g. "always use pytest, never commit `.env` files"); the Settings Router determines which `.claude/` targets to touch (a rule, an agent persona, `settings.json`, etc.) and produces a plain-language summary of the change. Dana reviews and approves it before anything is written — the same gating pattern as the Pre-Flight Permission checklist.
  - **Climax:** Dana sees exactly what will change and confirms it, with no silent config drift.
  - **Resolution:** the updated `.claude/` files are in place and apply starting with the next run.

- **UJ-3. Dana revokes MCP access she no longer needs, mid-run.**
  - **Persona + context:** Dana notices an agent has access to something it shouldn't need anymore.
  - **Entry state:** Dana opens the Permission Manager, either between runs or while a run is active.
  - **Path:** Dana sees the itemized checklist of currently granted files/MCP servers and revokes one.
  - **Climax:** the revoke takes effect immediately — if an agent is actively mid-run using that resource, it is cut off immediately (same abort/cleanup path as Stop & Undo: cancel the live stream, terminate any spawned process cleanly), not merely blocked on its next request.
  - **Resolution:** the agent's run is interrupted or continues without that resource, and all future runs respect the updated grant.

## 3. Glossary

- **Main orchestrator agent ("control tower")** — the top-level agent that receives user intent, plans the DAG, and sequences subagent execution. Not itself a subagent/flight.
- **Subagent (user-facing: "flight")** — a specialized agent spawned by the orchestrator to handle one part of a task (e.g. `auth_scaffold_worker`); "Subagent" is the technical term, "flight" is what the UI calls the same thing. An agent has exactly two terminal outcomes: completed or cancelled — once cancelled, it does not resume. If an agent runs into trouble mid-execution, the user is notified and can either push it (give redirect/guidance to get it back on track) or cancel it.
- **Context node** — a subtopic unit of context (derived from MCP servers, local docs, existing Claude context, or codebase files) that an agent's context graph is divided into. Not to be confused with an **execution node** (below) — two distinct concepts that both use the word "node" in the source architecture, disambiguated here.
- **Context graph** — the graph of context nodes and their topical-closeness connections built for a given agent (main orchestrator or subagent) before it runs.
- **Flight path** — the actual route through context nodes an agent takes, chosen to cover required context within the token budget at the most efficient route; shown live during execution and replayed in the Post-Run Audit.
- **Execution node** — the DAG unit representing one agent's run, carrying that agent's own `config`/`telemetry`/`live_stream` state and checkpoint (§10). One execution node per agent (main orchestrator or subagent); do not confuse with a context node, which is a unit of context, not of execution.
- **Meta-Planner** — the Claude-powered planning layer that determines agent/subagent count, task assignment, source gathering, and token/time estimates.
- **Settings Router** — the Claude-powered layer that parses natural-language configuration requests into structured updates to the git-aware `.claude/` control center.
- **`.claude/` control center** — the git-aware directory holding rules, permissions, subagent personas, and settings.
- **Pre-Flight Permission checklist** — the itemized checklist of files/MCP servers an agent run requests, approved (per item) before execution starts.
- **Permission Manager** — the persistent UI for granting/revoking file and MCP server access at any time, including mid-run.
- **Human-in-the-Loop (HITL) interrupt** — a pause triggered when an agent needs user input or is stopped/interrupted, backed by a LangGraph checkpoint.
- **Checkpoint** — a persisted state snapshot an interrupted or cancelled agent can be rolled back to.
- **Stop & Undo** — the action that aborts an in-flight LLM stream, terminates spawned MCP processes, and rolls back to the pre-interrupt checkpoint.
- **Post-Run Audit** — the final summary comparing estimated vs. actual time/tokens per agent and overall, with the full flight path replay.
- **FastMCP bridge** — a dynamically generated, on-the-fly Model Context Protocol server wrapping an external API for agent use.

## 4. Features

### 4.1 Settings

**Description:** The Settings Router parses natural-language configuration requests into structured updates to the git-aware `.claude/` control center, and gives the user a full transparent summary of current settings whenever they open the panel. Realizes UJ-2.

#### FR-1: Natural-language settings update

User can submit a natural-language configuration request (e.g. "always use pytest, never commit `.env` files") and have the Settings Router determine which `.claude/` target(s) — `team_instructions`, `local_instructions`, `settings.json`, `settings.local.json`, `rule`, `skill`, `command`, `agent` — to create, update, or revoke. Realizes UJ-2.

**Consequences (testable):**
- System classifies each requested change into one of the 8 `target_category` values and produces a `file_path` + `content` + `action` per change.
- System returns a plain-language summary of the proposed changes before any file is written.
- If `.claude/` does not exist (new repo), the system creates the directory structure as part of the first Settings action.

#### FR-2: Settings change approval gate

User must explicitly approve a proposed Settings change before it is written to disk. Realizes UJ-2.

**Consequences (testable):**
- No `.claude/` file is created, modified, or deleted until the user approves the specific summary presented.
- User can reject the proposed change; no files are touched if rejected.

#### FR-3: Settings transparency on demand

User can open Settings at any time and see a full, current summary of everything configured in `.claude/` (rules, permissions, subagent personas, commands, skills).

**Consequences (testable):**
- Summary reflects the current on-disk state of `.claude/`, not a cached snapshot.

### 4.2 Permission Manager

**Description:** Itemized checklist for file/MCP access approval before execution, with the ability to add or revoke access at any time — including mid-run, with immediate effect. Realizes UJ-1 (step 4), UJ-3.

#### FR-4: Pre-Flight Permission checklist

User can review an itemized checklist of every file and MCP server a planned run's agents would access, before execution starts, and approve or reject each item individually (checkbox-style), not just the checklist as a whole. Realizes UJ-1.

**Consequences (testable):**
- Checklist is itemized per agent (main orchestrator and each subagent), not a single flattened list.
- Each file/MCP item can be approved or rejected independently; execution does not begin until the user has made a decision on every item.
- An agent whose task depends on a rejected item proceeds without that resource — its flight path (FR-9) is selected only from the context nodes actually granted, with no re-planning pass and no hard block on the agent starting.

#### FR-5: Mid-run permission revoke with immediate cutoff

User can revoke a previously granted file or MCP server permission at any time, including while an agent is actively using it. Realizes UJ-3.

**Consequences (testable):**
- If any agent is actively mid-run using the revoked resource, every agent currently using it is cut off immediately, not just the one the user was looking at when they revoked — a shared grant is revoked for the whole run, not per grant-instance. Each affected agent's stream is aborted and any spawned process is terminated — same cleanup path as Stop & Undo (FR-16). The revoke does not merely block an agent's *next* request.
- All future runs respect the updated grant automatically.

#### FR-6: Permission grant addition outside Pre-Flight

User can add a new file or MCP server grant at any time outside the Pre-Flight Permission checklist, without re-running the full checklist. Realizes UJ-3.

**Consequences (testable):**
- The newly added grant is available to any agent that requests it starting immediately, without requiring a new run to be started.
- Adding a grant does not require re-approving previously-approved items.

### 4.3 Subagent Task Management

**Description:** The Meta-Planner determines how many agents/subagents a task needs and what each is responsible for, builds a per-agent context graph, selects each agent's flight path, predicts token/time cost, and sequences execution through the main orchestrator agent acting as "control tower." This is the core differentiator of the product. Realizes UJ-1.

#### FR-7: Task decomposition

System determines, from the user's plain-language intent, how many agents/subagents are needed and the specific responsibility of each. Realizes UJ-1.

**Consequences (testable):**
- Output is a structured plan (DAG blueprint) naming each agent/subagent and its task, produced before any execution begins.
- Every subagent's stated responsibility is non-overlapping with every other subagent's in the same plan — no two subagents in one plan own the same piece of work. `[NOTE FOR PM: this is a coarse bound, not a full quality bar for decomposition granularity; revisit at architecture stage once real task-complexity signals exist to size against.]`

#### FR-8: Per-agent context graph construction

System builds a context graph for the main orchestrator agent and every subagent, where context nodes are subtopics derived from that agent's candidate sources — MCP servers, local docs, existing Claude context, and (for an existing repo) the codebase's own files — connected by topical closeness. Realizes UJ-1.

**Consequences (testable):**
- Existing-repo runs include codebase files as context nodes; new-repo runs do not (no codebase yet).
- The graph is rendered visually and available before execution starts.

#### FR-9: Flight path selection

System selects, for each agent, a route through its context graph (the "flight path") that covers the context required for its task, stays within the predicted token budget, and is the most token-efficient route available. Realizes UJ-1.

**Consequences (testable):**
- The selected path is shown to the user before execution and replayed against the actual path taken in the Post-Run Audit (FR-20).

#### FR-10: Token/time cost prediction

System predicts, per agent and in aggregate, the token count and duration a run will require, based on system prompt length, assigned workspace files, and anticipated tool round-trips. Realizes UJ-1.

**Consequences (testable):**
- Estimates are displayed before execution starts and are the baseline the Post-Run Audit (FR-19) compares actuals against.
- Estimates do not account for push-loop iterations (FR-17) or discarded/cancelled work (FR-16, FR-22) as inputs — this is a known, acknowledged source of estimate error affecting SM-2 (§7) that a run involving an interrupt is expected to undershoot.

#### FR-11: Control-tower sequencing

The main orchestrator agent sequences subagent execution — starting one agent's task and holding dependent subagents in a waiting state until it is safe to release them — rather than starting every agent simultaneously. Applies uniformly on existing and new repos. Realizes UJ-1.

**Consequences (testable):**
- A subagent whose task depends on another subagent's output does not begin execution until that dependency completes.

#### FR-12: Task list & summaries display

User can see a live list of tasks for the main orchestrator and every subagent, each with a summary of its intended action, an interactive button to show that agent's DAG graph, a stop/HITL control, and a question button visible only when that agent has an open question.

**Consequences (testable):**
- The question button/badge is not shown for agents that are not currently blocked on input.

### 4.4 Execution Engine

**Description:** Renders the DAG and tracks the flight path and telemetry live during execution. Realizes UJ-1.

#### FR-13: Live DAG rendering

User can view a DAG graph showing context gained, local files used, and MCP servers (FastMCP-generated vs. pre-provided) for the run. Realizes UJ-1.

**Consequences (testable):**
- The DAG reflects the current run's actual agent structure (main orchestrator + every spawned subagent as its own execution node), not a static template.
- Each MCP server shown is labeled as FastMCP-generated (via FR-23) or pre-provided, distinguishably.

#### FR-14: Real-time flight path tracking

User can watch the flight path update live as execution proceeds, context node by context node. Realizes UJ-1.

**Consequences (testable):**
- Each context node the flight path enters is visually marked as "current" within a bounded delay of the backend actually entering it (see §8 Streaming latency NFR).
- Previously-traversed context nodes remain visibly distinguishable from the upcoming, untraversed portion of the path.

#### FR-15: Real-time token/time telemetry

User can see expected vs. actual token and time metrics for each agent and the overall task, updating live during execution.

**Consequences (testable):**
- Displayed actual values update within the bound set by the §8 Streaming latency NFR of the underlying metric changing.
- Per-agent and overall totals are both visible simultaneously, not one or the other.

### 4.5 Human-in-the-Loop & Undo

**Description:** Lets the user immediately abort and roll back a run, or redirect an agent that has run into trouble instead of losing the whole run. Realizes UJ-1 (edge case).

#### FR-16: Stop & Undo

User can immediately abort an in-flight agent's LLM stream, which terminates any spawned FastMCP processes for that step and rolls the agent's execution node back to its pre-interrupt checkpoint state. Realizes UJ-1.

**Consequences (testable):**
- No orphaned processes remain after a Stop & Undo.
- Intermediate scratchpad tokens generated from the aborted step are discarded from the run's completed work but tracked separately as "cancelled tokens" (FR-22) — not folded into the agent's actual-tokens total and not silently dropped.

#### FR-17: Trouble notification with push-or-cancel

When an agent runs into trouble mid-execution, the user is notified and can either push it (provide redirect/guidance input to get it back on track) or cancel it outright.

**Consequences (testable):**
- A cancelled agent does not resume; its outcome is terminal.
- A pushed agent continues from its current state using the user's guidance, without a full checkpoint rollback.

### 4.6 Question Answering

**Description:** Handles a blocked agent's question through an interactive, terminal-like input in the UI. Realizes UJ-1.

#### FR-18: In-UI question response and live reasoning visibility

User can answer a specific agent's blocking question directly in the UI, in free text, the way they would respond in a terminal session — and, independent of whether a question is pending, can watch that agent's live reasoning trace (Claude's "thinking") stream in the same view, not just its status. Realizes UJ-1.

**Consequences (testable):**
- The question button/badge appears only on agents currently in a state requiring input.
- The agent resumes execution using the user's response without a terminal round-trip.
- The live reasoning trace is visible for any executing agent, whether or not it currently has an open question.

### 4.7 Post-Run Audit Engine

**Description:** Final, comprehensive summary of a completed run — expected vs. actual metrics, full flight path replay, and a changelog of what changed. Realizes UJ-1.

#### FR-19: Expected vs. actual metrics summary

User can view, after a run completes, a summary comparing expected vs. actual time and token usage for each agent and for the overall task. Realizes UJ-1.

**Consequences (testable):**
- Every agent that ran (completed or cancelled) has an entry in the summary; none are silently omitted.
- The summary distinguishes actual/completed tokens from cancelled tokens (FR-22) per agent.

#### FR-20: Flight path replay

User can view the full flight path actually taken through the context graph after the run completes, with token usage highlighted per context node and per agent. Realizes UJ-1.

**Consequences (testable):**
- The replayed path matches the actual sequence of context nodes the agent entered during execution, not the originally-planned flight path (FR-9) if the two diverged.
- Token usage is attributable to a specific context node, not just aggregated per agent.

#### FR-21: Generated files changelog

User can view a changelog of files created, modified, or deleted during the run as part of the Post-Run Audit.

**Consequences (testable):**
- Each changelog entry names the specific file path and the operation (created/modified/deleted).
- A file touched by more than one agent in the same run shows once with all contributing agents attributed, not once per agent.

#### FR-22: Cancelled tokens tracking

User can view, as its own line item in the Post-Run Audit, the tokens consumed by work that was later discarded via Stop & Undo or a cancelled agent ("cancelled tokens") — reported separately from the actual-tokens total for completed work. Realizes UJ-1 (edge case).

**Consequences (testable):**
- Cancelled tokens are never added into an agent's or the run's actual/completed token total.
- Cancelled tokens are still visible to the user, per agent, so wasted spend from aborted runs is not hidden.

### 4.8 Dynamic Tools (FastMCP Bridge Synthesis)

**Description:** When a planned task needs an external API capability no existing MCP server covers, the system generates a new, fully compliant MCP bridge for that API on-the-fly and mounts it for the requesting agent's use. A synthesized bridge goes through the same Pre-Flight Permission gate (FR-4) as a pre-provided MCP server before any agent can use it — synthesis does not bypass the security boundary described in §9.

#### FR-23: On-the-fly MCP bridge synthesis

System can identify, during planning, that a task needs an external API capability no existing MCP server provides, and generate a fully compliant MCP bridge for that API on-the-fly.

**Consequences (testable):**
- A synthesized bridge exposes the same MCP protocol surface as a pre-provided server — it is functionally indistinguishable to the agent using it.
- Bridge generation happens during planning (FR-7/FR-8), before the Pre-Flight Permission checklist is shown, so it can be included in that checklist (FR-24) rather than appearing after the user has already approved the run.

#### FR-24: Pre-Flight approval for synthesized bridges

User must approve a newly-synthesized MCP bridge through the same Pre-Flight Permission checklist (FR-4) as any pre-provided MCP server, before the agent that needs it can use it.

**Consequences (testable):**
- A synthesized bridge appears as its own itemized entry in the Pre-Flight checklist, labeled distinctly from pre-provided servers (consistent with FR-13's "FastMCP-generated vs. pre-provided" labeling).
- If the user rejects a synthesized bridge, the requesting agent proceeds without it, per FR-4's rejected-item behavior — no re-planning, no hard block.

#### FR-25: Generated tool debugging (MCP Inspector)

User can interactively test and debug a synthesized MCP bridge before it executes against a real agent, using the MCP Inspector (`uv run mcp dev server.py` / `fastmcp dev server.py`).

**Consequences (testable):**
- Debugging access is available for any synthesized bridge prior to its first use by an agent, not only after a failure.

### 4.9 Usage Telemetry (opt-in)

**Description:** The Success Metrics in §7 require cross-run and cross-user data that a purely local, single-run Post-Run Audit doesn't produce on its own. This feature makes those metrics actually computable, on an explicit opt-in basis.

#### FR-26: Opt-in telemetry collection

User can opt in, from Settings (FR-3), to sharing anonymized usage telemetry — run counts, per-agent completion/cancellation outcomes, and estimated-vs-actual token/time deltas — that feeds the Success Metrics in §7.

**Consequences (testable):**
- Telemetry collection is off by default; the user must take an explicit opt-in action before any data leaves the local install.
- Collected telemetry contains only structured counts, durations, and deltas already computed by the Post-Run Audit (FR-19, FR-22) — no file contents, prompts, agent reasoning (FR-18), or generated code is included.
- User can view what was collected and sent at any time, consistent with the product's transparency principle (FR-3).
- Telemetry collection uses a minimal, purpose-built collection endpoint, distinct from the "cloud-hosted/managed backend" deferred to v3 (§6.2) — that non-goal refers to hosting agent orchestration itself, not a lightweight analytics sink.

## 5. Non-Goals (Explicit)

- Claude Wrapper does not support any LLM provider other than Claude. It is not a multi-model or bring-your-own-model tool, now or in a later version.
- Claude Wrapper does not replace the IDE. It owns the agent conversation (planning, permissions, execution, audit) only — the IDE remains the source of truth for the resulting files and commands.

## 6. MVP Scope

### 6.1 In Scope

- All 9 features and FR-1 through FR-26 ship together in the v1 release: Settings, Permission Manager, Subagent Task Management, Execution Engine, Human-in-the-Loop & Undo, Question Answering, Post-Run Audit, Dynamic Tools (FastMCP Bridge Synthesis), Usage Telemetry. These ship as a unit because the product's value proposition is trust-through-transparency — a context graph without live telemetry, or bridge synthesis without the same Pre-Flight gate as everything else, would each re-create a version of the terminal's opacity problem the product exists to solve.
- Single developer per run (no shared/concurrent multi-user sessions).
- Locally hosted orchestration backend (FastAPI/LangGraph on the developer's own machine), per the architecture doc's technology stack. The opt-in telemetry collection endpoint (FR-26) is a separate, minimal exception — see FR-26's consequences.
- Works against both a brand-new repo and an existing codebase (per UJ-1).

*Note: the architecture doc's 5-phase roadmap (Core Engine → FastMCP Bridge → Visual Canvas → "Node Inspector" [the roadmap phase's name for the slide-over agent detail drawer — unrelated to the context-node/execution-node distinction in §3] → Post-Run Audit) is the build sequence for reaching this v1 release — backend first, then visualization — not a scope cut. Nothing in that roadmap is deferred past v1.*

### 6.2 Out of Scope for MVP

- **Multi-user/team collaboration on a single run** — deferred to v2. Intent is to make this compatible with BMAD-style multi-agent/multi-user collaboration patterns. `[NOTE FOR PM: emotionally load-bearing for the user — revisit at v2 planning, don't let it silently slip further.]`
- **Cloud-hosted/managed backend** — deferred to v3, specifically later than the v2 items above, primarily due to hosting cost. v1 and v2 both stay local-only.

## 7. Success Metrics

*All metrics below are collected via the opt-in telemetry described in FR-26 — they are computable only across the population that has opted in, not the full user base. Numeric targets marked `[PROVISIONAL]` are placeholders pending a pre-launch measurement spike; they exist so each metric is falsifiable in principle, not because real baseline data exists yet (see §11 OQ-4).*

**Primary**
- **SM-1**: Token reduction — average tokens consumed per completed task, compared to a naive/unscoped baseline run (no context graph, full-context dump). Target: `[PROVISIONAL: ≥20% reduction]`, while SM-C1 holds. The naive-baseline comparison itself has no in-scope FR generating it — it must be produced via a one-off, dev-only measurement pre-launch, not an end-user-facing toggle. Validates FR-8, FR-9.
- **SM-2**: Estimate accuracy — mean absolute % delta (MAPE) between predicted and actual tokens/time per agent, as surfaced in the Post-Run Audit. Target: `[PROVISIONAL: ≤20% MAPE]`. Validates FR-10, FR-19. Note FR-10 does not yet account for push-loop/cancellation variance (see FR-10 consequences), which will inflate this metric until addressed.
- **SM-3**: Weekly retention — % of opted-in users with ≥1 run reaching `completed` or `cancelled` (both count — cancelling mid-run is legitimate product use, not a failed session) in a given week, measured from that user's first completed or cancelled run ("week 1" anchor), for each week after. Target: `[PROVISIONAL: ≥40%]`.

**Secondary**
- **SM-4**: Cancellation-to-completion ratio — % of agent runs ended via Stop & Undo / cancel vs. completed normally. Watched as a leading indicator of plan quality, not optimized directly. Validates FR-16, FR-17.
- **SM-5**: Time-to-first-approval — median time from Pre-Flight checklist display to full approval decision (all items decided), for a checklist of typical size (≤10 items). Target: `[PROVISIONAL: under 30 seconds]`. Validates FR-4 (checkbox-style approval should make this fast, not a chore).

**Counter-metrics (do not optimize)**
- **SM-C1**: Task success rate (agent output actually usable/correct) — must not drop as SM-1 (token reduction) improves. A flight path that's cheap but starves an agent of needed context is a regression, not a win. Counterbalances SM-1.
- **SM-C2**: Push-saves that still end in cancellation — if "push" (FR-17) is used but the agent is cancelled shortly after anyway, that's wasted user effort, not a HITL success. Counterbalances SM-4.

## 8. Cross-Cutting NFRs

- **Streaming latency:** agent status, token telemetry, and flight-path updates (FR-14, FR-15) must reach the UI over WebSockets/SSE with low enough latency to feel live, not polled — target a sub-second perceived delay between a backend state change and its UI reflection.
- **Checkpoint durability:** LangGraph state checkpoints (backing FR-16 Stop & Undo and FR-17 push-or-cancel) must survive a backend crash/restart without corrupting or losing the ability to roll back to the last valid checkpoint.
- **Process cleanup guarantee:** every FastMCP process spawned for an agent must be terminated when that agent is cancelled, pushed past, or the run ends — no orphaned processes left running after the UI reports a run as finished or cancelled.
- **Planning latency:** context graph construction and flight path selection (FR-8, FR-9) for a given agent should complete within a low-single-digit-second ceiling for a typical-size repo/task, `[PROVISIONAL — to be validated at architecture stage against real repo sizes]`, so the Pre-Flight Permission checklist (FR-4) doesn't stall the user before they can start reviewing.

## 9. Constraints and Guardrails

**Cost**
- v1 provides visibility only — no hard token/dollar cap and no warn-before-exceed threshold. The Meta-Planner's pre-run estimate (FR-10) and the live telemetry (FR-15) are the guardrail; the user decides whether to Stop & Undo (FR-16) if a run is trending expensive. Hard caps and proactive warnings are open for v2+ reconsideration once real usage data exists.

**Safety**
- Stop & Undo (FR-16) must be reliably available for any executing agent at any time — it is the backstop for every other guardrail in this section.
- A cancelled agent (FR-17) is terminal by design (Glossary, §3) specifically so users never have to guess whether a "cancelled" agent might silently resume.

**Security**
- The Permission Manager's approve/revoke flow (FR-4, FR-5, FR-6) is the v1 security boundary, and it applies equally to synthesized FastMCP bridges (FR-24) — a bridge the system generates for itself does not get a lighter approval path than one that already existed. Spawned FastMCP processes run with no additional OS-level sandboxing beyond what file/MCP access the user has explicitly granted; "isolated" in this context means each bridge is scoped to the agent that requested it, not that it runs in an OS-level sandbox. `[NOTE FOR PM: revisit if v2 multi-user collaboration (§6.2) changes the trust model — a shared session raises the stakes on this boundary.]`

## 10. Developer Products — API Contracts & Public Surface

*Claude Wrapper is itself a developer product: the Settings Router schema and the per-agent execution-node schema are contracts other tooling (and future collaborators, per the v2 multi-user goal) will build against.*

- **Settings Router contract:** `SettingAction` / `SettingsRouterOutput` (Pydantic) is the structured output contract for FR-1/FR-2 — `target_category`, `file_path`, `content`, `action`, plus the `user_summary` used for the FR-2 approval gate. Changes to this schema are breaking changes for any downstream automation built against Settings.
- **Execution-node telemetry contract:** the per-agent execution-node schema (`node_id`, `parent_id`, `status`, `config`, `telemetry`, `live_stream`) backs FR-12, FR-13, FR-14, FR-15, FR-16, FR-17, FR-18. `live_stream` itself carries `thinking` (Claude's live reasoning trace — realizes the "watch the agent think" half of FR-18, alongside the "answer its question" half already named there), `latest_message`, `requires_user_input`, and `interrupt_state`. `status` is a closed enum (`waiting_input`, `executing`, `completed`, `failed`) that does not yet have a value for "in trouble, awaiting push-or-cancel" (FR-17) — proposed fix: add a `trouble` value, distinct from the terminal `failed`/`cancelled` outcomes, so the UI can key its push-or-cancel affordance off the schema rather than inferring it. See §11 OQ-2.
- **Language / runtime targets:** Python (FastAPI + LangGraph) for the orchestration backend, Node.js/Next.js + React Flow for the frontend, per the architecture doc's technology stack. Specific version pins and a formal deprecation/versioning policy for the two contracts above are not yet defined. `[OPEN QUESTION: see §11.]`

## 11. Open Questions

1. What is the versioning/deprecation policy for the Settings Router and execution-node telemetry schemas (§10) once external tooling starts depending on them?
2. §10 proposes adding a `trouble` value to the execution-node `status` enum to give FR-17's push-or-cancel flow a schema home — needs confirmation and formal adoption at the architecture stage, since the source schema doesn't currently have it.
3. All five §7 Success Metric targets are marked `[PROVISIONAL]` pending a pre-launch measurement spike (SM-1 also needs a one-off naive-baseline comparison run, which has no in-scope FR building it) — these need real numbers before they're treated as committed launch criteria.
4. The Key Platform Features table in the source architecture doc scopes the question button to "subagent questions" specifically, while the source's own User Flow section describes it more broadly as any agent needing input — the source itself doesn't resolve this. The PRD (FR-12, FR-18) took the broader reading (main orchestrator can ask questions too); flagging in case that choice needs revisiting once the orchestrator's actual question-asking behavior is designed.
5. FR-11's control-tower sequencing is confirmed to apply uniformly to new and existing repos alike (resolved during discovery — see `addendum.md`'s sequencing note, which describes the mechanism, not a scope limitation to new projects only). No open item here; listed for traceability since the mechanism note could otherwise be misread as new-project-only.

## 12. Open-Item Summary

*This section inventories every outstanding marker in the document by kind, so a reader doesn't have to hunt for them — it is not limited to `[ASSUMPTION]` tags.*

- **`[ASSUMPTION]` tags:** none remain unresolved. Two were raised during discovery (Pre-Flight partial approval, Stop & Undo token accounting) and both were resolved and folded into FR-4 and FR-16/FR-22 respectively — no index entries needed.
- **`[NOTE FOR PM]` callouts (3):** FR-7's decomposition quality bar (coarse only, needs real sizing signals at architecture stage); §6.2's multi-user collaboration deferral (emotionally load-bearing, don't let it silently slip past v2); §9's Security note (revisit trust model if v2 multi-user changes it).
- **Open Questions (§11):** 4 substantive (schema versioning policy, `status` enum adoption, SM target-setting, question-button scope precedent) plus 1 traceability note (FR-11, already resolved, listed to prevent misreading).
