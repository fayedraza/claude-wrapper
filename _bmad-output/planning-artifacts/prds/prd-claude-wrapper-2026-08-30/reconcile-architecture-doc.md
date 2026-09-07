# Reconciliation: Source Architecture Doc vs. Drafted PRD

Source: `docs/claude_wrapper_system_architecture_and_plan.md`
Target: `_bmad-output/planning-artifacts/prds/prd-claude-wrapper-2026-08-30/prd.md`
Also checked: `addendum.md`, both referenced diagrams.

Overall: the PRD is a faithful, well-structured translation of the source doc's 7 Key Platform Features and the Pydantic/node schemas, and it correctly treats the 5-phase roadmap as build sequencing rather than a scope cut (§6.1, explicit note). The gaps below are real but graded — most are omissions of a named capability/nuance rather than outright contradictions.

---

## Gap 1 (highest severity): FastMCP Synthesizer / "Dynamic Tools" has no dedicated Feature or FR

**Source says:** The backend architecture is explicitly three pillars — "The Brain," "The Engine," and **"Dynamic Tools (FastMCP Synthesizer): Identifies missing external API capabilities and generates fully compliant Model Context Protocol bridges on-the-fly, mounting them locally for isolated agent access"** (§6). This is reinforced by the Technology Stack table's "Tool Integration" row (§7: "FastMCP and Pydantic for rapid, on-the-fly wrapping of external APIs... connect via stdio... or SSE"), by Roadmap Phase 2 being entirely dedicated to it ("Build the prompt and execution pipeline that takes an API URL/spec, writes a FastMCP script using type hints, and launches it over stdio"), and by the technical architecture diagram, which shows it as its own labeled box fed by an explicit "Missing APIs identified" arrow from The Engine.

**PRD says:** No Feature section (§4.1–4.7) or FR describes the *generation* of a FastMCP bridge as a product capability — trigger condition, inputs, output, or user visibility. It surfaces only as: (a) a Glossary term ("FastMCP bridge — a dynamically generated, on-the-fly Model Context Protocol server...") that assumes the capability rather than specifying it, and (b) the phrase "MCP servers (FastMCP-generated vs. pre-provided)" inside FR-13 (DAG rendering), which distinguishes the two kinds of server without saying how or when the generated kind comes to exist.

**Why it matters:** This is one of three named backend pillars in the source doc, not a minor mechanism — it's the difference between "the platform only orchestrates MCP servers I already have" and "the platform writes and runs new code against an external API on my behalf when it decides one is missing." That has real product and security implications the PRD doesn't resolve: does a newly-synthesized bridge for an arbitrary external API get the same Pre-Flight Permission review as an existing MCP server (FR-4), or does it bypass that gate because it doesn't exist yet at Pre-Flight time? The PRD's own Security section (§9) states Pre-Flight approve/revoke "is the v1 security boundary," but never says whether bridge synthesis happens before or after that boundary is drawn. This should be its own FR (or at minimum an Open Question in §11) rather than an assumed Glossary term.

**Related sub-point — isolation language dropped:** Source says generated bridges are "mounted locally for **isolated agent access**." PRD's Security section instead states "Spawned FastMCP processes run with no additional OS-level sandboxing beyond what file/MCP access the user has explicitly granted" — plausibly consistent (source's "isolated" may mean logically-scoped-per-agent, not OS-sandboxed), but the PRD doesn't acknowledge or reconcile the source's isolation claim at all, so a reader can't tell if this is the same guarantee restated or a walked-back one.

---

## Gap 2: MCP Inspector debugging capability (Roadmap Phase 2) dropped entirely

**Source says:** Phase 2 of the Development Roadmap (§8) includes a specific, named developer-facing capability: "**Note: Developers can interactively test and debug these generated tools prior to execution using the built-in MCP Inspector by running `uv run mcp dev server.py` or `fastmcp dev server.py`.**"

**PRD says:** Nothing. It doesn't appear in §4 (Features/FRs), §6 (MVP Scope — which explicitly discusses the roadmap and says "nothing in that roadmap is deferred past v1"), §10 (Developer Products), or in `addendum.md` (which does capture other mechanism-level detail worth pushing to architecture, e.g. the flight-path routing algorithm and control-tower sequencing, but not this).

**Why it matters:** This is a concrete, named testability/debugging affordance tied directly to Gap 1's FastMCP synthesis capability — if the platform is going to write and run generated code against external APIs, a way to test/debug that generated code before it executes against a real agent is a meaningful trust/safety feature, not incidental roadmap trivia. Since §6.1 asserts nothing from the roadmap is deferred, this capability is implicitly still in scope — but silently, with no FR or addendum trail for the architecture stage to pick up. It should at least be captured in `addendum.md` alongside the other Phase-2-adjacent mechanism detail, if not promoted to an FR.

---

## Gap 3: Claude's live reasoning scratchpad exposure is not named as a capability

**Source says:** §5 (Frontend UI) describes "**The Input Drawer**: An interactive slide-over component that binds directly to the `live_stream` data of the active node. It **exposes Claude's real-time reasoning scratchpad** alongside dedicated user input fields, allowing users to inject context or decisions directly into the agent's working memory." This is echoed in User Flow stage C: real-time token tracking and flight path visualized "across Claude's 'thinking' process," and in the node schema (§6.1) via the `live_stream.thinking` field.

**PRD says:** FR-18 (In-UI question response) captures the *input* half (user can answer a blocking question in free text) but not the *output* half — that the user can watch Claude's live reasoning/thinking text stream, not just its status or its final question. §10 lists `live_stream` as one of six top-level node-schema fields backing FR-12/13/14/15/18 but doesn't enumerate its sub-fields (`thinking`, `latest_message`, `requires_user_input`, `interrupt_state`), so the "watch the reasoning trace live" capability is present only implicitly, one schema-field name removed from being named at all.

**Why it matters:** "See the agent's live reasoning, not just its status" is a distinct trust/observability capability (arguably central to the doc's "safety and observability of a visual IDE" framing — see Gap 5) from "answer its question when blocked." A reader of the PRD alone would not know this scratchpad-visibility feature exists. Low-cost fix: either fold it into FR-18's description or the Vision, or add a line to §10's node telemetry contract naming the `live_stream` sub-fields.

*Minor related point:* the source's **Subagent Resource Inspector** (§5) — visualizing "the distribution of Claude context window usage" per subagent, not just token counts — is also not explicitly distinguished from token telemetry (FR-15) in the PRD. Likely reasonable to treat as covered by FR-13/FR-15 together, but flagged for completeness.

---

## Gap 4: Question-button scope — PRD silently resolves a source-internal ambiguity

**Source says:** Two different scopes for the same UI element. The Key Platform Features table (§2, Subagent Task Management row) says the question button is "**interactive... that will only appear for subagent questions**" — i.e., scoped to subagents specifically, implying the orchestrator doesn't get one. But User Flow stage D says the button "appears whenever **an agent** requires specific user input to proceed" — generic, not subagent-limited. The source doc itself doesn't resolve this.

**PRD says:** FR-12 sides with the broader reading — "a question button visible only when **that agent** has an open question" — applied uniformly to "the main orchestrator and every subagent" in the same FR's opening clause.

**Why it matters:** Not a PRD error exactly (it had to pick one of two source-internal readings), but the PRD doesn't flag that it made a choice here, so downstream readers may not realize the source doc was ambiguous on whether the orchestrator itself can ever be the one asking a question. Worth a one-line note or Open Question if the distinction (orchestrator vs. subagent-only questions) turns out to matter at the architecture stage.

---

## Gap 5 (tone/framing, lowest severity): Vision reframes rather than restates the source's "visual IDE" analogy

**Source says (opening framing, §1 preamble):** the platform combines "the dynamic planning of autonomous AI with the safety and observability of **a visual Integrated Development Environment (IDE)**." This is an analogy — the platform behaves *like* a visual IDE for agent orchestration (for its safety/observability qualities), not a claim about replacing anything.

**PRD says (Vision, §1):** "Claude Wrapper replaces **the terminal — not the IDE**... The IDE remains the source of truth for the resulting files and commands — Claude Wrapper owns the agent conversation, not the codebase." This is reinforced as a formal Non-Goal (§5): "Claude Wrapper does not replace the IDE."

**Why it matters / why it's likely fine:** This isn't a contradiction — the source never claims to replace the IDE either. But the PRD's framing is materially more assertive and specific (a firm positioning statement with a stated non-goal) than the source's loose analogy, and the safety/observability *quality* the source attributes to "a visual IDE" is redistributed across the PRD's Vision narrative (approval gates, live streaming, Stop & Undo, Post-Run Audit) rather than named as a single unifying idea. This is almost certainly intentional product positioning added during PM discovery (plausible given §2.2's explicit "companion to the IDE" non-user framing), not a drafting error — flagged per the task's instruction to check this specific example, not because it looks like a mistake.

---

## Confirmed non-gaps (checked, no issue found)

- **All 7 Key Platform Features** (§2 table) map 1:1 to PRD §4.1–4.7 with no capability silently dropped.
- **Pydantic `SettingAction`/`SettingsRouterOutput` schema (§6.2):** all 8 `target_category` literals, the 3 `action` literals, and `file_path`/`content`/`user_summary` are reproduced correctly in FR-1 and PRD §10.
- **Node telemetry schema (§6.1):** PRD §10 correctly uses the canonical `status` enum (`waiting_input`, `executing`, `completed`, `failed`) from §6.1's own footnote, rather than the inconsistent `awaiting_input` term used in source §5's prose — a correct resolution of a source-internal inconsistency, not an error. PRD §10/§11 also proactively flags a real gap in the *source* schema itself (no distinct "cancelled" status value, conflated with "failed") as an Open Question — this is the PRD doing reconciliation work the source doc needed, not omitting anything.
- **5-phase Development Roadmap (§8):** PRD §6.1 explicitly and correctly treats it as build sequencing, not a scope cut, and states nothing is deferred past v1.
- **Meta-Planner cost basis:** "system prompt length, assigned workspace files, and anticipated tool round-trips" is reproduced verbatim in FR-10.
- **Technology Stack table (§7):** Frontend (Next.js/React Flow), backend (FastAPI/LangGraph), and telemetry stack (SQLite/Redis, WebSockets/SSE) are appropriately treated as implementation detail and correctly excluded from the FR-level PRD, surfacing only in §10's "Language/runtime targets" — a reasonable capability-vs-implementation split, not a drop. (Prefect as a named backend alternative is the one line item omitted from §10, but this is implementation detail appropriately left out.)
- **Stop & Undo / cancelled-tokens accounting:** PRD FR-16/FR-22 goes further than the source (explicit "cancelled tokens" line-item tracking) without contradicting it.
