# Adversarial Review — Claude Wrapper PRD

**Target:** `/Users/fayedraza/claude-wrapper/_bmad-output/planning-artifacts/prds/prd-claude-wrapper-2026-08-30/prd.md`
**Lens:** Adversarial (bmad-review)
**Content class:** docs (product requirements document)
**Background consulted (not review targets):** `addendum.md`, `docs/claude_wrapper_system_architecture_and_plan.md`

---

## Findings

```json
[
  {
    "lens": "adversarial",
    "location": "§1 Vision / §2.1 JTBD #2 vs §9 Constraints and Guardrails (Cost)",
    "trigger_condition": "The Vision and JTBD #2 promise the user is 'not... surprised by the bill,' but §9 explicitly states v1 has 'no hard token/dollar cap and no warn-before-exceed threshold' — cost control depends entirely on the user noticing live telemetry and manually invoking Stop & Undo.",
    "guard_snippet": "Reword the JTBD/Vision claim to 'visibility into cost as it happens' rather than 'not surprised,' or add a v1 warn-before-exceed threshold FR so the guardrail actually matches the promise.",
    "potential_consequence": "A user who doesn't watch telemetry in real time can still be bill-surprised on launch, directly contradicting the product's own headline promise."
  },
  {
    "lens": "adversarial",
    "location": "§7 Success Metrics (SM-1 through SM-5), general",
    "trigger_condition": "Every success metric requires cross-run and/or cross-user aggregate measurement (token-reduction baselines, retention cohorts, cancellation ratios, approval-time distributions), but no FR in §4 specifies any mechanism to collect, store, or export usage data beyond a single local Post-Run Audit view for that one run.",
    "guard_snippet": "Add an explicit FR (or NFR) defining a local analytics/telemetry collection mechanism, its opt-in/consent model, and where aggregated data lands — or mark §7 metrics as aspirational/post-v1 until that mechanism exists.",
    "potential_consequence": "None of the five success metrics can actually be computed against a shipped v1; the PRD's own measurement plan is unimplementable as scoped."
  },
  {
    "lens": "adversarial",
    "location": "§7 SM-3 (Weekly retention)",
    "trigger_condition": "SM-3 has no baseline cohort definition, no numeric target, no defined anchor for 'week 1' (signup? first run? repo init?), and doesn't specify whether a cancelled or failed run counts as 'running a task.' The product is also locally hosted per §6.1, so there is no described way to observe this metric without a phone-home mechanism that raises its own unaddressed privacy questions.",
    "guard_snippet": "Define cohort start event, task-completion criteria (must a run finish successfully to count?), a numeric target %, and how a locally-run tool reports this metric back to the team, including consent language.",
    "potential_consequence": "SM-3 as written can be reported as 'met' or 'missed' arbitrarily since there's no agreed definition of what's being counted."
  },
  {
    "lens": "adversarial",
    "location": "§7 SM-2 (Estimate accuracy)",
    "trigger_condition": "The target is 'estimates tight enough that users trust them enough to approve a run without second-guessing' — a subjective trust outcome with no numeric MAPE threshold and no defined proxy (survey? approval hesitation time?) for measuring 'trust.'",
    "guard_snippet": "Set a numeric mean-absolute-% target for token/time delta, and if trust itself matters, tie it to a measurable proxy (e.g., SM-5's approval time, or an explicit post-run rating prompt).",
    "potential_consequence": "SM-2 cannot be objectively validated or falsified — any estimate error can be rationalized as 'still trusted enough.'"
  },
  {
    "lens": "adversarial",
    "location": "§7 SM-5 (Time-to-first-approval)",
    "trigger_condition": "SM-5 states only that checkbox-style approval 'should make this fast, not a chore' — no target duration, threshold, or comparison baseline is given, unlike SM-1/SM-2 which at least name a metric shape.",
    "guard_snippet": "Add a concrete target (e.g., 'median approval time under N seconds for a checklist of typical size') so the metric can be graded pass/fail.",
    "potential_consequence": "SM-5 is purely descriptive and can never be reported as met or missed, defeating its purpose as a secondary success metric."
  },
  {
    "lens": "adversarial",
    "location": "§7 SM-1 (Token reduction) vs §11 Open Question #4",
    "trigger_condition": "SM-1 is the Primary #1 success metric, but its target ('meaningful reduction') is explicitly undefined per §11 Q4, and its baseline ('naive/unscoped baseline run — no context graph, full-context dump') isn't backed by any in-scope FR or toggle that would actually produce that comparison run.",
    "guard_snippet": "Either add an explicit v1 FR/dev-only mode that can run the naive baseline for comparison, or move SM-1's numeric target-setting to a pre-launch measurement spike and mark it provisional in §7 rather than presenting it as a committed Primary metric.",
    "potential_consequence": "The PRD's flagship metric ships without an agreed number to hit or a way to generate the comparison it's measured against, so 'success' on SM-1 is undecidable at launch."
  },
  {
    "lens": "adversarial",
    "location": "FR-4 Consequences (testable), §4.2",
    "trigger_condition": "The third consequence bullet states an agent whose task depends on a rejected item 'proceeds without that resource or is blocked/flagged' — an explicit either/or inside a section the document itself labels 'testable.' A test cannot fail this consequence since both branches are permitted.",
    "guard_snippet": "Resolve the `[NOTE FOR PM]` before treating FR-4 as implementation-ready: pick one behavior (re-plan flight path vs. proceed without resource vs. block) and state it as the single testable consequence.",
    "potential_consequence": "Downstream architecture/engineering can implement either behavior and both would 'pass' this FR, producing inconsistent behavior across agents or across implementers."
  },
  {
    "lens": "adversarial",
    "location": "FR-17 (§4.5) vs §10 Node telemetry contract vs §11 Open Question #3",
    "trigger_condition": "FR-17 requires the system to represent 'an agent in trouble, awaiting push-or-cancel' as a distinct state from a hard failure, but §10 states the node schema's status enum ('waiting_input', 'executing', 'completed', 'failed') conflates 'failed' and 'cancelled,' with no state for 'awaiting push-or-cancel.' §10's own list of FRs the node contract 'backs' (FR-12, FR-13, FR-14, FR-15, FR-18) omits FR-16 and FR-17 entirely, despite both depending on the same status/interrupt_state fields.",
    "guard_snippet": "Add the missing enum value (e.g., 'trouble') to the node schema and explicitly list FR-16/FR-17 among the FRs the contract backs in §10, resolving §11 Q3 before this reaches architecture.",
    "potential_consequence": "The UI cannot distinguish a recoverable, push-able agent from a terminally failed one using the documented contract, so FR-17's push-or-cancel UI has no data to key off of as specified."
  },
  {
    "lens": "adversarial",
    "location": "§3 Glossary ('Node') vs §10 Node telemetry contract vs FR-13/FR-16",
    "trigger_condition": "The Glossary defines 'Node' as a context-graph subtopic ('a subtopic unit of context... that an agent's context graph is divided into'), but §10's node schema and FR-16 ('rolls the node back to its pre-interrupt checkpoint state') use 'node' to mean a DAG execution unit/agent (one node = one subagent, with its own config/telemetry/checkpoint). The PRD never disambiguates which sense a given FR uses.",
    "guard_snippet": "Introduce two distinct terms (e.g., 'context node' for graph subtopics vs. 'execution node'/'agent node' for DAG units) and apply them consistently across FR-8/FR-9/FR-14 (context nodes) vs. FR-13/FR-16/§10 (execution nodes).",
    "potential_consequence": "Architecture and engineering could build a single unified 'node' data model conflating two different concepts, or misread which nodes a given FR's checkpoint/rollback logic applies to."
  },
  {
    "lens": "adversarial",
    "location": "FR-11 (§4.3) vs addendum.md 'New-project agent sequencing' vs §0",
    "trigger_condition": "FR-11 asserts control-tower sequencing 'applies uniformly on existing and new repos,' but the addendum — the actual discovery material this PRD is meant to have distilled — frames the control-tower model specifically under a 'New-project agent sequencing' heading and explicitly calls it 'distinct from the parallel-by-default execution implied elsewhere in the architecture doc.' §0 claims the PRD 'works backward from a finalized technical architecture,' but this tension between FR-11's uniformity claim and the architecture doc's implied parallel default is never reconciled.",
    "guard_snippet": "Either cite evidence that uniform sequencing was validated for existing-repo runs too, or scope FR-11 to new-repo runs only and add a separate (possibly parallel-by-default) requirement for existing-repo sequencing, matching the architecture doc's own framing.",
    "potential_consequence": "Architecture may implement uniform sequential gating for existing-repo runs, silently forfeiting parallelism the source architecture doc assumed was available, with no product decision on record that this tradeoff was intended."
  },
  {
    "lens": "adversarial",
    "location": "FR-10 (§4.3) input list",
    "trigger_condition": "FR-10 predicts token/time cost 'based on system prompt length, assigned workspace files, and anticipated tool round-trips' only — it does not account for HITL push/redirect loops (FR-17) or discarded work from Stop & Undo (FR-16/FR-22), which the PRD elsewhere treats as significant enough to warrant their own dedicated Post-Run Audit line item ('cancelled tokens').",
    "guard_snippet": "Add push-loop iterations and expected rework/interrupt frequency as inputs to the FR-10 estimator, or explicitly note them as an acknowledged source of estimate error feeding into SM-2.",
    "potential_consequence": "Estimates will systematically undershoot actuals on any run that hits a push-or-cancel interrupt, directly working against SM-2 (estimate accuracy) before implementation even starts."
  },
  {
    "lens": "adversarial",
    "location": "FR-6, FR-13, FR-14, FR-15, FR-19, FR-20, FR-21 — missing 'Consequences (testable)' blocks",
    "trigger_condition": "Roughly a third of the FRs (FR-6, FR-13, FR-14, FR-15, FR-19, FR-20, FR-21) lack the 'Consequences (testable)' subsection that every other FR carries, leaving them as bare feature descriptions with no falsifiable acceptance criteria — despite §0's claim that FRs are 'numbered' precisely so 'downstream artifacts (epics, tickets) have stable references.'",
    "guard_snippet": "Add explicit, falsifiable Consequences bullets to each of these FRs (e.g., for FR-14: 'the displayed flight path node the user sees updates within Ns of the backend actually entering that node').",
    "potential_consequence": "Epics/stories derived from these FRs will lack acceptance criteria, forcing engineers or QA to invent their own definition of done inconsistently across the same feature set."
  },
  {
    "lens": "adversarial",
    "location": "§12 Assumptions Index",
    "trigger_condition": "§12 states 'No inline [ASSUMPTION] tags remain unresolved... all raised during discovery... were resolved,' which reads as a clean-bill-of-health for the document, but the PRD still carries multiple unresolved markers of a different kind — `[NOTE FOR PM]` in FR-4, §6.2, and §9, plus four numbered items in §11 Open Questions — that are just as load-bearing as an unresolved assumption would be.",
    "guard_snippet": "Either broaden §12 to summarize all outstanding markers (NOTE FOR PM, OPEN QUESTION, ASSUMPTION) with their resolution status, or rename the section to scope it explicitly to '[ASSUMPTION] tags only' so it isn't read as a general readiness statement.",
    "potential_consequence": "A reader skimming §12 in isolation could conclude the PRD has no open issues, missing the FR-4 fork, the §9 security note, and four open questions that materially affect scope and implementation."
  },
  {
    "lens": "adversarial",
    "location": "UJ-3 (§2.3) and FR-5 (§4.2) — shared-resource revoke",
    "trigger_condition": "Both UJ-3 and FR-5 describe revoking a resource from a single agent's grant, but permission grants are itemized per-agent (FR-4: 'itemized per agent... not a single flattened list'), so the same file or MCP server could be granted to multiple concurrently running agents. Neither UJ-3 nor FR-5 states whether a revoke cuts off only the one agent/grant instance or the resource for every agent currently holding it.",
    "guard_snippet": "Add a consequence bullet to FR-5 clarifying revoke scope: per-grant-instance vs. per-resource-across-all-agents, and what happens to other agents still using that resource when a shared grant is revoked.",
    "potential_consequence": "An implementer could revoke a shared MCP server for one agent while a second agent silently continues using it, defeating the immediate-cutoff guarantee FR-5 promises."
  },
  {
    "lens": "adversarial",
    "location": "§1 Vision, opening sentence",
    "trigger_condition": "The Vision's foundational claim — 'Claude Wrapper replaces the terminal — not the IDE' — is asserted with no supporting rationale for why a developer would stop using a terminal for git operations, test runners, debugging, or ad hoc scripts, none of which any JTBD (§2.1) or FR (§4) addresses.",
    "guard_snippet": "Either narrow the claim (e.g., 'replaces the terminal for agent orchestration and hand-off, not for general shell use') or add a JTBD/non-goal statement scoping exactly which terminal use cases are and aren't covered.",
    "potential_consequence": "The product's headline positioning overpromises scope that no requirement actually delivers, setting an expectation (full terminal replacement) the FR list doesn't support and inviting early user disappointment or scope-creep pressure."
  },
  {
    "lens": "adversarial",
    "location": "FR-7 (§4.3) Task decomposition",
    "trigger_condition": "FR-7 requires the system to determine 'how many agents/subagents are needed' but sets no bound, sanity check, or quality criterion on that count — nothing distinguishes a correct decomposition from a degenerate one (e.g., one monolithic agent for a multi-part task, or excessive over-decomposition of a trivial one).",
    "guard_snippet": "Add a testable consequence to FR-7 defining at least a coarse quality bar (e.g., decomposition granularity bounded by task complexity signals, or a re-planning trigger if a single agent's estimated scope exceeds a threshold).",
    "potential_consequence": "The core differentiator of the product (per §4.3's own description) has no acceptance criterion of its own; poor decomposition can only be caught indirectly and after the fact via SM-1/SM-C1, not prevented or tested at the FR level."
  }
]
```

## Markdown Summary — Adversarial Lens (16 findings)

### 1. "Not surprised by the bill" vs. no cost cap
**Location:** §1 Vision / §2.1 JTBD #2 vs §9 Constraints (Cost)
The Vision and JTBD #2 promise the user is never bill-surprised, but §9 admits v1 has no hard cap and no warn-before-exceed threshold — the guardrail is manual vigilance, not the automated safety the Vision implies. **Fix:** reword the promise to match reality, or add a v1 warning threshold.

### 2. Success metrics have no measurement mechanism
**Location:** §7, general
Every metric (SM-1 through SM-5) needs cross-run/cross-user aggregate data, but no FR specifies any telemetry/analytics collection, and the product is locally hosted (§6.1) with no described phone-home path. **Fix:** add an explicit collection/consent FR or mark §7 as post-v1 aspirational.

### 3. SM-3 (weekly retention) undefined on every axis
**Location:** §7 SM-3
No cohort start event, no numeric target, no definition of what counts as "running a task," and no path to observe this from a local install. **Fix:** define all four before treating this as a committed metric.

### 4. SM-2 (estimate accuracy) conflates a number with a feeling
**Location:** §7 SM-2
Target is "tight enough that users trust them" — no MAPE threshold, no defined trust proxy. **Fix:** set a numeric delta target; if trust matters, tie it to a measurable proxy.

### 5. SM-5 (time-to-first-approval) has no target at all
**Location:** §7 SM-5
Purely descriptive ("should make this fast"), un-gradable as written. **Fix:** add a concrete duration target.

### 6. SM-1 (flagship metric) has no target and no baseline mechanism
**Location:** §7 SM-1 vs §11 Q4
"Meaningful reduction" is undefined per the PRD's own open question, and the naive-baseline comparison run has no FR building it. **Fix:** add a baseline-generation mode or mark SM-1 provisional pending a measurement spike.

### 7. FR-4's "testable" consequence contains an unresolved either/or
**Location:** FR-4, §4.2
"Proceeds without that resource or is blocked/flagged" can't fail a test since both outcomes pass. **Fix:** resolve the `[NOTE FOR PM]` and pick one behavior.

### 8. FR-17's required state has no home in the node schema
**Location:** FR-17 vs §10 vs §11 Q3
The schema's status enum can't represent "trouble, awaiting push-or-cancel," and §10's FR-backing list omits FR-16/FR-17 despite depending on the same fields. **Fix:** add the enum value and update the backing list.

### 9. "Node" means two different things in the same document
**Location:** §3 Glossary vs §10/FR-13/FR-16
Glossary: node = context-graph subtopic. §10/FR-16: node = an agent/DAG execution unit with its own checkpoint. Never disambiguated. **Fix:** split into two terms.

### 10. FR-11's uniformity claim contradicts its own source material
**Location:** FR-11 vs addendum.md
The addendum frames control-tower sequencing as a new-project concern, explicitly distinct from the architecture doc's implied parallel default — FR-11 asserts uniform application without reconciling this. **Fix:** scope FR-11 or add a parallel-path requirement for existing repos.

### 11. FR-10's cost model omits the variance the rest of the PRD cares about
**Location:** FR-10, §4.3
Estimator inputs don't include push loops or discarded work, even though FR-16/17/22 treat those as material enough to need a dedicated audit line. **Fix:** add them as estimator inputs or acknowledge the gap.

### 12. A third of the FRs have no acceptance criteria
**Location:** FR-6, FR-13, FR-14, FR-15, FR-19, FR-20, FR-21
Missing "Consequences (testable)" blocks that every other FR carries, despite §0's claim that FRs anchor downstream epics/tickets. **Fix:** add falsifiable consequences to each.

### 13. §12's clean bill of health is narrower than it reads
**Location:** §12 Assumptions Index
Claims no unresolved items, but scopes that only to `[ASSUMPTION]` tags — ignoring live `[NOTE FOR PM]` and `[OPEN QUESTION]` markers elsewhere in the same document. **Fix:** broaden the section or rename it to scope the claim accurately.

### 14. Shared-resource revoke scope is undefined
**Location:** UJ-3, FR-5
Grants are itemized per-agent, so a resource could be shared across agents — neither UJ-3 nor FR-5 says whether revoke cuts off one grant instance or the resource for everyone holding it. **Fix:** add an explicit consequence clarifying scope.

### 15. "Replaces the terminal" is unsupported by any requirement
**Location:** §1 Vision
No JTBD or FR addresses git, test runners, debugging, or ad hoc scripts — the use cases that actually keep developers in a terminal. **Fix:** narrow the claim or explicitly scope it.

### 16. Task decomposition has no quality bar
**Location:** FR-7, §4.3
Nothing in FR-7 bounds or validates "how many agents are needed" — the product's stated core differentiator has no acceptance criterion of its own. **Fix:** add a coarse quality/bound check as a testable consequence.

---

*Context consulted but not reviewed: `addendum.md` (implementation/UX depth intentionally out of PRD scope — not flagged as a gap here) and `docs/claude_wrapper_system_architecture_and_plan.md` (source architecture, used to check consistency of PRD claims against it).*
