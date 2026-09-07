---
title: 'Story 1.3: View current .claude/ configuration'
type: 'feature'
created: '2026-09-07'
status: 'done'
review_loop_iteration: 0
context: []
baseline_commit: '9fb757e3af1e71cfa7bee8efeaaa8a98e2667ae4'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Story 1.2 only shows *proposed* changes before approval — a developer has no way to see what's already configured in `.claude/` without opening files by hand.

**Approach:** Add a read-only "Currently configured" section to the same Settings drawer, backed by a new endpoint that walks live on-disk `.claude/` state (rules, agent personas; permission grants shown only when present — none exist today, no schema yet).

## Boundaries & Constraints

**Always:** New `GET /api/settings/current`, strictly read-only — no `.claude/` writes anywhere in this story. Walk `.claude/rules/*.md` and `.claude/agents/*.md` fresh on every request, no caching (same "no cached snapshot" rule as Story 1.2). Check `settings.json`/`settings.local.json` for a `permissionGrants` key — namespaced deliberately distinct from Claude Code's own reserved `permissions` key (same file real Claude Code reads; this repo's own `.claude/settings.json` already has a `hooks` block Claude Code enforces) — show grant rows only if present; today it's always absent, so the section is correctly empty. "Currently configured" is the second section of the existing `SettingsDrawer.tsx`, fetched when the drawer opens and re-fetched after a successful Approve & Apply. Config-kind chip is `rule`/`agent`/`mcp` — a distinct, informal vocabulary from `target_category`, per the UX mock — render the literal kind, never an invented label. A different, simpler read-only row component than `ProposedChangeCard` (no actions, no content preview).

**Ask First:** None anticipated — permission-grant handling already confirmed with the human (show empty until Story 1.4 defines a real schema).

**Never:** Implement Story 1.4's actual grant creation/management. Invent a permission-grant schema beyond checking whether `permissionGrants` is present. Write to `.claude/` anywhere in this story.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Rules + agents exist | `.claude/rules/*.md`, `.claude/agents/*.md` present | One row per file: kind, one-line description, path | N/A |
| No permission grants (today's reality) | `settings.json` has no `permissionGrants` key | No grant rows shown | N/A |
| `.claude/` doesn't exist yet | fresh repo | Empty summary, friendly empty state | N/A |
| Fetch fails | backend/network error | Error message shown; rest of drawer still works | Error envelope surfaced |
| Change applied | Approve & Apply succeeds (Story 1.2 flow) | Summary re-fetches and reflects it without reopening the drawer | N/A |

</frozen-after-approval>

## Code Map

- `backend/brain/settings_router/summary.py` -- `get_current_configuration()`: walks `.claude/rules/`, `.claude/agents/`, checks `permissionGrants`
- `backend/brain/settings_router/models.py` -- add `ConfigSummaryItem`/`CurrentConfiguration` models
- `backend/gateway/main.py` -- add `GET /api/settings/current`
- `backend/pyproject.toml` -- add `pyyaml` (safe frontmatter parsing)
- `frontend/lib/settings-api.ts` -- add `getCurrentConfiguration()` + types
- `frontend/components/settings/ConfigSummaryItem.tsx` -- read-only row (kind chip + text + path)
- `frontend/components/settings/SettingsDrawer.tsx` -- "Currently configured" section, fetch on open + after apply

## Tasks & Acceptance

**Execution:**
- [x] `backend/pyproject.toml` -- add `pyyaml` -- safe frontmatter parsing for agent persona name/description
- [x] `backend/brain/settings_router/models.py` -- summary schema -- structured response contract
- [x] `backend/brain/settings_router/summary.py` -- classification logic per Boundaries -- core FR-3 behavior
- [x] `backend/gateway/main.py` -- `GET /api/settings/current` -- exposes the summary to the frontend
- [x] `backend/tests/brain/settings_router/test_summary.py` -- unit tests covering the I/O matrix
- [x] `frontend/lib/settings-api.ts` -- `getCurrentConfiguration()` + types -- wire client
- [x] `frontend/components/settings/ConfigSummaryItem.tsx` -- read-only row -- reusable across the summary list
- [x] `frontend/components/settings/SettingsDrawer.tsx` -- "Currently configured" section -- FR-3 UI, fetched on open + after apply

**Acceptance Criteria:**
- Given `.claude/` has rule and agent files, when I open Settings, then I see a "Currently configured" section listing each one with its kind, one-line description, and file path
- Given no permission grants are configured, when I open Settings, then the summary shows no grant rows — not an error
- Given I approve a proposed change, when it's applied, then the "Currently configured" summary reflects it without closing and reopening the drawer
- Given the summary fetch fails, when I open Settings, then I see an error message and the rest of the drawer still works

## Spec Change Log

## Design Notes

Agent persona "text": if the file has YAML frontmatter with `name`/`description` (matching this repo's own `SKILL.md` convention), show `"{name}: {description}"`; else fall back to filename + first content line. Rule "text": first non-empty content line, heading markup stripped. Neither is an external spec — both are reasonable heuristics since no schema for rule/agent file content exists in the docs.

**Note for Story 1.4:** permission grants have no on-disk schema anywhere in the docs (confirmed by investigation — PRD FR-4/5/6 and ARCHITECTURE-SPINE.md AD-6 describe only behavior, no field names). Story 1.3 deliberately does not invent one — it only checks for a `permissionGrants` key in `settings.json`/`settings.local.json` and shows nothing when absent (true today). **Story 1.4 owns defining the real schema** under that same `permissionGrants` key name (chosen specifically to not collide with Claude Code's own reserved `permissions` key). Once Story 1.4 writes real data there, Story 1.3's reader should pick it up automatically without needing to change — verify that assumption holds when 1.4 is implemented rather than taking it on faith.

Open question for 1.4, raised during 1.3 planning: flat per-file toggle, or per-action like Claude Code's own rules (`Read(pattern)`, `Edit(pattern)`, `Bash(pattern)`)? FR-4's "itemized checklist" doesn't settle it — worth confirming deliberately, not inheriting by default.

## Verification

**Commands:**
- `cd backend && uv run pytest tests/brain/ -v` -- expected: all pass
- `cd frontend && npm run build` -- expected: succeeds

## Suggested Review Order

**Summary reader (FR-3)**

- Entry point: walks live `.claude/` state fresh every call, never caches, never writes.
  [`summary.py:39`](../../backend/brain/settings_router/summary.py#L39)

- Deliberately uses `iterdir()` over `glob()` — a real bug found during review: `glob()` silently swallows `PermissionError` while scanning a directory, which would have misreported a genuine access failure as "nothing configured."
  [`summary.py:193`](../../backend/brain/settings_router/summary.py#L193)

- The resulting asymmetry (per-file failures degrade gracefully, directory-level failures propagate to the error envelope) is deliberate — documented after review flagged it as looking like an oversight.
  [`summary.py:207`](../../backend/brain/settings_router/summary.py#L207)

- Agent persona text: frontmatter `name`/`description` when present and both real strings, else filename + first line — both paths now strip heading markup consistently.
  [`summary.py:92`](../../backend/brain/settings_router/summary.py#L92)

- Frontmatter parsing never invents structure it can't verify — falls back cleanly on non-YAML, non-mapping, or pathological (`RecursionError`) content.
  [`summary.py:114`](../../backend/brain/settings_router/summary.py#L114)

- Permission grants: checks only for key presence, renders whatever generic text it finds — Story 1.4 owns the real schema, this never invents one.
  [`summary.py:143`](../../backend/brain/settings_router/summary.py#L143)

**API surface**

- `GET /api/settings/current` — the only new endpoint, strictly read-only.
  [`main.py:111`](../../backend/gateway/main.py#L111)

- Schema: `ConfigKind` is a deliberately separate, informal vocabulary from `TargetCategory` — never conflated.
  [`models.py:62`](../../backend/brain/settings_router/models.py#L62)

**Drawer UI**

- Fetches on open and re-fetches after Approve & Apply, guarded against out-of-order responses with a monotonic request token — a real race a client-only reviewer found and fixed.
  [`SettingsDrawer.tsx:115`](../../frontend/components/settings/SettingsDrawer.tsx#L115)

- Fetch on open, wired independently of the propose/approve flow so a failure here can't block the rest of the drawer.
  [`SettingsDrawer.tsx:108`](../../frontend/components/settings/SettingsDrawer.tsx#L108)

- Read-only row component — no actions, no preview, distinct chip vocabulary and colors (with dark-mode variants) from `ProposedChangeCard`.
  [`ConfigSummaryItem.tsx:12`](../../frontend/components/settings/ConfigSummaryItem.tsx#L12)

**Peripherals**

- Unit/API tests covering the full I/O matrix, including two genuine (unmocked, chmod-based) permission-failure tests.
  [`test_summary.py`](../../backend/tests/brain/settings_router/test_summary.py)
