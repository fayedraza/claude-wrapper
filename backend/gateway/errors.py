"""App-wide error envelope.

Architecture Data & formats convention: every error surfaced to the frontend
uses this single shape `{error_code, message, node_id}`, never a bespoke
per-feature shape. Settings has no run/agent node to attach an error to, so
`node_id` is always `null` here (see spec-1-2 Design Notes) rather than a
second envelope shape.
"""

from pydantic import BaseModel


class ErrorEnvelope(BaseModel):
    error_code: str
    message: str
    node_id: str | None = None
