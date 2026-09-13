"""Meta-Planner task decomposition (Story 2.1): a submitted developer intent
-> a `DagBlueprint` preview (main orchestrator + subagents), nothing written
or executed.

`decompose_task()` reads the on-disk project root as bounded context, asks
Claude to decompose the intent into structured `AgentSpec`s via
`client.messages.parse()` -- following the Settings Router's LLM-call
pattern exactly (see `brain/settings_router/router.py:classify_request`) --
then sanitizes and dedup-checks every `node_id` server-side (reusing
`sanitize_slug`) and remaps every `parent_id`/`depends_on` reference to the
resolved slugs before returning. The LLM's own slug is never trusted for
uniqueness (Boundaries).
"""

from __future__ import annotations

import fnmatch
from pathlib import Path

import anthropic

from brain.settings_router.router import sanitize_slug

from .models import AgentSpec, DagBlueprint, Node

MODEL = "claude-opus-5"
MAX_TOKENS = 8000

# Bound how much of the project root is fed to the decomposer per file and
# overall, so a large codebase can't blow the context window -- same
# thresholds as the Settings Router's .claude/ context read.
_MAX_CHARS_PER_FILE = 4000
_MAX_CONTEXT_CHARS = 60000
_SKIP_DIR_NAMES = {".git", ".claude", "node_modules", "__pycache__", ".venv", "venv"}

# Filenames that commonly hold secrets -- never read these into the context
# sent to Claude's API, even though they aren't in a skipped directory.
# Matched against the filename only (fnmatch, case-sensitive), not the full
# path.
_SECRET_FILE_PATTERNS = (
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "id_rsa*",
    "*.p12",
    "*credentials*.json",
    ".npmrc",
    ".netrc",
)


def _is_secret_file(name: str) -> bool:
    return any(fnmatch.fnmatch(name, pattern) for pattern in _SECRET_FILE_PATTERNS)


SYSTEM_PROMPT = """\
You are the Meta-Planner for Claude Wrapper, a tool that runs a main
orchestrator agent plus subagents against a project to accomplish a
developer's plain-language task.

Given a developer's intent and a snapshot of the project root, decompose the
task into exactly one main orchestrator agent plus zero or more subagents.

Rules:
- Exactly one agent has parent_id=null -- the main orchestrator that
  coordinates every other agent. Every other agent's parent_id must be the
  node_id of another agent in your response (its coordinator).
- Every depends_on entry must be the node_id of another agent in your
  response -- never a dangling reference, never a node_id you didn't also
  emit as an agent.
- Give each agent a short, descriptive node_id (e.g. "main_orchestrator",
  "auth_scaffold_worker") -- this is only a naming hint, not a guaranteed
  unique identifier.
- responsibility is one short, plain-language sentence describing what that
  agent does -- not a multi-step plan or a list.
- If the project root snapshot shows no source files yet (a new/empty
  codebase), scope the agents to greenfield setup work instead of assuming
  existing code or conventions.
- This is a preview only. Do not propose executing anything, writing files,
  or any action beyond planning the agents themselves.

For every agent (including the main orchestrator), also propose its context
graph: a `nodes` list of subtopic nodes the agent will draw from to do its
work.
- Each node has a `topic` (short, plain-language subtopic), a `source`, and
  optionally a `source_ref`.
- `source` must be exactly one of:
  - "codebase_file" -- a real file shown in the project root snapshot. Only
    use this source if the snapshot actually shows source files; set
    `source_ref` to the real relative path shown in the snapshot. Never
    invent a path, and never use "codebase_file" for a new/empty codebase.
  - "local_docs" -- project documentation/config the agent would read.
  - "claude_context" -- context already available to the agent from its own
    instructions/conversation, with no separate file.
  - "mcp" -- a hypothetical MCP tool/resource this agent would use. No real
    MCP registry exists yet, so this is always a proposal, not a real
    connection.
- Give each node a short, descriptive node_id (like agent node_ids, this is
  only a naming hint, not a guaranteed-unique identifier) -- it only needs
  to be unique within this one agent's own nodes list, not across agents.
- `neighbors` lists node_ids of topically-related nodes on the *same* agent.
  Every neighbor entry must be a node_id you also emitted as a node for that
  same agent -- never a dangling reference, never another agent's node_id.
- Give every agent at least one node when the project/intent gives you
  anything to name; an agent with genuinely nothing to draw from can have an
  empty nodes list.
"""


class MetaPlannerValidationError(ValueError):
    """The submitted intent is blank or whitespace-only. No LLM call is made."""


class MetaPlannerLLMError(anthropic.AnthropicError):
    """The LLM call failed (API error, timeout, missing credentials) or
    returned no parseable structured output."""


def _read_project_context(project_root: Path) -> str:
    """Read a bounded snapshot of the project root as decomposition context.

    Skips `.claude/`, `.git/`, and common build/dependency directories, plus
    well-known secret-bearing filenames (`.env`, `*.pem`, `id_rsa*`, etc. --
    see `_SECRET_FILE_PATTERNS`) so credentials are never sent to Claude's
    API as decomposition context. If nothing else exists, says so explicitly
    so the LLM scopes agents for a greenfield/new codebase rather than
    assuming existing code.
    """
    if not project_root.exists():
        return "(project root does not exist yet -- treat this as a new, empty codebase.)"

    chunks: list[str] = []
    total_chars = 0
    for path in sorted(project_root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in _SKIP_DIR_NAMES for part in path.parts):
            continue
        if _is_secret_file(path.name):
            continue
        relative = path.relative_to(project_root).as_posix()
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        truncated = text[:_MAX_CHARS_PER_FILE]
        if len(text) > _MAX_CHARS_PER_FILE:
            truncated += "\n...(truncated)"
        entry = f"### {relative}\n{truncated}\n"
        if total_chars + len(entry) > _MAX_CONTEXT_CHARS:
            chunks.append("...(remaining project files omitted for length)")
            break
        chunks.append(entry)
        total_chars += len(entry)

    if not chunks:
        return "(project root has no files beyond .claude/ and .git -- treat this as a new, empty codebase.)"
    return "\n".join(chunks)


def _dedupe_slug(base_slug: str, seen: set[str]) -> str:
    """Disambiguate a sanitized slug that collides with an earlier agent in
    the same decomposition response (mirrors
    `settings_router.router._dedupe_resolved_path`'s suffix scheme)."""
    if base_slug not in seen:
        return base_slug
    suffix = 2
    candidate = f"{base_slug}-{suffix}"
    while candidate in seen:
        suffix += 1
        candidate = f"{base_slug}-{suffix}"
    return candidate


def _resolve_agent_nodes(nodes: list[Node]) -> list[Node]:
    """Sanitize/dedup/remap one agent's `nodes` list in its own per-agent
    namespace (Design Notes: a node_id only needs to be unique within its
    own agent's nodes, never globally) -- mirrors the agent-level
    node_id/parent_id/depends_on pass above, applied to Node.node_id/
    neighbors instead. Unlike agent parent_id, a dangling neighbor entry
    has no "manufactures a second root" failure mode, so it's always
    dropped silently (Boundaries), never an error.
    """
    # Pass 1: sanitize + dedup every node_id in this agent's own namespace.
    # Keyed by the LLM's raw (untrusted) node_id string; if two nodes share
    # the exact same raw node_id, only the first occurrence's mapping is
    # kept -- otherwise the second would silently overwrite it and a
    # neighbor reference to that shared raw id would resolve to the wrong
    # (second) node, leaving the first unreachable by reference.
    node_id_map: dict[str, str] = {}
    seen_slugs: set[str] = set()
    resolved_nodes: list[Node] = []
    for node in nodes:
        slug = _dedupe_slug(sanitize_slug(node.node_id), seen_slugs)
        seen_slugs.add(slug)
        if node.node_id not in node_id_map:
            node_id_map[node.node_id] = slug
        resolved_nodes.append(node.model_copy(update={"node_id": slug}))

    # Pass 2: remap neighbors to the resolved slugs, dropping any entry that
    # doesn't resolve to a node_id in this same agent's nodes list, dropping
    # a self-reference (a node is never topically related to itself), and
    # deduplicating while preserving order. Also force the Engine-owned
    # execution/telemetry fields back to None regardless of what the LLM
    # returned -- never trust the LLM for Engine-owned fields (AD-2/AD-8),
    # mirroring the Settings Router's treatment of `file_path`.
    final_nodes: list[Node] = []
    for node in resolved_nodes:
        remapped_neighbors = [
            node_id_map[n] for n in node.neighbors if n in node_id_map and node_id_map[n] != node.node_id
        ]
        remapped_neighbors = list(dict.fromkeys(remapped_neighbors))
        final_nodes.append(
            node.model_copy(
                update={
                    "neighbors": remapped_neighbors,
                    "status": None,
                    "telemetry": None,
                    "live_stream": None,
                    "checkpoint_ref": None,
                }
            )
        )
    return final_nodes


def decompose_task(intent: str, project_root: Path, client: anthropic.Anthropic) -> DagBlueprint:
    """Decompose a developer intent into a `DagBlueprint`. Read-only,
    preview-only: no `.claude/` write, no checkpoint store, nothing executes
    (Boundaries).

    Also sanitizes/dedupes/remaps each agent's own `nodes`/`neighbors` in
    that agent's per-agent namespace (`_resolve_agent_nodes`), not just the
    agent-level `node_id`/`parent_id`/`depends_on` handled below.

    Raises `MetaPlannerValidationError` on a blank/whitespace intent (no LLM
    call made) and `MetaPlannerLLMError` on any LLM failure or empty parsed
    output.
    """
    if not intent.strip():
        raise MetaPlannerValidationError("intent must not be blank")

    context = _read_project_context(project_root)
    user_content = f"Project root snapshot:\n\n{context}\n\n---\n\nDeveloper intent:\n{intent}"

    try:
        response = client.messages.parse(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
            output_format=DagBlueprint,
        )
    except TypeError as exc:
        # Mirrors classify_request: the SDK raises a bare TypeError (not an
        # anthropic.APIError) when it can't resolve any credentials at all.
        raise MetaPlannerLLMError(str(exc)) from exc
    except anthropic.AnthropicError as exc:
        raise MetaPlannerLLMError(str(exc)) from exc

    parsed = response.parsed_output
    if parsed is None:
        # `ParsedMessage.parsed_output` is Optional -- reachable on
        # truncation, a refusal, or any response that isn't parseable text,
        # not just a type-checker artifact.
        raise MetaPlannerLLMError("Claude did not return structured output")

    # Pass 1: sanitize + dedup every node_id, keyed by the LLM's original
    # (untrusted) node_id string so pass 2 can remap parent_id/depends_on
    # references against it.
    node_id_map: dict[str, str] = {}
    seen_slugs: set[str] = set()
    resolved_agents: list[AgentSpec] = []
    for agent in parsed.agents:
        slug = _dedupe_slug(sanitize_slug(agent.node_id), seen_slugs)
        seen_slugs.add(slug)
        node_id_map[agent.node_id] = slug
        resolved_agents.append(agent.model_copy(update={"node_id": slug}))

    # Pass 2: remap parent_id/depends_on to the resolved slugs. depends_on
    # entries that don't resolve to a node_id in this response are dropped
    # (Boundaries: no dangling reference) rather than passed through raw. A
    # non-null parent_id that doesn't resolve is different -- silently
    # falling back to None would manufacture a second apparent root, so
    # that's treated as an unparseable/invalid response instead (Boundaries:
    # "every other parent_id/depends_on entry resolves to a node_id in the
    # same response").
    final_agents: list[AgentSpec] = []
    for agent in resolved_agents:
        if agent.parent_id is None:
            remapped_parent = None
        elif agent.parent_id in node_id_map:
            remapped_parent = node_id_map[agent.parent_id]
        else:
            raise MetaPlannerLLMError(
                f"Claude returned a parent_id ({agent.parent_id!r}) that does not "
                "match any node_id in the same response"
            )
        remapped_depends_on = [node_id_map[dep] for dep in agent.depends_on if dep in node_id_map]
        resolved_nodes = _resolve_agent_nodes(agent.nodes)
        final_agents.append(
            agent.model_copy(
                update={
                    "parent_id": remapped_parent,
                    "depends_on": remapped_depends_on,
                    "nodes": resolved_nodes,
                }
            )
        )

    # AC #1 / Boundaries: exactly one agent has parent_id=null. Zero (every
    # parent_id was non-null, or the response was empty) or more than one
    # (a malformed/ambiguous response) both indicate Claude didn't follow
    # the contract -- treat as an LLM error rather than returning a
    # blueprint with no single root or multiple apparent roots.
    root_count = sum(1 for agent in final_agents if agent.parent_id is None)
    if root_count != 1:
        raise MetaPlannerLLMError(
            f"Claude returned {root_count} agents with parent_id=null; exactly one is required"
        )

    return parsed.model_copy(update={"agents": final_agents})
