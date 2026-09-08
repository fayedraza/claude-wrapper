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

**Approach:** A new persistent "Permissions" surface (own drawer + header entry, same pattern as Settings) to view, add, move, and revoke grants. Grants are flat per-resource (file path or MCP server name — chosen over per-action rules), persisted under a `permissionGrants` key in one of two files, chosen by scope: `local` (`.claude/settings.local.json`, personal) or `team` (`.claude/settings.json`, shared). **Renegotiated post-implementation** (see Spec Change Log): originally scoped to `local` only; the human asked for team-scope management too, plus a way to move a grant between scopes, plus a UI banner showing which file each grant lives in.

## Boundaries & Constraints

**Always:** Endpoints `GET/POST /api/permission-grants`, `PATCH /api/permission-grants/{id}`, `DELETE /api/permission-grants/{id}`. Grant shape: `{id, kind: "file"|"mcp", target, scope: "local"|"team"}` — flat, one row per resource, `scope` derived from which file it's in (never persisted inside the JSON entry itself). Add is idempotent within its own scope; the same `kind`+`target` can independently exist in both scopes (matches how Claude Code's own real permission arrays merge rather than conflict across settings files). Revoke and update locate a grant by id regardless of which file it's in. Moving a grant (via `PATCH .../{id}` with a new `scope`) onto an existing identical grant in the destination merges into it (same idempotency rule as add). `apply.py`'s Settings-Router write path must preserve an existing `permissionGrants` entry when writing either settings file for an unrelated reason (the cross-story regression this story already fixed once for `settings.local.json` — now extended to `settings.json` too). `summary.py`'s "Currently configured" reader delegates to `grants.py`'s `list_grants()` (single source of truth, both scopes) rather than re-parsing JSON itself. Permission Manager is a new persistent header entry next to Settings (UX-DR6): own drawer + component tree, reusing only Settings drawer's dialog chrome. The Permission Manager's grant list shows a scope banner (Local/Team) per row; the add-grant form lets the user choose scope, with inline copy explaining the consequence (which file, shared or not).

**Ask First:** None anticipated.

**Never:** Implement the live Pre-Flight checklist (FR-4) or mid-run cutoff (FR-5's active-run half) — needs the execution engine, doesn't exist yet. Validate a granted file/server actually exists or is reachable. Read or write Claude Code's own reserved `permissions`/`hooks` keys in either settings file — only ever `permissionGrants`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| No grants yet | No `permissionGrants` key in either file | Empty list, friendly empty state | N/A |
| Add a grant | `kind`+`target`+`scope` | New row with generated id, in the chosen file | N/A |
| Add an already-granted resource | Same `kind`+`target`+`scope` as existing | Existing grant returned, no duplicate | N/A |
| Add same resource in the other scope | Same `kind`+`target`, different `scope` | Both grants exist independently (not deduped across scopes) | N/A |
| Add with empty/whitespace target | `target="   "` | Rejected | 400 envelope |
| Revoke a grant | Existing id, any scope | Row disappears from list + its file | N/A |
| Revoke unknown/already-revoked id | Nonexistent id | Error shown, list re-fetches | 404 envelope |
| Move a grant between scopes | `PATCH` with a new `scope` | Removed from old file, added to new file, same id | N/A |
| Move onto an identical existing grant | Destination already has same `kind`+`target` | Merges into the existing grant, source row removed | N/A |
| Edit a grant's target/kind in place | `PATCH` with `target`/`kind`, no `scope` change | Updated in place, same file, same id | N/A |
| Unrelated Settings Router write to either settings file | e.g. a hooks/rule tweak applied via `/api/settings/apply` | Existing `permissionGrants` in that file survives untouched | N/A |
| Fetch fails | Backend/network error | Error shown; drawer still usable | Envelope surfaced |

</frozen-after-approval>

## Code Map

- `backend/brain/settings_router/models.py:66` -- extend `ConfigKind` +`"file"`; add `GrantScope`, `PermissionGrantKind`, `PermissionGrant`, `PermissionGrantsList`, `AddPermissionGrantRequest`, `UpdatePermissionGrantRequest`
- `backend/brain/settings_router/grants.py` (new) -- `list_grants`/`add_grant`/`revoke_grant`/`update_grant` across both `settings.local.json` (local) and `settings.json` (team) scope
- `backend/brain/settings_router/summary.py:148-172` -- `_permission_grant_items` delegates entirely to `grants.list_grants()`, single source of truth for both surfaces
- `backend/brain/settings_router/apply.py:68` -- `_preserve_permission_grants` extended to guard both `settings.local.json` and `settings.json` writes
- `backend/gateway/main.py:171` -- four `/api/permission-grants` routes (GET/POST/PATCH/DELETE) + two exception handlers, mirroring `SettingsPathError`
- `.gitignore` -- add `.claude/settings.local.json`
- `frontend/lib/settings-api.ts:46,58-67` -- add `"file"` to `ConfigKind`; export `readErrorMessage`
- `frontend/lib/permission-grants-api.ts` (new) -- client, mirrors `settings-api.ts`; `GrantScope`, `updatePermissionGrant`
- `frontend/components/settings/ConfigSummaryItem.tsx:12-16` -- `"file"` chip color, reused by `PermissionGrantRow`
- `frontend/components/permission-manager/PermissionGrantRow.tsx` (new) -- kind chip + scope banner + target + Move/Revoke actions
- `frontend/components/permission-manager/PermissionManagerDrawer.tsx` (new) -- add-grant form (kind+target+scope) + list + move/revoke wiring, chrome from `SettingsDrawer.tsx:43-132`
- `frontend/app/page.tsx:14-43` -- "Permissions" header button opening the new drawer, mutually exclusive with Settings

## Tasks & Acceptance

**Execution:**
- [x] `backend/brain/settings_router/models.py` -- grant models + `ConfigKind` extension + `GrantScope`
- [x] `backend/brain/settings_router/grants.py` -- list/add/revoke/update across both scopes, core FR-6 logic
- [x] `backend/brain/settings_router/summary.py` -- delegate to `grants.list_grants()`
- [x] `backend/brain/settings_router/apply.py` -- extend grant-preservation guard to `settings.json`
- [x] `backend/gateway/main.py` -- four endpoints + two exception handlers
- [x] `backend/tests/brain/settings_router/test_grants.py` -- I/O matrix coverage, both scopes + update/move
- [x] `backend/tests/brain/settings_router/test_summary.py` -- both-scope display coverage
- [x] `backend/tests/brain/settings_router/test_apply.py` -- team-scope grant-preservation regression test
- [x] `.gitignore` -- add `.claude/settings.local.json`
- [x] `frontend/lib/permission-grants-api.ts` -- client + `updatePermissionGrant`
- [x] `frontend/lib/settings-api.ts` -- `"file"` `ConfigKind`, export `readErrorMessage`
- [x] `frontend/components/settings/ConfigSummaryItem.tsx` -- `"file"` chip color
- [x] `frontend/components/permission-manager/PermissionGrantRow.tsx` -- row + scope banner + move/revoke
- [x] `frontend/components/permission-manager/PermissionManagerDrawer.tsx` -- form (kind+target+scope) + list + move/revoke
- [x] `frontend/app/page.tsx` -- "Permissions" header entry point

**Acceptance Criteria:**
- Given no grants exist, when I open Permissions, then I see a friendly empty state, not an error
- Given I add a grant to either scope, when it succeeds, then it appears in the list without reopening the drawer, tagged with the right scope banner
- Given I revoke a grant, when it succeeds, then it disappears from the list and from its file, regardless of which scope it was in
- Given I move a grant to the other scope, when it succeeds, then it disappears from the old file and appears in the new one with the same id
- Given a grant exists in either file, when I open Settings, then "Currently configured" shows the correct kind chip, target text, and file path — never a hardcoded placeholder
- Given the Settings Router applies an unrelated change to either settings file, when it writes, then any existing `permissionGrants` in that file survives

## Spec Change Log

- **Renegotiated after merge (human-initiated, not a review finding):** The human asked why grants only ever wrote to `settings.local.json`, whether Claude Code's own real `permissions.allow`/`ask`/`deny` keys array-merge across `settings.json`/`settings.local.json` (confirmed: yes, per Claude Code's own docs — but irrelevant here since this app's agents aren't Claude Code CLI processes), and then explicitly requested: manage grants from both `settings.local.json` and `settings.json`; add a banner showing which file a grant lives in; add the ability to update/move a grant between the two. This amends the frozen `Never: ... Read or write ... settings.json` line and the `Approach` line above — both rewritten in place per the human-renegotiation exception, rather than left contradicting the shipped code. **KEEP:** the flat per-resource schema, the idempotent-add rule, targets-are-opaque-identifiers, and the `apply.py` grant-preservation fix all survive unchanged — only the file scope widened from one file to two, plus a new `PATCH` update/move operation. `summary.py` was further simplified during this change to delegate entirely to `grants.py`'s `list_grants()` rather than keep its own separate (and once-diverging) JSON-parsing logic — this drops the old freeform-entry text/description/name fallback (a pre-schema Story 1.3 heuristic) in favor of strict schema validation on read, matching what's already enforced on write; no real freeform entries exist in this repo today, so nothing observable regresses.

## Design Notes

Grants persist under `permissionGrants` in one of two files, chosen by scope: `local` (`.claude/settings.local.json`, personal, not committed) or `team` (`.claude/settings.json`, shared, usually committed — the same file Claude Code's own `hooks`/`permissions` keys live in, though this app never touches those keys, only its own `permissionGrants`). `grants.py`'s `list_grants()` is the single canonical reader for both files, tagging each grant with its scope; `summary.py`'s "Currently configured" display delegates to it entirely rather than re-parsing JSON itself, so the two UI surfaces can never disagree about what's configured (an earlier version had separate logic that once did disagree — see Spec Change Log).

Confirmed real Claude Code's own `permissions.allow/ask/deny`/`allowedMcpServers` keys are irrelevant to enforcement here — this app's agents aren't Claude Code CLI processes, so there's no Claude Code permission engine on the other end to hand grants to; enforcement is this app's own responsibility, in the not-yet-built `backend/engine/`. That's true regardless of which settings file `permissionGrants` lives in.

No mockup or `.config-kind.file` color exists — pick one distinct from `rule`/`agent`/`mcp`, reuse identically in `ConfigSummaryItem` and `PermissionGrantRow`.

Targets are opaque identifiers — never check a file exists or a server is reachable. Validate non-empty-after-trim + a generous max length, nothing more.

## Verification

**Commands:**
- `cd backend && uv run pytest tests/brain/ -v` -- expected: all pass
- `cd frontend && npm run build` -- expected: succeeds

## Suggested Review Order

**Grant persistence across two scopes (FR-6)**

- Entry point: view/add/revoke/update across both `settings.local.json` (local) and `settings.json` (team), each grant tagged with which one it came from.
  [`grants.py:116`](../../backend/brain/settings_router/grants.py#L116)

- Add is idempotent within its own scope only; the same `kind`+`target` in both scopes is two independent, both-apply facts, not a collision.
  [`grants.py:130`](../../backend/brain/settings_router/grants.py#L130)

- Revoke and update locate a grant by id via `_find_grant`, regardless of which scope it's in -- callers never need to know which file a grant lives in.
  [`grants.py:107`](../../backend/brain/settings_router/grants.py#L107)

- Moving a grant between scopes merges into an identical existing grant at the destination (same idempotency rule as add) rather than duplicating.
  [`grants.py:183`](../../backend/brain/settings_router/grants.py#L183)

- `scope` is derived from which file an entry is read from, never persisted inside the JSON entry itself -- `_dump_grants` explicitly excludes it on write.
  [`grants.py:101`](../../backend/brain/settings_router/grants.py#L101)

**Cross-story regression fix -- grants surviving unrelated writes, now for both files**

- Originally fixed only for `settings.local.json`; widening grants to `settings.json` reintroduced the identical risk there, so the guard now covers both.
  [`apply.py:70`](../../backend/brain/settings_router/apply.py#L70)

- Regression test for the team-scope case, mirroring the original `settings.local.json` one.
  [`test_apply.py:192`](../../backend/tests/brain/settings_router/test_apply.py#L192)

**Single source of truth for display -- fixing a real, once-observed inconsistency**

- `summary.py`'s "Currently configured" reader now delegates entirely to `grants.list_grants()` instead of its own separate JSON-parsing logic -- the two UI surfaces literally cannot disagree anymore, since they share one function.
  [`summary.py:145`](../../backend/brain/settings_router/summary.py#L145)

**Schema (FR-6)**

- Flat per-resource grant shape `{id, kind, target, scope}` -- chosen over per-action rules; `ConfigKind` gains `"file"`. `GrantScope` deliberately distinct from `ConfigKind`/`TargetCategory`.
  [`models.py:95`](../../backend/brain/settings_router/models.py#L95)

- New `PermissionGrant`, `PermissionGrantsList`, `AddPermissionGrantRequest`, `UpdatePermissionGrantRequest` contracts.
  [`models.py:98`](../../backend/brain/settings_router/models.py#L98)

**API surface**

- Four endpoints (GET/POST/PATCH/DELETE) + two exception handlers (400/404), mirroring the existing `SettingsPathError` pattern.
  [`main.py:175`](../../backend/gateway/main.py#L175)

**Permission Manager UI**

- New persistent header entry next to Settings (UX-DR6); opening either drawer now closes the other.
  [`page.tsx:34`](../../frontend/app/page.tsx#L34)

- Add-grant form now includes a scope selector with inline copy explaining the consequence of each choice (which file, shared or not).
  [`PermissionManagerDrawer.tsx:285`](../../frontend/components/permission-manager/PermissionManagerDrawer.tsx#L285)

- Moving a grant handles the merge case: the response's id may differ from the one moved (destination already had an identical grant), so state is reconciled by id, not assumed unchanged.
  [`PermissionManagerDrawer.tsx:180`](../../frontend/components/permission-manager/PermissionManagerDrawer.tsx#L180)

- Concurrent revokes/moves tracked via `Set`s, not single ids, so in-flight state can't clobber across rows.
  [`PermissionManagerDrawer.tsx:50`](../../frontend/components/permission-manager/PermissionManagerDrawer.tsx#L50)

- Scope banner (Local/Team) per row, distinct styling from the kind chip -- reuses `ConfigSummaryItem`'s exported chip-color map for kind so `file`/`mcp` render identically in both surfaces.
  [`PermissionGrantRow.tsx:19`](../../frontend/components/permission-manager/PermissionGrantRow.tsx#L19)

**Peripherals**

- Client for all four endpoints, mirroring `settings-api.ts`'s conventions; `GrantScope`, `updatePermissionGrant`.
  [`permission-grants-api.ts`](../../frontend/lib/permission-grants-api.ts)

- Full I/O-matrix coverage across both scopes, including genuine (unmocked, chmod-based) permission-failure tests.
  [`test_grants.py`](../../backend/tests/brain/settings_router/test_grants.py)

- `.claude/settings.local.json` added -- first story to actually write it.
  [`.gitignore`](../../.gitignore)
