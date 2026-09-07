---
title: 'Story 1.4: View and manage permission grants between runs'
type: 'feature'
created: '2026-09-07'
status: 'done'
review_loop_iteration: 0
context: []
baseline_commit: '07a2ae3b1836227d9b3603a8bff50011e1d2c5fd'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** No run engine exists yet, so FR-4's live Pre-Flight checklist and FR-5's live mid-run cutoff can't be built. FR-6 (add a grant anytime, no run required) and the standing half of FR-5 ("future runs respect it automatically") are implementable now — and Story 1.3 left `permissionGrants` schema-less for this story to define.

**Approach:** A new persistent "Permissions" surface (own drawer + header entry, same pattern as Settings) to view, add, revoke grants. Grants are flat per-resource (file path or MCP server name — chosen over per-action rules), persisted under `.claude/settings.local.json`'s `permissionGrants` key, never the team-shared `settings.json`.

## Boundaries & Constraints

**Always:** New endpoints `GET/POST /api/permission-grants`, `DELETE /api/permission-grants/{id}`. Grant shape: `{id, kind: "file"|"mcp", target}` — flat, one row per resource. Reads/writes go only to `.claude/settings.local.json` (never `settings.json`); add it to `.gitignore`. Adding an already-present (same kind+target) grant is idempotent. Fix `summary.py`'s `_permission_grant_items`/`_grant_text` to render real `kind`/`target`, not hardcode `kind="mcp"`; add `"file"` to `ConfigKind` + its chip color. Permission Manager is a new persistent header entry next to Settings (UX-DR6): own drawer + component tree (`frontend/components/permission-manager/`), reusing only Settings drawer's dialog chrome.

**Ask First:** None anticipated.

**Never:** Implement the live Pre-Flight checklist (FR-4) or mid-run cutoff (FR-5's active-run half) — needs the execution engine, doesn't exist yet. Validate a granted file/server actually exists or is reachable. Read or write `permissionGrants` in `settings.json`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| No grants yet | No `permissionGrants` key | Empty list, friendly empty state | N/A |
| Add a grant | `kind`+`target` | New row with generated id | N/A |
| Add an already-granted resource | Same `kind`+`target` as existing | Existing grant returned, no duplicate | N/A |
| Add with empty/whitespace target | `target="   "` | Rejected | 400 envelope |
| Revoke a grant | Existing id | Row disappears from list + file | N/A |
| Revoke unknown/already-revoked id | Nonexistent id | Error shown, list re-fetches | 404 envelope |
| Fetch fails | Backend/network error | Error shown; drawer still usable | Envelope surfaced |

</frozen-after-approval>

## Code Map

- `backend/brain/settings_router/models.py:66` -- extend `ConfigKind` +`"file"`; add `PermissionGrantKind`, `PermissionGrant`, `PermissionGrantsList`, `AddPermissionGrantRequest`
- `backend/brain/settings_router/grants.py` (new) -- `list_grants`/`add_grant`/`revoke_grant` against `.claude/settings.local.json` only
- `backend/brain/settings_router/summary.py:143-187` -- `_permission_grant_items`/`_grant_text`: render real `kind`/`target`, fall back for freeform entries
- `backend/gateway/main.py:111` -- three `/api/permission-grants` routes + two exception handlers, mirroring `SettingsPathError`
- `.gitignore` -- add `.claude/settings.local.json`
- `frontend/lib/settings-api.ts:46,58-67` -- add `"file"` to `ConfigKind`; export `readErrorMessage`
- `frontend/lib/permission-grants-api.ts` (new) -- client, mirrors `settings-api.ts`
- `frontend/components/settings/ConfigSummaryItem.tsx:12-16` -- `"file"` chip color, reused by `PermissionGrantRow`
- `frontend/components/permission-manager/PermissionGrantRow.tsx` (new) -- kind chip + target + Revoke button
- `frontend/components/permission-manager/PermissionManagerDrawer.tsx` (new) -- add-grant form + list, chrome from `SettingsDrawer.tsx:43-132`
- `frontend/app/page.tsx:14-43` -- "Permissions" header button opening the new drawer

## Tasks & Acceptance

**Execution:**
- [x] `backend/brain/settings_router/models.py` -- grant models + `ConfigKind` extension
- [x] `backend/brain/settings_router/grants.py` -- list/add/revoke, core FR-6 logic
- [x] `backend/brain/settings_router/summary.py` -- fix `_permission_grant_items`/`_grant_text`
- [x] `backend/gateway/main.py` -- three endpoints + two exception handlers
- [x] `backend/tests/brain/settings_router/test_grants.py` -- I/O matrix coverage
- [x] `.gitignore` -- add `.claude/settings.local.json`
- [x] `frontend/lib/permission-grants-api.ts` -- client
- [x] `frontend/lib/settings-api.ts` -- `"file"` `ConfigKind`, export `readErrorMessage`
- [x] `frontend/components/settings/ConfigSummaryItem.tsx` -- `"file"` chip color
- [x] `frontend/components/permission-manager/PermissionGrantRow.tsx` -- row + revoke
- [x] `frontend/components/permission-manager/PermissionManagerDrawer.tsx` -- form + list
- [x] `frontend/app/page.tsx` -- "Permissions" header entry point

**Acceptance Criteria:**
- Given no grants exist, when I open Permissions, then I see a friendly empty state, not an error
- Given I add a grant, when it succeeds, then it appears in the list without reopening the drawer
- Given I revoke a grant, when it succeeds, then it disappears from the list and from disk
- Given a grant exists, when I open Settings, then "Currently configured" shows the correct kind chip and target text, not a hardcoded placeholder

## Spec Change Log

## Design Notes

Grants persist only in `settings.local.json` — a personal trust decision, not team-shared config; `settings.json` is Claude Code's own enforced file, out of scope. `summary.py` keeps reading `permissionGrants` from both files for display (unchanged from 1.3).

No mockup or `.config-kind.file` color exists — pick one distinct from `rule`/`agent`/`mcp`, reuse identically in `ConfigSummaryItem` and `PermissionGrantRow`.

Targets are opaque identifiers — never check a file exists or a server is reachable. Validate non-empty-after-trim + a generous max length, nothing more.

## Verification

**Commands:**
- `cd backend && uv run pytest tests/brain/ -v` -- expected: all pass
- `cd frontend && npm run build` -- expected: succeeds

## Suggested Review Order

**Grant persistence (FR-6)**

- Entry point: view/add/revoke against `.claude/settings.local.json` only, never `settings.json`.
  [`grants.py:91`](../../backend/brain/settings_router/grants.py#L91)

- Add is idempotent on `kind`+`target`; validates non-empty-after-trim and a length cap, nothing more.
  [`grants.py:100`](../../backend/brain/settings_router/grants.py#L100)

- Revoke raises `PermissionGrantNotFoundError` for an unknown/already-revoked id.
  [`grants.py:128`](../../backend/brain/settings_router/grants.py#L128)

**Cross-story regression fix — grants surviving unrelated writes**

- A real, review-caught bug: approving an unrelated `settings.local.json` change used to silently wipe every permission grant via full-file overwrite. Now preserves the existing `permissionGrants` unless the new content itself redefines that key.
  [`apply.py:68`](../../backend/brain/settings_router/apply.py#L68)

- Regression test reproducing the exact scenario the reviewer demonstrated.
  [`test_apply.py:151`](../../backend/tests/brain/settings_router/test_apply.py#L151)

**Schema (FR-6)**

- Flat per-resource grant shape `{id, kind, target}` -- chosen over per-action rules; `ConfigKind` gains `"file"`.
  [`models.py:66`](../../backend/brain/settings_router/models.py#L66)

- New `PermissionGrant`/`PermissionGrantsList`/`AddPermissionGrantRequest` contracts.
  [`models.py:88`](../../backend/brain/settings_router/models.py#L88)

**Story 1.3 integration -- honoring its "verify, don't assume" note**

- `_permission_grant_items`/`_grant_kind`/`_grant_text` now render the real `kind`/`target` schema instead of a hardcoded `"mcp"` placeholder, falling back gracefully for legacy freeform entries.
  [`summary.py:143`](../../backend/brain/settings_router/summary.py#L143)

**API surface**

- Three new endpoints + two exception handlers (400/404), mirroring the existing `SettingsPathError` pattern.
  [`main.py:171`](../../backend/gateway/main.py#L171)

**Permission Manager UI**

- New persistent header entry next to Settings (UX-DR6); opening either drawer now closes the other.
  [`page.tsx:30`](../../frontend/app/page.tsx#L30)

- Own drawer + component tree, reusing only Settings drawer's dialog chrome; fetch-on-open with a request-token guard.
  [`PermissionManagerDrawer.tsx:35`](../../frontend/components/permission-manager/PermissionManagerDrawer.tsx#L35)

- Concurrent revokes tracked via a `Set`, not a single id, so in-flight state can't clobber across rows.
  [`PermissionManagerDrawer.tsx:44`](../../frontend/components/permission-manager/PermissionManagerDrawer.tsx#L44)

- Read-only row reusing `ConfigSummaryItem`'s exported chip-color map so `file`/`mcp` render identically in both surfaces.
  [`PermissionGrantRow.tsx:17`](../../frontend/components/permission-manager/PermissionGrantRow.tsx#L17)

- New `"file"` chip color (no mockup exists for this screen) exported for reuse.
  [`ConfigSummaryItem.tsx:12`](../../frontend/components/settings/ConfigSummaryItem.tsx#L12)

**Peripherals**

- Client for the three endpoints, mirroring `settings-api.ts`'s conventions.
  [`permission-grants-api.ts`](../../frontend/lib/permission-grants-api.ts)

- `readErrorMessage` exported for reuse by the new client.
  [`settings-api.ts:46`](../../frontend/lib/settings-api.ts#L46)

- Full I/O-matrix coverage including two genuine (unmocked, chmod-based) permission-failure tests.
  [`test_grants.py`](../../backend/tests/brain/settings_router/test_grants.py)

- `.claude/settings.local.json` added -- first story to actually write it.
  [`.gitignore`](../../.gitignore)
