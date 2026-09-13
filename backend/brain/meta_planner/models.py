"""Pydantic contract for the Meta-Planner (Story 2.1, extended in Story 2.2).

`DagBlueprint` is the exact shape `client.messages.parse()` is asked to fill
in (see `decompose.py`), mirroring the Settings Router's
`SettingsRouterOutput` precedent (`brain/settings_router/models.py`). Per
spec Boundaries: "`node_id`s are sanitized and dedup-checked server-side --
never trust the LLM's slug for uniqueness" -- the `node_id` (and any
`parent_id`/`depends_on` reference to it) on a parsed `AgentSpec` is treated
as an unvalidated hint only; `decompose.decompose_task()` overwrites every
`node_id` with a sanitized, deduped slug and remaps references accordingly
before returning. Story 2.2 extends this same treatment to each agent's
`Node.node_id`/`neighbors`, in that node's own per-agent namespace (Design
Notes: a node_id only needs to be unique within its own agent's `nodes`
list, never globally).

Design Notes: `AgentSpec.nodes` (Story 2.2) is the unified `Node` model --
per AD-2, one entity carries both context-graph fields (topic, source,
neighbors -- populated by the Meta-Planner at planning time) and
execution/telemetry fields (`status`, `telemetry`, `live_stream`,
`checkpoint_ref` -- left `None`, pre-provisioned for the Engine to write
later). The Meta-Planner never writes to the checkpoint store and never
sets execution fields itself (AD-8).
"""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Node(BaseModel):
    """One subtopic node in an agent's context graph (Story 2.2).

    Context-graph fields (`topic`, `source`, `source_ref`, `neighbors`) are
    populated by the Meta-Planner at planning time. Execution/telemetry
    fields are pre-provisioned but left unset (`None`) here -- the Engine is
    the sole writer of `status` and the rest, once a run actually executes
    (AD-2/AD-8). This is the same `Node` entity, not a separate
    context-only type.
    """

    node_id: str = Field(
        description=(
            "A short, descriptive identifier for this node, unique within "
            "its own agent's nodes list only (naming hint, not "
            "guaranteed-unique -- sanitized server-side, mirroring "
            "AgentSpec.node_id)."
        )
    )
    topic: str = Field(description="Short, plain-language subtopic this node represents.")
    source: Literal["mcp", "local_docs", "codebase_file", "claude_context"] = Field(
        description=(
            "Where this node's context comes from. 'codebase_file' only "
            "when the project snapshot shows real source files to cite -- "
            "never invent a path for a new/empty codebase. 'mcp' is always "
            "LLM-proposed (no real MCP registry exists yet)."
        )
    )
    source_ref: str | None = Field(
        default=None,
        description=(
            "A concrete reference for this node's source, e.g. a real "
            "relative file path when source='codebase_file'. May be null "
            "for sources with no single concrete reference."
        ),
    )
    neighbors: list[str] = Field(
        default_factory=list,
        description=(
            "node_ids of topically-related nodes on this same agent. Every "
            "entry must be a node_id present elsewhere in this same "
            "agent's nodes list -- never a dangling reference."
        ),
    )

    # Execution/telemetry fields (AD-2): pre-provisioned, always unset by
    # the Meta-Planner. The Engine (never the Brain) writes these once a
    # run executes (AD-8/AD-5). Kept loosely typed here -- the pinned
    # `TelemetryEvent`/status-enum contracts are introduced by the Engine
    # stories that actually write them.
    status: str | None = Field(default=None, description="Engine-owned. Always null from the Meta-Planner.")
    telemetry: dict | None = Field(default=None, description="Engine-owned. Always null from the Meta-Planner.")
    live_stream: dict | None = Field(default=None, description="Engine-owned. Always null from the Meta-Planner.")
    checkpoint_ref: str | None = Field(default=None, description="Engine-owned. Always null from the Meta-Planner.")

    @model_validator(mode="after")
    def _codebase_file_requires_source_ref(self) -> "Node":
        if self.source == "codebase_file" and not (self.source_ref or "").strip():
            raise ValueError("source_ref must be a non-empty string when source='codebase_file'")
        return self


class AgentSpec(BaseModel):
    """One agent in a decomposed task: the main orchestrator or one subagent."""

    node_id: str = Field(
        description=(
            "A short, descriptive identifier for this agent (e.g. "
            "'main_orchestrator', 'auth_scaffold_worker'). This is only a "
            "naming hint -- the server sanitizes it into a unique slug "
            "before returning; do not rely on it being unique yourself."
        )
    )
    parent_id: str | None = Field(
        description=(
            "The node_id of this agent's coordinator in the DAG. Exactly "
            "one agent in the whole response has parent_id=null -- the "
            "main orchestrator. Every other agent's parent_id must be "
            "another node_id present in this same response."
        )
    )
    responsibility: str = Field(
        description="One-line, plain-language description of what this agent is responsible for."
    )
    depends_on: list[str] = Field(
        default_factory=list,
        description=(
            "node_ids of other agents in this same response that must "
            "complete before this one starts. Every entry must be a "
            "node_id present elsewhere in this same agents list -- never a "
            "dangling reference."
        ),
    )
    nodes: list[Node] = Field(
        default_factory=list,
        description=(
            "This agent's context graph: subtopic nodes it will draw from, "
            "each tagged with its source and connected to topically- "
            "related neighbors within this same agent's nodes list. Every "
            "agent, including the main orchestrator, gets a non-empty "
            "nodes list where the project has any subtopics to name."
        ),
    )


class DagBlueprint(BaseModel):
    """Top-level structured-output schema for one decomposition call."""

    intent: str = Field(description="The original developer intent this blueprint decomposes.")
    agents: list[AgentSpec] = Field(default_factory=list)
