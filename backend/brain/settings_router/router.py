"""Settings Router classification (FR-1): natural-language request -> proposals.

`classify_request()` reads the on-disk `.claude/` state as context (Boundaries:
"no cached snapshot"), asks Claude to classify the request into structured
`SettingAction`s via `client.messages.parse()`, then recomputes every
`file_path` server-side from `target_category` (Design Notes mapping) before
returning -- the LLM's own `file_path` guess is never trusted for a write,
only used (sanitized) as the slug source for categories that need one.
"""

from __future__ import annotations

import re
from pathlib import Path

import anthropic

from .models import SettingsRouterOutput, TargetCategory

MODEL = "claude-opus-5"
MAX_TOKENS = 8000

# Design Notes mapping: category -> fixed filename directly under .claude/.
_FIXED_RELATIVE_PATHS: dict[str, str] = {
    "team_instructions": "CLAUDE.md",
    "local_instructions": "CLAUDE.local.md",
    "settings.json": "settings.json",
    "settings.local.json": "settings.local.json",
}

# Design Notes mapping: category -> (subdirectory, nest under its own slug dir).
# `.claude/{rules,skills/{slug},commands,agents}/{slug}.md`
_SLUG_CATEGORY_SUBDIR: dict[str, tuple[str, bool]] = {
    "rule": ("rules", False),
    "skill": ("skills", True),
    "command": ("commands", False),
    "agent": ("agents", False),
}

# Bound how much on-disk .claude/ content is fed to the classifier per file
# and overall, so a large control center can't blow the context window.
_MAX_CHARS_PER_FILE = 4000
_MAX_CONTEXT_CHARS = 60000
_SKIP_DIR_NAMES = {".git", "node_modules", "__pycache__"}

SYSTEM_PROMPT = """\
You are the Settings Router for Claude Wrapper, a tool that manages a git-aware
`.claude/` control center (rules, instructions, settings, skills, commands,
agent personas).

Given a developer's natural-language configuration request and a snapshot of
the current `.claude/` directory, classify the request into zero or more
structured changes.

Rules:
- Each change has a `target_category`, one of exactly these 8 values:
  team_instructions, local_instructions, settings.json, settings.local.json,
  rule, skill, command, agent. Never invent a different category or label.
- `team_instructions` is project-wide standing guidance (CLAUDE.md).
  `local_instructions` is developer-local guidance not meant to be shared/committed
  (CLAUDE.local.md).
- `settings.json` / `settings.local.json` are for permission/tool
  configuration, not prose guidance.
- `rule`, `skill`, `command`, `agent` are named, individually-filed items --
  give each a short, descriptive, kebab-case name in `file_path` (e.g.
  "testing.md" or "always-use-pytest"). This name is only a hint used to
  derive a slug; you do not control the real path.
- `file_path` is otherwise only a hint -- the real path is computed
  server-side from `target_category`. Do not include directory separators
  beyond a bare filename/slug guess.
- `content` is the full file content to write (for create/update) -- for
  team_instructions/local_instructions this is prose/Markdown; for
  settings.json/settings.local.json this is the JSON document (or the merged
  result you propose); for rule/skill/command/agent this is the Markdown body.
- `action` is "create" if the target file doesn't exist yet in the provided
  snapshot, "update" if it does and should change, or "revoke" if the request
  asks to remove/undo something that exists. For "revoke", `content` may be
  empty.
- One request can produce multiple changes (e.g. a rule file plus a
  settings.json permission entry) -- emit one SettingAction per distinct
  file touched.
- If the request doesn't map to any concrete `.claude/` change (chit-chat,
  already satisfied, out of scope), return an empty `updates` list and use
  `user_summary` to explain why in plain language -- this is a normal,
  friendly outcome, not an error.
- Always populate `user_summary` with a short, plain-language explanation of
  what the proposed changes do (or why there are none).
"""


class SettingsPathError(ValueError):
    """A computed or supplied `.claude/` path would escape the control-center directory."""


def sanitize_slug(raw: str) -> str:
    """Turn an LLM-proposed name/path hint into a safe kebab-case slug.

    Only the final path segment is considered (any directory components in
    the hint are discarded, not honored) and a trailing extension is
    stripped; the result contains only `[a-z0-9-]`, never `.`/`/`/`\\` or
    `..`, so it cannot be used to escape `.claude/`.
    """
    last_segment = re.split(r"[\\/]", raw.strip())[-1]
    stem = re.sub(r"\.[A-Za-z0-9]+$", "", last_segment)
    slug = re.sub(r"[^a-z0-9]+", "-", stem.strip().lower()).strip("-")
    # Cap length -- an arbitrarily long LLM-proposed hint could otherwise exceed
    # OS filename limits.
    return (slug or "unnamed")[:64]


def compute_file_path(claude_dir: Path, target_category: TargetCategory, file_path_hint: str) -> Path:
    """Deterministically compute the authoritative on-disk path for a change.

    Never trusts `file_path_hint` as a path -- for fixed-name categories it is
    ignored entirely; for named categories only its sanitized final segment
    (the slug) is used. Raises `SettingsPathError` if the result would
    resolve outside `claude_dir` (defense in depth -- sanitize_slug already
    makes this unreachable in practice).
    """
    claude_dir_resolved = claude_dir.resolve()

    if target_category in _FIXED_RELATIVE_PATHS:
        relative = Path(_FIXED_RELATIVE_PATHS[target_category])
    else:
        subdir, nest_under_slug = _SLUG_CATEGORY_SUBDIR[target_category]
        slug = sanitize_slug(file_path_hint)
        relative = Path(subdir) / (f"{slug}/{slug}.md" if nest_under_slug else f"{slug}.md")

    resolved = (claude_dir_resolved / relative).resolve()
    if resolved != claude_dir_resolved and claude_dir_resolved not in resolved.parents:
        raise SettingsPathError(f"Computed path '{resolved}' escapes control-center directory '{claude_dir_resolved}'")
    return resolved


def display_path(claude_dir: Path, resolved_path: Path) -> str:
    """Render an absolute on-disk path as the `.claude/...`-relative string the UI shows."""
    relative = resolved_path.resolve().relative_to(claude_dir.resolve())
    return f"{claude_dir.name}/{relative.as_posix()}"


def _read_claude_dir_context(claude_dir: Path) -> str:
    """Read the current on-disk `.claude/` state as classification context.

    No cached snapshot (Boundaries) -- this always walks the live directory.
    Returns a bounded plain-text listing; if `.claude/` doesn't exist yet,
    says so explicitly (first-run case).
    """
    if not claude_dir.exists():
        return "(.claude/ does not exist yet -- this will be the first file written there.)"

    chunks: list[str] = []
    total_chars = 0
    for path in sorted(claude_dir.rglob("*")):
        if not path.is_file():
            continue
        if any(part in _SKIP_DIR_NAMES for part in path.parts):
            continue
        relative = path.relative_to(claude_dir).as_posix()
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        truncated = text[:_MAX_CHARS_PER_FILE]
        if len(text) > _MAX_CHARS_PER_FILE:
            truncated += "\n...(truncated)"
        entry = f"### {claude_dir.name}/{relative}\n{truncated}\n"
        if total_chars + len(entry) > _MAX_CONTEXT_CHARS:
            chunks.append("...(remaining .claude/ files omitted for length)")
            break
        chunks.append(entry)
        total_chars += len(entry)

    if not chunks:
        return f"({claude_dir.name}/ exists but is empty.)"
    return "\n".join(chunks)


def classify_request(user_request: str, claude_dir: Path, client: anthropic.Anthropic) -> SettingsRouterOutput:
    """Classify a natural-language request into structured `.claude/` proposals.

    Reads live on-disk `.claude/` state as context, calls
    `client.messages.parse()` against the `SettingsRouterOutput` schema, then
    overwrites each returned action's `file_path` with the server-computed,
    containment-validated path (Boundaries: never trust the LLM's path).
    Raises whatever `anthropic.APIError` subclass the SDK raises on failure
    (rate limit, timeout, auth, ...) -- callers surface that as the app-wide
    error envelope; nothing is written here regardless.
    """
    context = _read_claude_dir_context(claude_dir)
    user_content = (
        f"Current .claude/ state:\n\n{context}\n\n---\n\nDeveloper request:\n{user_request}"
    )

    try:
        response = client.messages.parse(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
            output_format=SettingsRouterOutput,
        )
    except TypeError as exc:
        # The SDK raises a bare TypeError (not an anthropic.APIError) when it can't
        # resolve any credentials at all (e.g. ANTHROPIC_API_KEY unset). Normalize
        # it into the anthropic.AnthropicError family so callers only ever need to
        # handle one exception hierarchy for "the LLM call failed".
        raise anthropic.AnthropicError(str(exc)) from exc
    parsed = response.parsed_output
    if parsed is None:
        # `ParsedMessage.parsed_output` is Optional -- reachable on truncation,
        # a refusal, or any response that isn't parseable text, not just a
        # type-checker artifact.
        raise anthropic.AnthropicError("Claude did not return structured output")

    resolved_updates = []
    seen_paths: set[Path] = set()
    for update in parsed.updates:
        resolved_path = compute_file_path(claude_dir, update.target_category, update.file_path)
        resolved_path = _dedupe_resolved_path(claude_dir, update.target_category, update.file_path, resolved_path, seen_paths)
        seen_paths.add(resolved_path)
        resolved_updates.append(update.model_copy(update={"file_path": display_path(claude_dir, resolved_path)}))

    return parsed.model_copy(update={"updates": resolved_updates})


def _dedupe_resolved_path(
    claude_dir: Path,
    target_category: TargetCategory,
    file_path_hint: str,
    resolved_path: Path,
    seen: set[Path],
) -> Path:
    """Disambiguate a resolved path that collides with an earlier update in the
    same classification response.

    Two updates in one response can independently sanitize to the same slug
    (e.g. two unnamed `rule` actions both landing on `rules/unnamed.md`) --
    approving both would silently let the second overwrite the first with no
    warning shown anywhere. Only named categories (`rule`/`skill`/`command`/
    `agent`) can be disambiguated this way -- a fixed-path category
    (`team_instructions`, `settings.json`, ...) has nowhere else to go, so a
    collision there is left as-is (it's two edits to the same singleton
    file, not a naming accident).
    """
    if target_category not in _SLUG_CATEGORY_SUBDIR or resolved_path not in seen:
        return resolved_path

    base_slug = sanitize_slug(file_path_hint)
    suffix = 2
    candidate = compute_file_path(claude_dir, target_category, f"{base_slug}-{suffix}")
    while candidate in seen:
        suffix += 1
        candidate = compute_file_path(claude_dir, target_category, f"{base_slug}-{suffix}")
    return candidate
