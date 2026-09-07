---
title: 'Story 1.2: Submit natural-language settings request + approve'
type: 'feature'
created: '2026-09-07'
status: 'done'
review_loop_iteration: 0
context: []
baseline_commit: 'b64d7a7dd83433681940ebc4412aead71eb630bf'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** A developer has no way to change `.claude/` config except editing files by hand, risking silent config drift with no review step. Story 1.1 only created the bare directory.

**Approach:** Add a Settings Router backend that classifies a natural-language request into structured proposals via Claude, plus a frontend Settings drawer (request box + proposed-change cards) gated behind Approve & Apply / Reject before anything is written.

## Boundaries & Constraints

**Always:** `client.messages.parse()` with a Pydantic `SettingsRouterOutput` schema (`user_summary`, `updates: List[SettingAction]`; `target_category` is a `Literal` of the 8 PRD values, plus `file_path`, `content`, `action`). Model `claude-opus-5`, `anthropic.Anthropic()` (env-based auth). Compute `file_path` server-side from `target_category` — never trust the LLM's path (see Design Notes) — and validate it resolves under `.claude/` before writing. Read on-disk `.claude/` state as classification context (no cached snapshot). Nothing written until Approve & Apply; Reject touches no files. Settings opens as a drawer/overlay, not a route. Category chip renders the literal `target_category` string. Reuse Story 1.1's Tailwind tokens. Anthropic call must be mockable so tests never hit the live API.

**Ask First:** None anticipated — model choice (Claude Opus 5) already confirmed.

**Never:** Write to `.claude/` without explicit approval. Invent a 9th `target_category` or use a label like "config"/"MCP grant". Build Story 1.3 (config viewer) or Story 1.4 (permission grants) — this story only submits/approves Settings proposals. Call the LLM from the frontend directly — always through the backend.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Single action | "always use pytest" | One proposed-change card (e.g. `rule`, create) with summary + preview | N/A |
| Multiple actions | "always use pytest, never commit .env" | One card per proposed action | N/A |
| Approve | Approve & Apply pressed on a card | File written/updated/revoked exactly as previewed; nothing else touched | N/A |
| Reject | Reject pressed | Card discarded; no filesystem write | N/A |
| No-op request | Request maps to nothing actionable | `user_summary` explains why; no cards shown | Friendly empty state, not an error |
| LLM/API failure | Anthropic API errors (rate limit, timeout, auth) | Request fails, no partial writes | Error envelope surfaced to UI |
| Path escape | LLM-proposed path resolves outside `.claude/` | Rejected before any write | 400 validation error, nothing written |

</frozen-after-approval>

## Code Map

- `backend/pyproject.toml` -- add `anthropic` dependency
- `backend/brain/settings_router/models.py` -- `SettingAction`/`SettingsRouterOutput` Pydantic models
- `backend/brain/settings_router/router.py` -- `classify_request()`: reads `.claude/`, calls `client.messages.parse()`, computes `file_path`, validates path containment
- `backend/brain/settings_router/apply.py` -- `apply_action()`: writes/updates/deletes one approved action's target file
- `backend/gateway/main.py` -- `POST /api/settings/propose`, `POST /api/settings/apply`
- `frontend/components/settings/ProposedChangeCard.tsx` -- UX-DR10 card
- `frontend/components/settings/SettingsDrawer.tsx` -- request textarea + card list + Approve/Reject
- `frontend/app/page.tsx` -- app shell with a persistent settings entry point (first real UI beyond Story 1.1's scaffold)

## Tasks & Acceptance

**Execution:**
- [x] `backend/pyproject.toml` -- add `anthropic` dependency -- required for the LLM call
- [x] `backend/brain/settings_router/models.py` -- Pydantic schema -- structured-output contract
- [x] `backend/brain/settings_router/router.py` -- classification logic per Boundaries -- core FR-1 behavior, mockable
- [x] `backend/brain/settings_router/apply.py` -- approval-gated write -- FR-2, only path touching `.claude/`
- [x] `backend/gateway/main.py` -- propose/apply endpoints -- exposes the feature to the frontend
- [x] `backend/tests/brain/settings_router/` -- unit tests covering the I/O matrix, Anthropic client mocked -- verifies behavior with no live API calls
- [x] `frontend/components/settings/ProposedChangeCard.tsx` -- UX-DR10 card -- reusable across the drawer
- [x] `frontend/components/settings/SettingsDrawer.tsx` -- submission + review UI -- FR-1/FR-2 UI
- [x] `frontend/app/page.tsx` -- app shell + settings entry point -- first real frontend surface

**Acceptance Criteria:**
- Given an existing or newly-initialized `.claude/` directory, when I submit a natural-language request, then I see the request's overall `user_summary` once, plus one proposed-change card per classified action, each showing `target_category`, file path, action, and content preview (resolved during step-03: `SettingAction` has no per-action summary field — confirmed with the human rather than guessing)
- Given a proposed change, when I press Approve & Apply, then the file is written/updated/revoked exactly as previewed and nothing else in `.claude/` changes
- Given a proposed change, when I press Reject, then no files are touched
- Given a request that maps to nothing actionable, when I submit it, then I see a plain-language explanation and no crash

## Spec Change Log

## Design Notes

Category → path mapping (deterministic, server-computed; `{slug}` = LLM-proposed kebab-case name, sanitized server-side): `team_instructions`→`.claude/CLAUDE.md`, `local_instructions`→`.claude/CLAUDE.local.md`, `settings.json`/`settings.local.json`→same-named file, `rule`/`skill`/`command`/`agent`→`.claude/{rules,skills/{slug},commands,agents}/{slug}.md`.

Error envelope: reuse the app-wide `{error_code, message, node_id}` shape with `node_id` always `null` here, rather than a second shape.

## Verification

**Commands:**
- `cd backend && uv run pytest tests/brain/ -v` -- expected: all pass, including mocked-LLM edge cases
- `cd frontend && npm run build` -- expected: succeeds

**Manual checks (if no CLI):**
- A live call needs a real `ANTHROPIC_API_KEY`, not configured in this environment: with one set, POST a real request to `/api/settings/propose`, confirm the cards look right, press Approve & Apply, and confirm the exact file appears under `.claude/` with the previewed content and nothing else changed.

## Suggested Review Order

**Classification (FR-1)**

- Entry point: reads live `.claude/` state, calls Claude for structured output, then recomputes every path server-side before returning.
  [`router.py:178`](../../backend/brain/settings_router/router.py#L178)

- Fixed a real crash: the SDK's `parsed_output` is `Optional`, and `None` was reachable but unhandled before this review.
  [`router.py:209`](../../backend/brain/settings_router/router.py#L209)

- Disambiguates same-response path collisions (e.g. two unnamed `rule` actions) instead of letting one silently clobber the other.
  [`router.py:226`](../../backend/brain/settings_router/router.py#L226)

- No cached snapshot — always walks the live directory, bounded so a large control center can't blow the context window.
  [`router.py:141`](../../backend/brain/settings_router/router.py#L141)

**Path safety (the core security property of this story)**

- Independently re-derives the expected path from `target_category` and rejects any mismatch — closes the gap where a client could pair any category with any in-bounds path.
  [`apply.py:39`](../../backend/brain/settings_router/apply.py#L39)

- Client-supplied path re-validated at apply time, never trusted as the exact string `classify_request()` produced.
  [`apply.py:17`](../../backend/brain/settings_router/apply.py#L17)

- Deterministic category→path mapping; the LLM's own path guess is only ever a sanitized slug hint, never trusted directly.
  [`router.py:111`](../../backend/brain/settings_router/router.py#L111)

- Slug sanitization strips separators/`..` and caps length, so nothing here can escape `.claude/` or exceed OS filename limits.
  [`router.py:95`](../../backend/brain/settings_router/router.py#L95)

**API surface & error handling**

- `/api/settings/propose` (FR-1) and `/api/settings/apply` (FR-2) — the only two endpoints, cleanly separated read/write.
  [`main.py:93`](../../backend/gateway/main.py#L93)

- Filesystem failures now map to the app-wide error envelope instead of a raw 500.
  [`main.py:77`](../../backend/gateway/main.py#L77)

- Every `anthropic.AnthropicError` subclass (plus the SDK's bare-`TypeError` credential-resolution failure, normalized in `router.py`) maps to one envelope shape.
  [`main.py:65`](../../backend/gateway/main.py#L65)

- Single error envelope shape reused app-wide, `node_id` always `null` for Settings (Design Notes).
  [`errors.py`](../../backend/gateway/errors.py)

**Approval UI**

- Cards keyed by stable `id`, not array index — fixes a race where rejecting one card while another's approve was in flight could strand it on "applying…" forever.
  [`SettingsDrawer.tsx:117`](../../frontend/components/settings/SettingsDrawer.tsx#L117)

- Dialog accessibility: `role="dialog"`, focus trap, focus moved in on open and restored on close.
  [`SettingsDrawer.tsx:145`](../../frontend/components/settings/SettingsDrawer.tsx#L145)

- UX-DR10 card: literal `target_category` chip, action badge, content preview, gated behind Approve & Apply / Reject.
  [`ProposedChangeCard.tsx:26`](../../frontend/components/settings/ProposedChangeCard.tsx#L26)

- First real app shell surface — persistent Settings entry point replacing Story 1.1's stock scaffold.
  [`page.tsx:14`](../../frontend/app/page.tsx#L14)

- Thin fetch client to the two gateway endpoints; types mirror the backend Pydantic models by hand (no codegen yet).
  [`settings-api.ts:55`](../../frontend/lib/settings-api.ts#L55)

**Peripherals**

- Unit/API tests for the full I/O matrix minus Reject (frontend-only, deferred — see `deferred-work.md`), Anthropic client always mocked.
  [`test_apply.py`](../../backend/tests/brain/settings_router/test_apply.py), [`test_router.py`](../../backend/tests/brain/settings_router/test_router.py), [`test_gateway_endpoints.py`](../../backend/tests/brain/settings_router/test_gateway_endpoints.py)

- `anthropic==1.4.0` added; `ANTHROPIC_API_KEY` documented in `backend/.env.example` and the root `README.md`.
  [`pyproject.toml`](../../backend/pyproject.toml), [`.env.example`](../../backend/.env.example)
