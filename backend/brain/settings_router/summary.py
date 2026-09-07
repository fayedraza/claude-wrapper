"""Read-only "Currently configured" summary (FR-3): walk live `.claude/` state.

`get_current_configuration()` is the only entry point. It never writes
anything and never caches -- every call walks `.claude/rules/*.md` and
`.claude/agents/*.md` fresh (same "no cached snapshot" rule as
`router.classify_request`), and checks `settings.json`/`settings.local.json`
for a `permissionGrants` key (Boundaries: namespaced deliberately distinct
from Claude Code's own reserved `permissions` key).

A genuine directory-level failure (e.g. permission denied listing `rules/`
or `agents/`) is deliberately left unguarded here (see `_list_markdown_files`)
so it propagates up to the gateway's global `@app.exception_handler(OSError)`
-- the same mechanism `/api/settings/apply` relies on -- rather than being
silently reported as "nothing configured" (I/O matrix: "Fetch fails --
Error envelope surfaced").
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from .models import ConfigSummaryItem, CurrentConfiguration
from .router import display_path

_SETTINGS_FILENAMES = ("settings.json", "settings.local.json")

# `---\n...\n---` YAML frontmatter block at the very start of a file, matching
# this repo's own SKILL.md convention (Design Notes).
_FRONTMATTER_RE = re.compile(r"\A---[ \t]*\n(.*?\n)---[ \t]*\n?", re.DOTALL)

_HEADING_MARKUP_RE = re.compile(r"^#+\s*")


def get_current_configuration(claude_dir: Path) -> CurrentConfiguration:
    """Build the full "Currently configured" summary from live on-disk state.

    If `.claude/` doesn't exist yet (fresh repo), returns an empty summary --
    a friendly empty state, not an error (I/O matrix).
    """
    if not claude_dir.exists():
        return CurrentConfiguration(items=[])

    items: list[ConfigSummaryItem] = []
    items.extend(_rule_items(claude_dir))
    items.extend(_agent_items(claude_dir))
    items.extend(_permission_grant_items(claude_dir))
    return CurrentConfiguration(items=items)


# ---- rules ----------------------------------------------------------------


def _rule_items(claude_dir: Path) -> list[ConfigSummaryItem]:
    rules_dir = claude_dir / "rules"
    if not rules_dir.is_dir():
        return []

    items: list[ConfigSummaryItem] = []
    for path in _list_markdown_files(rules_dir):
        text = _read_text(path)
        if text is None:
            continue
        # Design Notes: rule "text" is the first non-empty content line,
        # heading markup stripped.
        line = _HEADING_MARKUP_RE.sub("", _first_non_empty_line(text)).strip()
        items.append(ConfigSummaryItem(kind="rule", text=line or path.stem, path=display_path(claude_dir, path)))
    return items


# ---- agents -----------------------------------------------------------------


def _agent_items(claude_dir: Path) -> list[ConfigSummaryItem]:
    agents_dir = claude_dir / "agents"
    if not agents_dir.is_dir():
        return []

    items: list[ConfigSummaryItem] = []
    for path in _list_markdown_files(agents_dir):
        text = _read_text(path)
        if text is None:
            continue
        items.append(ConfigSummaryItem(kind="agent", text=_agent_text(path, text), path=display_path(claude_dir, path)))
    return items


def _agent_text(path: Path, text: str) -> str:
    """Design Notes: `"{name}: {description}"` from YAML frontmatter when
    present (matching this repo's own SKILL.md convention); else filename +
    first content line."""
    frontmatter, body = _split_frontmatter(text)
    if frontmatter is not None:
        name = frontmatter.get("name")
        description = frontmatter.get("description")
        # Guard against non-string frontmatter values (e.g. a YAML list or
        # number under `name`/`description`) -- only a real string pair is a
        # usable "{name}: {description}"; anything else falls through to the
        # filename + first-line fallback below.
        if isinstance(name, str) and name and isinstance(description, str) and description:
            return f"{name}: {description}"

    # Same heading-markup stripping as rule text (_rule_items) -- a fallback
    # first line of "# Some Heading" should read as "Some Heading", not keep
    # the literal "#".
    first_line = _HEADING_MARKUP_RE.sub("", _first_non_empty_line(body)).strip()
    return f"{path.stem}: {first_line}" if first_line else path.stem


def _split_frontmatter(text: str) -> tuple[dict[str, Any] | None, str]:
    """Split a leading `---`-delimited YAML frontmatter block off `text`.

    Returns `(None, text)` unchanged if there's no frontmatter block, the
    block doesn't parse as YAML, or it doesn't parse to a mapping --
    frontmatter is a best-effort heuristic (Design Notes), never assumed.
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return None, text

    body = text[match.end() :]
    try:
        parsed = yaml.safe_load(match.group(1))
    except (yaml.YAMLError, RecursionError):
        # RecursionError: a pathological alias/anchor expansion (YAML "billion
        # laughs") in a frontmatter block can blow the recursion limit during
        # parsing -- fall back the same as any other unparseable frontmatter
        # rather than letting it crash the request.
        return None, body

    if isinstance(parsed, dict):
        return parsed, body
    return None, body


# ---- permission grants (Story 1.4 owns the real schema) ---------------------


def _permission_grant_items(claude_dir: Path) -> list[ConfigSummaryItem]:
    """Show a row per entry under `permissionGrants` in `settings.json`/
    `settings.local.json`, only when that key is present.

    Boundaries/Never: this deliberately does not invent a permission-grant
    schema -- it only checks for the key's presence (absent today, so this
    always returns `[]` in practice) and, when present, renders whatever
    generic text it can find on each entry. Story 1.4 owns the real schema;
    once it writes real data under this same key, this should pick it up
    automatically without needing to change.
    """
    items: list[ConfigSummaryItem] = []
    for filename in _SETTINGS_FILENAMES:
        settings_path = claude_dir / filename
        if not settings_path.is_file():
            continue

        text = _read_text(settings_path)
        if text is None:
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict) or "permissionGrants" not in data:
            continue

        grants = data["permissionGrants"]
        if not isinstance(grants, list):
            continue

        path_display = display_path(claude_dir, settings_path)
        for grant in grants:
            items.append(ConfigSummaryItem(kind="mcp", text=_grant_text(grant), path=path_display))
    return items


def _grant_text(grant: Any) -> str:
    if isinstance(grant, dict):
        candidate = grant.get("text") or grant.get("description") or grant.get("name")
        if candidate:
            return str(candidate)
    elif isinstance(grant, str) and grant:
        return grant
    return "Permission grant"


# ---- shared helpers -----------------------------------------------------


def _list_markdown_files(dir_path: Path) -> list[Path]:
    """Sorted, non-recursive `*.md` files directly under `dir_path`.

    Deliberately `iterdir()`, not `glob("*.md")`: pathlib's `glob()` silently
    swallows `OSError` (e.g. `PermissionError`) while scanning a directory
    and just yields nothing, which would misreport a real access problem as
    "nothing configured here." `iterdir()` propagates it, so a genuine
    directory-level failure reaches the gateway's global
    `@app.exception_handler(OSError)` (I/O matrix: "Fetch fails -- Error
    envelope surfaced") instead of being hidden.
    """
    return sorted(path for path in dir_path.iterdir() if path.is_file() and path.suffix.lower() == ".md")


def _read_text(path: Path) -> str | None:
    """Read one file's text, or `None` if it can't be read.

    Deliberately asymmetric with `_list_markdown_files` above: a single
    unreadable *file* is caught and skipped here (that file's row is just
    omitted -- one bad file shouldn't hide every other rule/agent), while a
    *directory*-level failure (e.g. `rules/` itself unreadable) is left to
    propagate, because a whole-directory failure means the entire summary
    for that category can't be trusted and should surface as an error
    instead of silently reporting "nothing configured."
    """
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _first_non_empty_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""
