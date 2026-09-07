---
name: 'Claude Wrapper'
description: 'Web app (Next.js) that replaces the terminal for AI agent orchestration and hand-off. "Flight Tracker" theme — warm, optimistic, plain-language developer tool, not a dark-terminal aesthetic.'
status: final
created: 2026-08-30
updated: 2026-08-30
sources:
  - mockups/key-intent-submission.html
  - mockups/key-task-list.html
  - mockups/key-dag-canvas.html
  - mockups/key-preflight-checklist.html
  - mockups/key-node-inspector.html
  - mockups/key-question-response.html
  - mockups/key-post-run-audit.html
  - mockups/key-flight-path-full.html
  - mockups/key-settings.html
colors:
  bg: '#FFF8F0'
  surface: '#FFFFFF'
  accent: '#2D9CDB'
  text1: '#1A1A2E'
  text2: '#6B6B7D'
  status-waiting-input: '#F5A623'
  status-executing: '#2D9CDB'
  status-trouble: '#FF8C42'
  status-completed: '#27AE60'
  status-cancelled: '#9B9BAA'
  status-failed: '#E74C3C'
  bg-dark: '#1E1B2E'
  surface-dark: '#2A2640'
  accent-dark: '#5AB8F5'
  text1-dark: '#F5F0FF'
  text2-dark: '#B0A8C9'
  status-waiting-input-dark: '#FFC15E'
  status-executing-dark: '#5AB8F5'
  status-trouble-dark: '#FF9A5C'
  status-completed-dark: '#4ADE80'
  status-cancelled-dark: '#8B84A8'
  status-failed-dark: '#FF6B6B'
typography:
  body:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
    fontSize: 16px
  label:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
    fontSize: 12px
  small:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
    fontSize: 14px
  heading-sm:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
    fontSize: 20px
  heading-lg:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
    fontSize: 28px
  literal-path:
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
    fontSize: 14px
rounded:
  sm: 8px
  md: 16px
  lg: 20px
  full: 999px
spacing:
  '1': 4px
  '2': 8px
  '3': 12px
  '4': 16px
  '5': 24px
  '6': 32px
components:
  task-list-row:
    background: '{colors.surface}'
    radius: '{rounded.md}'
    shadow: '0 2px 8px rgba(0,0,0,.05)'
    statusRail: '{colors.status-*}'
    nameFont: '{typography.body}'
    summaryFont: '{typography.small}'
    badgeRadius: '{rounded.full}'
  node-inspector-drawer:
    background: '{colors.surface}'
    dock: 'right'
    radius: '{rounded.lg}'
    shadow: '0 6px 24px rgba(45,156,219,.10)'
    backdrop: 'dimmed, non-interactive canvas behind'
    accentBorder: '{colors.status-trouble}'
    accentBorderWaitingInput: '{colors.status-waiting-input}'
    statRowFont: '{typography.small}'
  checklist-row:
    background: '{colors.surface}'
    radius: '{rounded.sm}'
    selectionAccent: '{colors.accent}'
    sensitiveFlag: '{colors.status-trouble}'
    labelFont: '{typography.body}'
    pathFont: '{typography.literal-path}'
  proposed-change-card:
    background: '{colors.surface}'
    radius: '{rounded.md}'
    shadow: '0 2px 8px rgba(0,0,0,.05)'
    borderAccent: '{colors.accent}'
    categoryBadgeRadius: '{rounded.full}'
    pendingIndicator: 'muted amber-adjacent, distinct from {colors.status-waiting-input}'
    pathFont: '{typography.literal-path}'
---

# DESIGN.md — Claude Wrapper

> **Both spines (this DESIGN.md and its companion EXPERIENCE.md) win on conflict with any mock, wireframe, or import.** The 9 HTML files in `mockups/` are illustrative references that encode real decisions made in this session — they are not the source of truth if a discrepancy is ever found between a mock and what's written here.

## Brand & Style

Claude Wrapper replaces the terminal for AI agent orchestration. The terminal it replaces is opaque, monochrome, and unforgiving — scrollback you have to parse, no visual sense of what's running or what's safe. Claude Wrapper's whole value proposition is trust-through-transparency: show the plan before it runs, show the live graph while it runs, show the receipts after. The visual language has to earn that trust by *reading* calm and legible, not by looking like a dashboard that's trying to impress you.

The theme is **"Flight Tracker"** — warm, optimistic, grounded. Think airport departures board crossed with a well-kept flight-ops room: status is always visible, color communicates state at a glance, and nothing about the surface tries to be dramatic. This is a deliberate rejection of the "dark terminal" aesthetic developer tools default to — Claude Wrapper is colorful and light-primary, not black-and-green. Warmth comes from the palette (warm off-white canvas, sky-blue accent) and from soft, generously-rounded shapes — never from copy tone, which stays plain and grounded (see EXPERIENCE.md § Voice and Tone).

Both light and dark modes are real, fully-specified, switchable options — dark is not an afterthought skin.

## Colors

The palette has two jobs: a calm, warm neutral base that lets the run graph dominate, and a six-color status vocabulary that carries real information (a node's status) rather than decoration.

- **`bg` (`#FFF8F0` light / `#1E1B2E` dark)** — the page canvas. Warm off-white in light mode (never stark white or cool gray) sets the "flight tracker," not "terminal," register immediately.
- **`surface` (`#FFFFFF` light / `#2A2640` dark)** — cards, rows, panels, drawers sit on this, one tone lifted off `bg`.
- **`accent` (`#2D9CDB` light / `#5AB8F5` dark)** — sky blue. The single chromatic color for primary actions, focus rings, selection state, and the `executing` status (the two concepts are intentionally the same color family — "this is happening now" reads consistently whether it's a button or a node).
- **`text1` / `text2`** — primary and secondary text, both kept at real contrast against `bg`/`surface` in both modes (see Accessibility Floor in EXPERIENCE.md).
- **Node status palette (six colors, both modes)** — `waiting_input` (amber), `executing` (accent blue), `trouble` (orange), `completed` (green), `cancelled` (gray), `failed` (red). This is the single vocabulary for the Architecture spine's node status enum (AD-5) — every status badge, rail, drawer accent, and legend entry in the product draws from exactly these six values, never an ad hoc color.

Avoid: black/green terminal palettes, gradients, saturated fills used decoratively, and borrowing a status color for anything that isn't actually that status (e.g. `trouble` orange must never appear as a decorative accent — it always means an agent needs a decision).

## Typography

System font stack (`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif`) for **all** UI text — headings, body, labels, and critically, agent/node names (`auth_scaffold_worker`, `backend_planner`). Agent names read as plain, friendly labels, not code identifiers, even though they're technically snake_case strings.

Monospace (`{typography.literal-path}`) is reserved narrowly for literal values that are actually file paths, `.env`/config filenames, or raw token/path strings — e.g. `src/auth/jwt.py`, `pyproject.toml`, `.env`. It never appears on agent names, headings, status labels, or summary prose.

Scale is a ~5-step ramp: `label` (12px) for badges/caps labels, `small` (14px) for summaries and metadata, `body` (16px) for primary content, `heading-sm` (20px) for section headers, `heading-lg` (28px) for page-level headings ("What do you want to do?"). No exotic display font, no oversized hero type — the ramp stays close together because this is a tool, not an editorial surface.

## Layout & Spacing

Spacing scale: 4 / 8 / 12 / 16 / 24 / 32px (`{spacing.1}`–`{spacing.6}`). Tight spacing (`{spacing.1}`–`{spacing.2}`) sits between closely related elements (a status badge and its label); generous spacing (`{spacing.5}`–`{spacing.6}`) separates major surfaces (header from hero input, sidebar from canvas).

Single-surface web app: a two-pane layout (task-list sidebar + canvas) is the live-run default; overlays (Node Inspector, Question-Response, Settings, Permission Manager) dock right as slide-over drawers over a dimmed backdrop rather than opening new routes or stacking additional panes. Modal/drawer stacks one level deep.

## Elevation & Depth

Two shadow levels, both accent-tinted rather than neutral black, keeping shadows part of the warm palette instead of reading as generic UI chrome:

- **Cards and nodes:** `0 2px 8px rgba(0,0,0,.05)` — a light lift for task-list rows, node cards, checklist rows, proposed-change cards.
- **Larger panels and overlays:** `0 6px 24px rgba(45,156,219,.10)` — a more pronounced, accent-tinted glow for drawers (Node Inspector, Question-Response, Settings), the Pre-Flight checklist overlay, and hero-level input panels.

Elevation communicates layering (this thing floats above that thing), never urgency — urgency and state are carried by the status color vocabulary, not by shadow weight.

## Shapes

Panels and node cards use a generous `{rounded.md}`–`{rounded.lg}` radius (16–20px) — soft enough to feel approachable, not sharp/clinical like a terminal. Chips and badges (status badges, category badges, question badges) are fully rounded pills (`{rounded.full}`, 999px) — the pill shape is reserved for compact, glanceable state indicators specifically. Smaller controls (checklist checkboxes, inline buttons) use the tighter `{rounded.sm}` (8px).

Imagery/icons, where used, follow the same corner logic as their containing surface.

## Components

- **Task-list row** — Identity (agent name, plain system font) + one-line action summary + status badge (pill, `{rounded.full}`, colored per status) + action cluster (view-graph / stop / question-badge-when-applicable). Card background `{colors.surface}`, `{rounded.md}`, `0 2px 8px rgba(0,0,0,.05)`. Planned (pre-execution) state renders as dashed-border, no-shadow cards to visually distinguish "not yet running" from live cards, which are solid with a status-tinted left rail.
- **Node-inspector-family drawer** — Right-docked slide-over, dimmed backdrop, `{rounded.lg}` corner on the drawer edge, `0 6px 24px rgba(45,156,219,.10)` shadow. Shared shell across the two states it renders: `trouble` (orange accent border, push/cancel decision UI) and `waiting_input` (amber accent border, question card + free-text response, no cancel action). Contains a telemetry stat row (time elapsed, tokens used) and a live reasoning ("thinking") block in both states.
- **Pre-Flight checklist row** — Grouped per agent under a group header; each file/MCP item independently checkable, `{rounded.sm}` checkbox control, `{colors.accent}` selection state, sensitive-file items flagged in `{colors.status-trouble}`. Overlay panel itself uses `0 6px 24px rgba(45,156,219,.10)`.
- **Proposed-change card (Settings)** — `{colors.surface}` background, `{rounded.md}`, `0 2px 8px rgba(0,0,0,.05)`, `{colors.accent}` border/emphasis. Anatomy: target path (monospace) + category chip (pill) + action badge (create/update/revoke) + plain-language summary + content preview + a distinct "not yet applied" pending indicator (muted amber-adjacent tone, deliberately not the same hex as `status-waiting-input` so it never reads as a live node state) ahead of the Approve & Apply / Reject gate.
- **Replay context-node annotation (Full Flight Path)** — Same visual family as the live DAG Canvas's node cards, reframed with an explicit "Replay" badge, solid (non-pulsing) route lines instead of the live canvas's animated dashed pulse, and per-context-node token figures nested under each agent-level node.

## Do's and Don'ts

| Do | Don't |
|---|---|
| Warm off-white/light-primary surfaces in both the default and dark-mode-as-setting variants | Default to a black/green dark-terminal aesthetic |
| Draw every status indicator from the six-color node-status vocabulary, consistently | Invent a one-off color for a new state, or reuse `trouble` orange decoratively |
| System font for all UI text, including agent/node names | Monospace agent names, headings, or summary prose |
| Reserve monospace strictly for literal file paths / `.env` / config filenames | Use monospace for anything that isn't a literal path/filename value |
| Soft, accent-tinted shadows at the two defined levels | Flat neutral-black shadows, or a third ad hoc elevation level |
| Pill shape reserved for chips/badges (state, category) | Use a pill for a card, panel, or drawer |
| Purposeful, understated motion on state change / flight-path advance | Flashy animation, celebratory motion (confetti, bounce) on completion |
