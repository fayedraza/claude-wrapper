---
title: PRD/Addendum → Architecture Spine Reconciliation
scope: Claude Wrapper architecture spine vs. finalized PRD + addendum
created: 2026-08-30
---

# Reconciliation: PRD/Addendum vs. ARCHITECTURE-SPINE.md

Sources read in full:
- `prd.md` (finalized PRD, FR-1–FR-26, Glossary, §7 Success Metrics, §8 Cross-Cutting NFRs, §9 Constraints, §10 Contracts, §11 Open Questions)
- `addendum.md` (flight-path routing mechanism, control-tower sequencing note, aesthetic direction)
- `ARCHITECTURE-SPINE.md` (AD-1 through AD-6, Consistency Conventions, Stack, Structural Seed, Source Tree, Capability → Architecture Map, Deferred)

10 findings below, ordered by severity. Findings 1–3 are structural contradictions or unaddressed core mechanisms (high severity — will cause independent builders to diverge). Findings 4–7 are NFR-enforceability gaps. Findings 8–10 are lower-severity strain/omission items.

---

## 1. [HIGH] AD-2's "Unified Node" model contradicts the PRD's explicit node cardinality

**PRD says (Glossary, §3):**
- **Context node** — a *subtopic* unit within an agent's context graph. An agent has many of these.
- **Execution node** — "the DAG unit representing **one agent's run**, carrying that agent's own `config`/`telemetry`/`live_stream` state and checkpoint... **One execution node per agent** (main orchestrator or subagent)." The Glossary explicitly disambiguates the two specifically *because* the source architecture doc conflated them under one word ("node") and this caused confusion the PRD had to resolve in prose.
- FR-13's consequence reinforces this: the DAG must reflect "main orchestrator + every spawned subagent **as its own execution node**" — i.e., execution nodes are 1:1 with *agents*, not with context-graph subtopics.

**Spine says (AD-2):**
> "`Node` is one entity, not two types... **Every subtopic node in an agent's context graph** carries both context-graph fields... and execution fields (`status`, `telemetry`, `live_stream`, checkpoint reference) **on the same record**. Execution fields are pre-provisioned on **every candidate node in the graph** at planning time..."

**The problem:** AD-2 resolves the PRD's *naming* ambiguity (the same word "node" meaning two things) but in doing so inverts the PRD's *cardinality* model. The PRD's execution node is a per-*agent* entity (one per agent, N agents per run); AD-2's unified Node gives execution-level fields (status/telemetry/live_stream/checkpoint) to every context-graph *subtopic* (many per agent). Under a literal reading of AD-2, a single agent with 10 context nodes in its graph would provision 10 checkpoints/status-tracks/live_streams, not 1 — directly at odds with "one execution node per agent" and with FR-13's requirement that the DAG show one execution node per spawned subagent.

**Consequence:** two builders reading only the spine would build fundamentally different schemas — one might follow AD-2 literally (per-context-node state), the other might follow the PRD/Glossary (state only at the per-agent granularity, context nodes are pure graph structure). This is exactly the kind of quiet, no-home requirement the spine should have caught and didn't; if anything it introduces a new contradiction while trying to remove an old one.

**Recommendation:** AD-2 needs to state explicitly which entity carries execution state — most likely: the per-agent execution node is authoritative for `status`/`checkpoint`/`live_stream`; context (subtopic) nodes carry only graph-structural fields plus a lightweight "traversal marker" (visited/current/upcoming, per FR-14) that is *not* a full checkpoint. As written, AD-2 does not say this and instead says the opposite ("pre-provisioned on every candidate node").

---

## 2. [HIGH] Addendum's flight-path routing algorithm (the "gas"/"wind" mechanism) has no owning AD

**Addendum says:** the flight-path selection is a specific three-part search — (a) a path must exist covering required context, (b) "gas" (tokens) must not run out before the destination (token-budget constraint), (c) the path should follow "wind patterns" (the direction of efficient token usage, not fight against it) — and explicitly flags this as "worth expanding into a concrete routing/scoring algorithm at the architecture stage." PRD FR-9 calls flight-path selection out as producing "the most token-efficient route available," and §4.3 calls Subagent Task Management (which includes FR-9) "the core differentiator of the product."

**Spine:** FR-9 is mapped in the Capability → Architecture Map to "AD-1, AD-2, AD-3" — but AD-1 is the orchestrator-worker paradigm, AD-2 is node structure, AD-3 is explicit *inter-agent* dependency edges (control-tower sequencing between subagents, not intra-agent context routing). None of the six ADs describe the actual routing/scoring mechanism: no cost function, no explicit token-budget-as-constraint rule, no "efficient-direction" heuristic, no algorithm family (shortest-path variant, greedy, LLM-scored, etc.).

**Consequence:** the single most novel, differentiator-defining mechanism in the product — explicitly called out by the addendum as needing architecture-stage formalization — is completely unaddressed by any invariant. Two builders would very plausibly implement two different routing algorithms (e.g., one optimizing purely for coverage-then-cheapest-path, another using an LLM-scored heuristic) and neither would be wrong per the spine, because the spine gives no rule to be right or wrong against. This is the addendum's dropped "gas"/"wind" framing the task flagged as a risk — it did not survive into the spine at all, not even flattened; it is simply absent.

**Recommendation:** add an AD (e.g., AD-7) that names flight-path selection as a constrained-search problem over the context graph with token budget as a hard constraint and token-efficiency as the optimization objective, and states where that search lives (e.g., `backend/brain/meta_planner/`) and roughly what shape it takes (deterministic graph algorithm vs. LLM-scored vs. hybrid) — even a coarse commitment prevents divergence.

---

## 3. [MEDIUM-HIGH] AD-5's terminal-status set contradicts the Glossary's "exactly two terminal outcomes"

**PRD Glossary (§3):** "An agent has **exactly two terminal outcomes: completed or cancelled** — once cancelled, it does not resume."

**PRD §10:** the *current* closed enum is literally listed as `(waiting_input, executing, completed, failed)` — no `cancelled` value appears in that literal list at all, which is itself an internal PRD inconsistency (Glossary names cancelled as one of exactly two terminal outcomes; §10's literal enum list has `failed` but not `cancelled`). §10 proposes adding `trouble`.

**Spine AD-5** resolves this by adopting a six-value enum: `waiting_input | executing | trouble | completed | cancelled | failed`, and states "`completed`, `cancelled`, and `failed` are terminal" — i.e., **three** terminal states.

**The problem:** the spine silently harmonizes a real PRD-internal inconsistency (Glossary's "exactly two" vs. §10's literal 4-value list missing `cancelled`) by inventing a resolution (add `cancelled` back in, keep `failed` as a third terminal state) without flagging that this deviates from the Glossary's explicit "exactly two terminal outcomes" language. AD-5 is probably the *right* practical resolution, but as written it reads as a clean adoption from the PRD when it is actually a substantive interpretive call the spine should own explicitly (i.e., "Glossary's 'exactly two' is superseded; `failed` is a third, system-triggered terminal state distinct from user-triggered `cancelled`").

**Recommendation:** AD-5 should add one sentence acknowledging it reconciles the Glossary/§10 tension and state the reconciliation rule (e.g., "`failed` is a system-detected terminal outcome, distinct from the user-facing `cancelled`; the Glossary's `completed`/`cancelled` framing describes user-visible terminal states, `failed` is the system-error case not enumerated there").

---

## 4. [MEDIUM] Streaming latency NFR (sub-second) has no enforcement home

**PRD §8:** "agent status, token telemetry, and flight-path updates (FR-14, FR-15) must reach the UI over WebSockets/SSE with low enough latency to feel live... target a sub-second perceived delay."

**Spine:** WebSocket/SSE is named as the transport (Structural Seed, `gateway/`), and the Capability → Architecture Map ties Execution Engine (FR-13–FR-15) to "AD-2, Naming/format conventions" — neither of which states or enforces a latency bound. There is no AD, convention row, or component responsibility that makes "sub-second" testable or assigns an owner if it's missed.

**Consequence:** the NFR is stranded — nothing in the spine would fail a review if telemetry arrived with multi-second lag, because no invariant claims ownership of the bound.

---

## 5. [MEDIUM] Planning latency NFR (context graph + flight path, FR-8/FR-9) is entirely unaddressed

**PRD §8:** context graph construction and flight path selection "should complete within a low-single-digit-second ceiling for a typical-size repo/task... so the Pre-Flight Permission checklist doesn't stall the user."

**Spine:** no AD, convention, or Deferred entry mentions planning-time performance at all. Given finding #2 above (no AD even covers the *algorithm*), it follows that no AD covers its *performance envelope* either. This is compounded risk: the mechanism itself is unspecified, and its latency bound is unspecified.

---

## 6. [MEDIUM] Process cleanup guarantee only covers the normal Stop & Undo path, not backend crash/restart

**PRD §8:** "every FastMCP process spawned for an agent must be terminated when that agent is cancelled, pushed past, **or the run ends** — no orphaned processes left running after the UI reports a run as finished or cancelled."

**Spine:** AD-6 covers logical scoping of spawned processes to the requesting agent (no OS sandboxing), and Stop & Undo's cleanup path is named under HITL & Undo (AD-1, AD-5, AD-6). But the NFR's guarantee is process-lifecycle-wide, not just "when the user clicks Stop & Undo" — it must hold even if the backend crashes mid-run (the same crash scenario the Checkpoint Durability NFR explicitly names). The spine's checkpoint-durability convention says LangGraph state survives a restart via Redis, but nothing states what happens to *already-spawned OS processes* on backend restart (are they tracked in Redis so they can be reaped on recovery? killed via a process-group parent that dies with the backend? orphaned and never cleaned?). This is unaddressed.

---

## 7. [MEDIUM] Checkpoint durability: broken internal cross-reference + unspecified Redis persistence mode

Two related issues:

**(a) Broken cross-reference.** The Consistency Conventions table states: "All state mutation goes through LangGraph's checkpointer (Redis, **AD below**)..." — but scanning AD-1 through AD-6, none of them is about the checkpointer/datastore choice. There is no "AD below" for Redis; the reference is dangling. Redis appears only in the Stack table, Structural Seed diagram, and this one convention line — never as its own governed decision.

**(b) Persistence mode unspecified.** PRD §8 requires checkpoints to "survive a backend crash/restart without corrupting or losing the ability to roll back to the last valid checkpoint." Redis's default persistence (RDB snapshotting) can lose the most recent writes on an unclean crash; satisfying this NFR requires a specific persistence configuration (e.g., AOF with `appendfsync everysec` or stricter) or an explicit acceptance of some data-loss window. The spine's Stack/Deployment sections say Redis is "required as a runtime dependency for checkpoint persistence" but never commit to a persistence mode, so the durability NFR is technically unenforceable as specified — a builder could ship default-config Redis and technically comply with the spine while violating the PRD's crash-survival requirement.

**Recommendation:** add the missing AD for the checkpointer/datastore choice, and have it commit to a persistence mode (or explicitly note the mode is deferred with the residual risk named).

---

## 8. [LOW-MEDIUM] Redis as a required local service is an infra commitment not traceable to the PRD text given

**PRD §6.1 (MVP Scope):** "Locally hosted orchestration backend (FastAPI/LangGraph on the developer's own machine), **per the architecture doc's technology stack**." The PRD's Cost constraint (§9) addresses only token/dollar spending caps, not infrastructure footprint. Nothing in the PRD or addendum as given specifies Redis, SQLite, or any particular checkpoint datastore — that detail is deferred to "the architecture doc's technology stack," i.e. `docs/claude_wrapper_system_architecture_and_plan.md`, which was not in scope for this reconciliation pass.

**Spine:** commits to Redis as "required as a runtime dependency," installed via Docker Compose or a local Redis install — i.e., a third long-running local process/service beyond frontend + backend, for a product whose MVP scope emphasizes "single developer... locally hosted."

**Not a contradiction** (the PRD explicitly defers this decision to the architecture doc), but worth flagging: the spine doesn't cite *where* the Redis requirement comes from (is it inherited from the source architecture doc, or a new architecture-stage decision?), and given finding #7's missing AD, there's no visible rationale in the spine itself for why Redis over a zero-extra-process embedded option (e.g., SQLite-backed LangGraph checkpointer) that would better match the "single developer, locally hosted, minimal footprint" framing implied (not stated) by §6.1. If Redis is a new architecture-stage decision rather than inherited, it should be justified against the durability NFR and the local-only framing explicitly, not asserted via a Stack-table row.

---

## 9. [LOW] FR-12 (Task list & summaries display) has no explicit frontend home

**PRD FR-12:** a live list of tasks for the main orchestrator and every subagent, each with a summary, a "show DAG graph" button, a stop/HITL control, and a conditional question button — this is a UI-heavy requirement.

**Spine:** the Capability → Architecture Map rolls FR-7–FR-12 together under "Subagent Task Management," homed in `backend/brain/meta_planner/` and `backend/engine/orchestrator/` — both backend-only locations. The Source Tree's frontend component list (`canvas/`, `node-inspector/`, `settings/`, `permission-manager/`) has no component that obviously owns "the live task list with summaries and per-agent stop/question controls." It might be intended to live inside `canvas/`, but that's not stated, and `node-inspector/` (the slide-over drawer) is a different UI surface (per-agent detail, not the list view). Minor, but a builder could reasonably miss that FR-12 needs its own frontend surface.

---

## 10. [LOW] Control-tower "universal, not new-project-only" clarification not carried into AD-3's rule text

**Addendum** explicitly calls out that control-tower sequencing "was first raised while discussing new-project behavior, but the user later confirmed explicitly... it applies universally — existing repos and new repos alike... It is **not** a new-project-only mechanism," specifically because the source architecture doc's diagram/prose "could otherwise be read as implying parallel-by-default execution." PRD FR-11 states "Applies uniformly on existing and new repos" and PRD §11 OQ-5 preserves this as a traceability note precisely because it's an easy misreading to reintroduce.

**Spine AD-3's rule text:** "the Meta-Planner emits explicit dependency edges in the DAG blueprint at planning time... The Engine mechanically respects this declared ordering — it never infers dependency from runtime behavior." This is correct and doesn't contradict the universal-applicability point, but it also never states it — AD-3 doesn't distinguish new-repo vs. existing-repo runs at all, so a reader of the spine alone (without the addendum's specific warning) has no signal that this was ever an ambiguity worth guarding against. Given the PRD went out of its way to preserve this as a numbered open-item entry specifically so it wouldn't silently regress, its complete absence from AD-3's text is a missed opportunity, not a contradiction.

---

## Summary Table

| # | Severity | Item | PRD/Addendum source | Spine location |
|---|----------|------|----------------------|-----------------|
| 1 | High | AD-2 unified node inverts PRD's execution-node cardinality | Glossary (context node / execution node), FR-13 | AD-2 |
| 2 | High | Flight-path routing algorithm (gas/wind) has no owning AD | addendum §"Context Matcher / Flight Path", FR-9 | Capability map row for FR-7–FR-12 |
| 3 | Medium-High | AD-5's 3 terminal states vs. Glossary's "exactly two" | Glossary, PRD §10/OQ-2 | AD-5 |
| 4 | Medium | Streaming latency NFR unenforceable | PRD §8 | (absent) |
| 5 | Medium | Planning latency NFR unenforceable | PRD §8 | (absent) |
| 6 | Medium | Process cleanup guarantee doesn't cover crash/restart | PRD §8 | AD-6, checkpoint convention |
| 7 | Medium | Checkpoint durability: broken "AD below" ref + no persistence mode | PRD §8 | Consistency Conventions table |
| 8 | Low-Medium | Redis requirement not traced/justified against local-only framing | PRD §6.1, §9 | Stack table, Deployment |
| 9 | Low | FR-12 has no explicit frontend component home | PRD FR-12 | Source Tree, Capability map |
| 10 | Low | "Universal, not new-project-only" caveat dropped from AD-3 | addendum control-tower note, PRD OQ-5 | AD-3 |
