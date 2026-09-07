# Reconciliation: UX Design vs. Architecture/PRD Backend Contracts

**Scope:** DESIGN.md, EXPERIENCE.md, and all 9 mockups in `ux-designs/ux-claude-wrapper-2026-08-30/` checked against `ARCHITECTURE-SPINE.md` (AD-1–AD-9) and PRD §10 (`SettingAction`/`SettingsRouterOutput`, execution-node telemetry contract).

**Legend:** 🔴 GENUINE INCOMPATIBILITY (would break or mislead at integration) · 🟢 FINE, NO ACTION (cosmetic/presentation choice, backend-compatible) · 🟡 GAP/NOTEWORTHY (not a mismatch per se, but needs attention)

---

## 1. Settings category vocabulary vs. `target_category` enum

Real enum (PRD §10 / FR-1): `team_instructions | local_instructions | settings.json | settings.local.json | rule | skill | command | agent` (exactly 8 values).

**🔴 GENUINE — `key-settings.html`, second proposal card, category badge.**
The `.claude/settings.json` proposal renders `<span class="proposal-badge category">config</span>`. `"config"` is not one of the 8 `target_category` values — the real value for that file is `settings.json`. An engineer wiring this card to the live `SettingAction.target_category` field and literally reusing the mockup's string will render nothing (or a blank/undefined badge) for every `settings.json`/`settings.local.json` change, since the mock never demonstrates those two literal enum strings. The first card (`rule`) is correct — it uses the exact enum value.
→ Fix: category badge text should render the literal `target_category` value (or an explicit, documented display-name mapping table covering all 8 values — none exists today).

**🔴 GENUINE — `EXPERIENCE.md § Component Patterns`, "Proposed-change card" row.**
> "Target path + category chip (rule / agent persona / MCP grant / etc.) + action badge..."

Two problems, and this is the spine document that "wins on conflict," so it's higher-severity than the mockup:
- `"agent persona"` is not a `target_category` value; the real value is `agent`. (Minor — plausibly just a friendlier gloss on `agent`.)
- `"MCP grant"` is not a `target_category` value **at all**, and MCP/file grants are not in the Settings Router's domain in the first place — they belong to the Permission Manager (FR-4–FR-6, `backend/gateway/` + `frontend/components/permission-manager/`), a structurally separate feature from Settings (FR-1–FR-3, `backend/brain/settings_router/`). Listing "MCP grant" as an example Settings proposed-change category conflates two different backend subsystems and could lead a builder to expect the Settings Router to emit `target_category: "mcp_grant"` or similar, which does not and will not exist.
→ Fix: EXPERIENCE.md's example list should read something like `rule / agent / settings.json / etc.` (real enum values), and should not cite MCP grants as a Settings category example.

**🟢 FINE — `key-settings.html`, "Currently configured" list `config-kind` chips (`rule` / `agent` / `mcp`).**
This is a read-only summary view (FR-3: "full, current summary of everything configured in `.claude/` (rules, permissions, subagent personas, commands, skills)"), not a rendering of a `SettingAction.target_category` value — FR-3's scope explicitly includes permissions alongside rules/personas, so grouping an MCP grant under a `mcp` display chip here is a legitimate summary-view label, not a mis-rendered enum. No action needed.

**🟡 NOTEWORTHY — missing `revoke` action-badge styling.**
`key-settings.html`'s CSS only defines `.action-create` and `.action-update`; FR-1 explicitly says the Settings Router can also "revoke" a target. The mockup never demonstrates a revoke proposal card. Not a backend mismatch — just an incomplete mock — but flag so a revoke-flavored proposal card gets a defined visual before build.

---

## 2. Node status enum (AD-5)

Real enum: `waiting_input | executing | trouble | completed | cancelled | failed` (exactly 6 values, this spelling).

**🟢 FINE — every surface checked uses exactly these 6 values, correctly spelled, no extras, none missing:**
- DESIGN.md's color tokens (`status-waiting-input`, `-executing`, `-trouble`, `-completed`, `-cancelled`, `-failed`) — 6/6, both light and dark.
- EXPERIENCE.md § State Patterns — states the enum verbatim and correctly marks `trouble` non-terminal / the other three terminal.
- `key-task-list.html` — legend and every `status-chip` (`st-executing`, `st-completed`, `st-trouble`, `st-waiting` mapped to `waiting_input`) use the 6 values; the CSS variable name `--status-waiting` is an internal shorthand, but the rendered text is `waiting_input` verbatim.
- `key-dag-canvas.html` — legend (6/6) and node classes (`st-executing/completed/trouble/waiting/cancelled`) match; `failed` appears in the legend but no node demos it (acceptable, not every state needs a live example).
- `key-node-inspector.html` (`trouble`) and `key-question-response.html` (`waiting_input`) — badge text is the literal enum value plus a plain-language suffix ("trouble — needs a decision", "waiting on your input" — copy variance is fine per Accessibility Floor, which only requires a co-located text label, not the raw enum string verbatim in body copy).
- `key-post-run-audit.html` / `key-flight-path-full.html` — reduced legends (`completed` / `trouble (recovered)` / `cancelled`) are explicitly scoped to terminal/historical framing per EXPERIENCE.md's own instruction ("reduced legend scoped to terminal states only"); this is a deliberate, documented UI reduction, not a schema drift — no action needed.

No incompatibility found on this axis.

---

## 3. Node data model — rollup vs. stored (AD-2)

AD-2: `Node` (context node) is the sole stored unit, carrying both context-graph and execution fields. "One execution node per agent" is a **computed rollup**, never separately stored.

**🟢 FINE — Task List (`key-task-list.html`) correctly presents agent-level rows as an aggregate/summary** — one row per agent, aggregate status + summed tokens + one-line summary — exactly the shape of AD-2's rollup view. Nothing in the row implies a separately-stored "agent execution record."

**🟢 FINE — `key-flight-path-full.html` (Full Flight Path Replay) correctly surfaces context-node-level granularity as the real underlying data** — `auth_scaffold_worker` is broken into its 6 actual context nodes, each with its own token figure, sequence badge, and trouble/resumed annotation, nested under the agent-level box; the sidebar's per-agent token total is explicitly built from a `ctx-breakdown` list that sums to the agent figure. This is the best-aligned artifact in the set relative to AD-2 — it demonstrates the real stored granularity (context nodes) feeding a computed agent-level total, matching AD-2's rollup language almost exactly.

**🟡 NOTEWORTHY — `key-dag-canvas.html`'s live "Flight path" panel shows only agent-level boxes and labels the line between them "active route" / "Flight path."** Per the PRD Glossary and AD-7, "flight path" is specifically the route through **context nodes within one agent's context graph** (a constrained search per AD-7), which is a different backend concept from the **inter-agent dependency edges** the orchestrator sequences by (AD-3). The live canvas's single connecting line (Orchestrator → backend_planner → auth_scaffold_worker) visually reads as "the flight path," but is actually rendering AD-3 dependency/dispatch order, not AD-7's per-agent context-node route (which, per the mocks, is only ever shown post-run in the Replay screen). This isn't a hard break — DESIGN.md/EXPERIENCE.md never mandate live context-node display, and deferring that detail to Replay is a legitimate, deliberate simplification for live glanceability (consistent with EXPERIENCE.md's Replay-only "per-context-node token figures nested under each agent-level node" instruction). But the identical label "Flight path" is used for two different backend data sources (AD-3 edges live vs. AD-7 route in Replay), which risks an implementer wiring the live canvas's connector lines to the wrong endpoint. Recommend EXPERIENCE.md clarify that the live DAG Canvas's connecting lines render dependency/sequencing order (AD-3), while "flight path" in the FR-20/AD-7 sense is context-node-level and only made visually explicit in Replay.

---

## 4. `live_stream` fields (`thinking`, `latest_message`, `requires_user_input`, `interrupt_state`)

**🟢 FINE — Node Inspector (`key-node-inspector.html`) and Question-Response (`key-question-response.html`) both render a single "Reasoning" block (`thinking-block` → `live_stream.thinking`) and, in the `waiting_input` case, a single "Question" card (→ `live_stream.latest_message` / `requires_user_input`).** Neither mock assumes a richer chat-message-history array, multiple pending questions, or any field not in the real `live_stream` shape. The UI presents one current thinking snippet and (when applicable) one current question — this matches a flat, single-current-value field shape, not a list/array the backend doesn't provide. `interrupt_state` isn't rendered as a distinct visible value anywhere, but nothing implies it needs to be — the drawer's chosen framing (`trouble` vs `waiting_input`) is already keyed off `status`, which is the correct AD-5-sanctioned trigger; `interrupt_state` can remain an internal/backend-only field. No incompatibility.

---

## 5. Trouble delivery channel (AD-5)

AD-5: `trouble` is delivered as an ordinary node-status update on the telemetry stream, not the `{error_code, message, node_id}` error envelope (reserved for `failed`/terminal-adjacent conditions).

**🟢 FINE — `key-node-inspector.html` treats `trouble` purely as a status-driven UI state.** The drawer's accent border, status badge, and push/cancel decision UI are all keyed off the same `status-badge`/CSS-class mechanism used for every other status value; nothing in the mock or in EXPERIENCE.md's Interaction Primitives implies `trouble` is triggered by a separate error/exception event, an error toast, or any handling distinct from a normal status-stream update. No incompatibility.

---

## 6. Telemetry / FR-26 UX gap

**🟡 CONFIRMED REAL GAP.** Checked `key-settings.html` in full — the "Add a rule or preference" section and the "Currently configured" list (rule / agent / mcp chips) contain no opt-in telemetry toggle, no privacy/data-sharing section, and no view of previously-collected telemetry data. EXPERIENCE.md's own Open Items section already flags this ("Usage Telemetry (FR-26) opt-in UX surface... not discussed or mocked this session") — this audit corroborates that the gap is real and nothing elsewhere accidentally covers it.
Per FR-26's PRD text ("User can opt in, from Settings (FR-3)..."), the natural location is a new section inside the Settings drawer — likely a third section after "Add a rule/preference" and "Currently configured," e.g. "Usage & Privacy," with an opt-in toggle and (optionally) a summary of what's been shared, consistent with the `not file contents/prompts/reasoning` allow-list AD-4 defines. This needs a mock before build.

---

## 7. Cancelled-tokens accounting (FR-22)

**🟢 FINE — `key-post-run-audit.html` structurally, not just visually, separates cancelled tokens.** Evidence:
- A dedicated `cancelled-chip` in the summary strip labeled "Cancelled tokens: 6.4k" with a note "Not counted in the totals above."
- A separate `.cancelled-card` section ("Cancelled work," subtitled "excluded from totals above") with its own figures (elapsed before cancel, tokens spent, est. if completed) and an explicit `not-counted-badge` ("Not counted toward completed-work totals").
- The main metrics table's total row is explicitly labeled "Total (completed work)" (49.8k) and does **not** include the cancelled agent's 6.4k — confirmed by arithmetic: 4.3k + 9.8k + 27.3k + 8.4k = 49.8k, cancelled 6.4k excluded.
- `key-flight-path-full.html`'s sidebar mirrors this: the cancelled agent's row shows "spent, not counted" with a `not-counted-pill`, and "Total (completed work)" again excludes it.

This is a genuinely separate line item/section in both artifacts, not a shared total with visual de-emphasis. No incompatibility with FR-22.

---

## 8. Permission revoke scope (FR-5)

**🟢 FINE — EXPERIENCE.md's Interaction Primitives states the multi-agent scope correctly:**
> "revoke — Permission Manager, at any time including mid-run: cuts off **every agent currently using the revoked resource** immediately, same abort/cleanup path as stop (FR-5)."

This matches FR-5's consequence text verbatim in substance ("every agent currently using it is cut off immediately, not just the one the user was looking at when they revoked — a shared grant is revoked for the whole run, not per grant-instance"). UJ-3's Key Flow also states it correctly ("if an agent is actively mid-run using that resource, it is cut off immediately"). No mockup exists for the Permission Manager screen itself (explicitly listed as an Open Item / not one of the 9 rendered screens), so there's no visual artifact to check further — but the behavioral spec that does exist is correct.

---

## 9. Other findings

**🟡 NOTEWORTHY — PRD Glossary/FR-13 language is itself stale relative to AD-2, and the UX correctly follows the newer Architecture spine, not the older PRD wording.** The PRD Glossary defines "Execution node... One execution node per agent" as if it were a real stored unit, and FR-13's consequence text says "every spawned subagent as its own execution node" — both predate AD-2's correction (execution-per-agent is a rollup, not stored). The UX design (Task List = rollup, Replay = real context-node granularity) actually follows AD-2 correctly rather than the stale PRD phrasing. Flagging only so nobody re-reads the PRD literally and reintroduces a separate "execution node" table at build time — the Architecture spine already resolved this and the UX is consistent with the resolution.

**🟢 FINE — `node_id` slug naming.** All mockups use human-readable snake_case slugs (`auth_scaffold_worker`, `backend_planner`, `token_refresh_worker`, `jwt_test_writer`) consistent with the Consistency Conventions table ("agent/subagent `node_id`s are human-readable slugs... never opaque UUIDs").

**🟢 FINE — Timestamps/run IDs.** No mockup renders a raw timestamp format that would conflict with "ISO 8601 UTC everywhere" — all displayed times are pre-formatted relative/duration strings (e.g., "41 minutes ago," "6m 12s"), which is expected client-side formatting of an ISO 8601 source value, not a schema conflict.

**🟡 NOTEWORTHY — Question-Response's monospace answer input.** (Design-system self-consistency issue, not a backend contract issue, noted for completeness only.) `key-question-response.html` styles the free-text answer textarea and its "Your response:" label in the monospace font family, explicitly for a "terminal-style" feel. DESIGN.md's own Do's/Don'ts table says monospace is reserved strictly for literal file paths/`.env`/config filenames and should never be used for anything else, including summary prose — the user's free-text answer is prose, not a literal path. This doesn't affect backend compatibility (no schema implication either way) but is an internal DESIGN.md-vs-mockup inconsistency worth a design pass.

---

## Summary Table

| # | Check | Verdict | Severity |
|---|---|---|---|
| 1a | Settings mockup `"config"` badge ≠ `settings.json` | 🔴 Genuine | Would break literal reuse |
| 1b | EXPERIENCE.md "MCP grant" as a Settings category example | 🔴 Genuine | Spine-level, higher severity |
| 1c | Settings mockup "Currently configured" `mcp` chip | 🟢 Fine | — |
| 2 | Node status enum, all surfaces | 🟢 Fine | — |
| 3a | Task List as rollup | 🟢 Fine | — |
| 3b | Flight Path Full Replay as real context-node granularity | 🟢 Fine | — |
| 3c | Live DAG Canvas "Flight path" label ambiguity (AD-3 vs AD-7 data) | 🟡 Noteworthy | Clarify before wiring |
| 4 | `live_stream` field shapes | 🟢 Fine | — |
| 5 | Trouble delivery channel | 🟢 Fine | — |
| 6 | FR-26 telemetry UX gap | 🟡 Confirmed gap | Needs a mock |
| 7 | Cancelled-tokens separation | 🟢 Fine | — |
| 8 | Permission revoke scope | 🟢 Fine | — |
| 9a | Stale PRD "execution node" language vs. UX (UX is correct) | 🟡 Context only | No UX fix needed |
| 9b | Missing "revoke" action badge style | 🟡 Noteworthy | Minor, add before build |
| 9c | Monospace answer input vs. DESIGN.md rule | 🟡 Noteworthy | Design-internal, not backend |

**Total genuine incompatibilities (🔴): 2** (both within Check 1 — Settings category vocabulary), both fixable by using the literal `target_category` enum values instead of invented/paraphrased labels.
