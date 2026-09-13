"""Flight path + cost estimate (Story 2.3): a pure-Python, deterministic pass
over one agent's already-resolved context graph -- no second LLM call (AD-7).

`select_flight_path` is called once per agent, after `decompose._resolve_agent_nodes`
has already sanitized/deduped/remapped that agent's `nodes`/`neighbors` in its
own per-agent namespace. It never talks to the LLM and never trusts the LLM
for `flight_path`/`estimated_tokens`/`estimated_duration_seconds` even though
those fields exist on the same `AgentSpec` schema Claude fills in -- they are
always overwritten here (mirrors `node_id`'s "hint, always overwritten"
precedent, Boundaries).

Rules (Boundaries):
- Flight path = exactly the `required=true` nodes on that agent, ordered by a
  DFS over their own `neighbors` -- local relations only, no global
  lookahead across the whole graph.
- Token cost per node: a required `codebase_file` node whose `source_ref`
  resolves to a real file *under* `project_root` costs that file's real size
  (`chars/4`); every other node (including a `codebase_file` node with a
  missing/hallucinated `source_ref`) costs a flat constant.
- Duration = total tokens / a throughput constant, plus a per-round-trip
  constant for every required `mcp` node on the path.
- Dollar cost = total tokens * a placeholder fixed per-token rate (Design
  Notes: no per-agent model is pinned yet -- same "reproducible placeholder
  constant" treatment as the duration throughput/round-trip figures, not a
  real per-model quote).
- Budget is informational only: the path always covers every required node
  regardless of cost -- nothing here ever drops a required node.
"""

from __future__ import annotations

from pathlib import Path

from .models import AgentSpec, Node

# Deterministic placeholder constants (Design Notes: there is no separate
# "budget" to tune against -- these just make the estimate reproducible).
# Flat token cost for any node whose real size can't be measured (every
# non-codebase_file source, and a codebase_file node whose source_ref
# doesn't resolve to a real file under project_root).
_FLAT_NODE_TOKEN_COST = 500

# Above this many bytes, skip reading a required codebase_file node's
# content entirely and estimate its cost from its on-disk size instead --
# a cost *estimate* has no need to fully load an oversized file into memory
# just to count its characters.
_MAX_READ_BYTES = 2_000_000

# Assumed processing throughput, in tokens per second, used to turn a total
# token estimate into a duration estimate.
_TOKENS_PER_SECOND = 250.0

# Flat latency added per required `mcp` node, representing that node's
# round-trip tool-call overhead on top of raw token throughput.
_MCP_ROUND_TRIP_SECONDS = 1.5

# Placeholder per-token dollar rate used to turn a total token estimate into
# a dollar-cost estimate -- Claude Sonnet 5 input pricing ($2 / 1M tokens),
# chosen as a reasonable default since no per-agent model is pinned yet
# (Design Notes). Revisit once real per-agent model selection exists.
_USD_PER_TOKEN = 2.0 / 1_000_000


def _resolve_under_project(project_root: Path, source_ref: str) -> Path | None:
    """Resolve `source_ref` against `project_root` and return it only if it
    is a real file *and* actually lives under `project_root` -- never trust
    an LLM-proposed `source_ref` as a safe, in-bounds path (mirrors
    `sanitize_slug`'s treatment of LLM-proposed path hints elsewhere in this
    package). Returns `None` on any missing/hallucinated/out-of-bounds path,
    never raises.
    """
    try:
        resolved = (project_root / source_ref).resolve()
        root_resolved = project_root.resolve()
    except (OSError, ValueError, RuntimeError):
        # OSError: e.g. a component too long / invalid on this platform.
        # ValueError: e.g. an embedded null byte in the path string.
        # RuntimeError: `Path.resolve()` raises this on a symlink loop.
        # Any of these means the LLM-proposed source_ref is malformed --
        # treat it exactly like a missing file, never propagate.
        return None
    if not resolved.is_file():
        return None
    try:
        resolved.relative_to(root_resolved)
    except ValueError:
        # Resolves to a real file, but outside project_root (e.g. a
        # "../../etc/passwd"-style source_ref) -- treat exactly like a
        # missing file, not a security exception.
        return None
    return resolved


def _node_token_cost(node: Node, project_root: Path) -> int:
    """Real file size (ceiling of `chars/4`) for a required `codebase_file`
    node whose `source_ref` resolves to a real file under `project_root`;
    the flat constant otherwise (I/O matrix rows 2-3).

    For a cost *estimate*, underestimating is the riskier direction, so
    character counts are rounded up (never down) to a whole token. A file
    over `_MAX_READ_BYTES` is never fully read into memory -- its cost is
    estimated straight from its on-disk byte size instead (also rounded up).
    """
    if node.source == "codebase_file" and node.source_ref:
        resolved = _resolve_under_project(project_root, node.source_ref)
        if resolved is not None:
            try:
                size = resolved.stat().st_size
            except OSError:
                return _FLAT_NODE_TOKEN_COST
            if size > _MAX_READ_BYTES:
                return -(-size // 4)
            try:
                chars = len(resolved.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                return _FLAT_NODE_TOKEN_COST
            return -(-chars // 4)
    return _FLAT_NODE_TOKEN_COST


def _order_required_nodes(required_nodes: list[Node]) -> list[str]:
    """DFS pre-order traversal over `neighbors`, restricted to this agent's
    own required nodes (AD-7: local relations only, no global lookahead).
    Traversal starts from each required node in its original `nodes`-list
    order (so the result is deterministic even when the graph has more than
    one connected component), and a neighbor pointing at a non-required (or
    dangling) node_id is simply not followed -- it was already dropped/kept
    out of `by_id` upstream.

    Implemented as an explicit-stack iterative DFS (rather than recursive)
    so an arbitrarily long chain of required nodes can never overflow
    Python's call stack with a `RecursionError`.
    """
    by_id = {node.node_id: node for node in required_nodes}
    visited: set[str] = set()
    order: list[str] = []

    for node in required_nodes:
        if node.node_id in visited:
            continue
        stack = [node.node_id]
        while stack:
            node_id = stack.pop()
            if node_id in visited:
                continue
            visited.add(node_id)
            order.append(node_id)
            # Push neighbors in reverse so they pop off the stack (and thus
            # get visited) in the same left-to-right order the old
            # recursive pre-order DFS visited them in.
            neighbors = [n for n in by_id[node_id].neighbors if n in by_id]
            stack.extend(reversed(neighbors))
    return order


def select_flight_path(agent: AgentSpec, project_root: Path) -> AgentSpec:
    """Return `agent` with `flight_path`/`estimated_tokens`/
    `estimated_duration_seconds`/`estimated_cost_usd` server-computed,
    overwriting whatever the LLM proposed for those four fields
    (Boundaries).

    No required nodes (or an empty `nodes` list) -> `flight_path` is `[]`
    and all three estimates are `0` (I/O matrix row 4).
    """
    required_nodes = [node for node in agent.nodes if node.required]
    if not required_nodes:
        return agent.model_copy(
            update={
                "flight_path": [],
                "estimated_tokens": 0,
                "estimated_duration_seconds": 0.0,
                "estimated_cost_usd": 0.0,
            }
        )

    path = _order_required_nodes(required_nodes)
    by_id = {node.node_id: node for node in required_nodes}

    total_tokens = sum(_node_token_cost(by_id[node_id], project_root) for node_id in path)
    mcp_count = sum(1 for node_id in path if by_id[node_id].source == "mcp")
    duration = (total_tokens / _TOKENS_PER_SECOND) + (mcp_count * _MCP_ROUND_TRIP_SECONDS)
    cost_usd = total_tokens * _USD_PER_TOKEN

    return agent.model_copy(
        update={
            "flight_path": path,
            "estimated_tokens": total_tokens,
            "estimated_duration_seconds": duration,
            "estimated_cost_usd": cost_usd,
        }
    )
