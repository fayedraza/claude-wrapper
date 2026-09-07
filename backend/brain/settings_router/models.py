"""Pydantic contract for the Settings Router (FR-1-FR-3).

`SettingsRouterOutput` is the exact shape `client.messages.parse()` is asked
to fill in (see `router.py`). Per spec Boundaries: "Compute `file_path`
server-side from `target_category` -- never trust the LLM's path" -- the
`file_path` on a parsed `SettingAction` is treated as an unvalidated hint
only; `router.classify_request()` overwrites it with the deterministically
computed, containment-checked path before anything is returned to the
frontend or accepted by `apply.apply_action()`.
"""

from typing import Literal

from pydantic import BaseModel, Field

# The 8 PRD target_category values verbatim (PRD FR-1) -- never add a 9th or
# rename one (e.g. "config", "MCP grant").
TargetCategory = Literal[
    "team_instructions",
    "local_instructions",
    "settings.json",
    "settings.local.json",
    "rule",
    "skill",
    "command",
    "agent",
]

ActionKind = Literal["create", "update", "revoke"]


class SettingAction(BaseModel):
    """One classified `.claude/` change, proposed or (on apply) approved."""

    target_category: TargetCategory
    file_path: str = Field(
        description=(
            "Proposed path under .claude/. When produced by the LLM this is "
            "only a hint (e.g. for the rule/skill/command/agent slug) -- "
            "never trusted directly for writes. When returned from "
            "classify_request() it is the authoritative, containment-"
            "checked relative path (e.g. '.claude/rules/testing.md')."
        )
    )
    content: str = Field(description="Full file content to write for create/update; ignored for revoke.")
    action: ActionKind


class SettingsRouterOutput(BaseModel):
    """Top-level structured-output schema for a single classification call."""

    user_summary: str = Field(
        description=(
            "Plain-language summary of the proposed changes as a whole. "
            "For a no-op request (nothing actionable), this explains why "
            "and `updates` is empty."
        )
    )
    updates: list[SettingAction] = Field(default_factory=list)


# Story 1.3 (FR-3): the "Currently configured" chip vocabulary from the UX
# mock (key-settings.html's `.config-kind.*`) -- deliberately distinct,
# informal, and unrelated to `TargetCategory` above. Never conflate the two
# or render `target_category` in a "Currently configured" row.
ConfigKind = Literal["rule", "agent", "mcp"]


class ConfigSummaryItem(BaseModel):
    """One read-only row in the "Currently configured" summary."""

    kind: ConfigKind
    text: str = Field(description="One-line description (Design Notes heuristics per kind).")
    path: str = Field(description="Display path, e.g. '.claude/rules/testing.md'.")


class CurrentConfiguration(BaseModel):
    """Top-level response for `GET /api/settings/current`."""

    items: list[ConfigSummaryItem] = Field(default_factory=list)
