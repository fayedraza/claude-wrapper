"""Meta-Planner (Story 2.1): decompose a plain-language developer intent into
a main orchestrator plus subagents, previewed before anything runs.

See `decompose.py` for the LLM call and `models.py` for the structured-output
contract (`AgentSpec`/`DagBlueprint`) it fills in. Read-only, preview-only:
this package never writes `.claude/`, never touches a checkpoint store, and
never executes anything -- that's later epics (2.2/2.3 for the context graph,
flight path, and cost estimate; Epic 3 for approve/reject and execution).
"""
