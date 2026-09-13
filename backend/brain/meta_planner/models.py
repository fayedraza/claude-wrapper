"""Pydantic contract for the Meta-Planner (Story 2.1).

`DagBlueprint` is the exact shape `client.messages.parse()` is asked to fill
in (see `decompose.py`), mirroring the Settings Router's
`SettingsRouterOutput` precedent (`brain/settings_router/models.py`). Per
spec Boundaries: "`node_id`s are sanitized and dedup-checked server-side --
never trust the LLM's slug for uniqueness" -- the `node_id` (and any
`parent_id`/`depends_on` reference to it) on a parsed `AgentSpec` is treated
as an unvalidated hint only; `decompose.decompose_task()` overwrites every
`node_id` with a sanitized, deduped slug and remaps references accordingly
before returning.

Design Notes: this shape is intentionally minimal -- `intent` + `agents`
only. Story 2.2 is expected to extend `AgentSpec` with a `nodes: list[Node]`
field (the unified Node model), not replace this shape.
"""

from pydantic import BaseModel, Field


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


class DagBlueprint(BaseModel):
    """Top-level structured-output schema for one decomposition call."""

    intent: str = Field(description="The original developer intent this blueprint decomposes.")
    agents: list[AgentSpec] = Field(default_factory=list)
