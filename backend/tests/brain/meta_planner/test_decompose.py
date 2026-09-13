"""Unit tests for `brain.meta_planner.decompose` (Story 2.1)."""

from pathlib import Path

import anthropic
import httpx2
import pytest
from anthropic import APIConnectionError
from pydantic import ValidationError

from brain.meta_planner.decompose import (
    MetaPlannerLLMError,
    MetaPlannerValidationError,
    decompose_task,
)
from brain.meta_planner.models import AgentSpec, DagBlueprint, Node

# ---- happy path: existing vs. new/empty codebase -------------------------


def test_decompose_task_existing_codebase_returns_blueprint(project_root: Path, make_fake_client) -> None:
    (project_root / "app.py").write_text("print('hello')", encoding="utf-8")
    fake_output = DagBlueprint(
        intent="add OAuth2 login",
        agents=[
            AgentSpec(node_id="main_orchestrator", parent_id=None, responsibility="Coordinate auth rollout", depends_on=[]),
            AgentSpec(
                node_id="auth_scaffold_worker",
                parent_id="main_orchestrator",
                responsibility="Add OAuth2/JWT middleware",
                depends_on=[],
            ),
        ],
    )
    client = make_fake_client(output=fake_output)

    result = decompose_task("add OAuth2 login", project_root, client)

    assert result.intent == "add OAuth2 login"
    roots = [a for a in result.agents if a.parent_id is None]
    assert len(roots) == 1
    assert roots[0].node_id == "main-orchestrator"
    subagents = [a for a in result.agents if a.parent_id is not None]
    assert len(subagents) == 1
    assert subagents[0].parent_id == roots[0].node_id
    # Every depends_on entry resolves to a node_id present in the response.
    node_ids = {a.node_id for a in result.agents}
    for agent in result.agents:
        for dep in agent.depends_on:
            assert dep in node_ids
    # The project context fed to the LLM included the existing file.
    sent_context = client.messages.calls[0]["messages"][0]["content"]
    assert "app.py" in sent_context


def test_decompose_task_new_empty_codebase_returns_same_shape(project_root: Path, make_fake_client) -> None:
    fake_output = DagBlueprint(
        intent="scaffold a new service",
        agents=[
            AgentSpec(node_id="main_orchestrator", parent_id=None, responsibility="Coordinate scaffolding", depends_on=[]),
        ],
    )
    client = make_fake_client(output=fake_output)

    result = decompose_task("scaffold a new service", project_root, client)

    assert len(result.agents) == 1
    assert result.agents[0].parent_id is None
    # New/empty codebase -- the LLM is told explicitly, not left to guess.
    sent_context = client.messages.calls[0]["messages"][0]["content"]
    assert "new, empty codebase" in sent_context


def test_decompose_task_skips_claude_and_git_dirs(project_root: Path, make_fake_client) -> None:
    (project_root / ".claude").mkdir()
    (project_root / ".claude" / "settings.json").write_text("{}", encoding="utf-8")
    (project_root / ".git").mkdir()
    (project_root / ".git" / "config").write_text("[core]", encoding="utf-8")
    fake_output = DagBlueprint(
        intent="x",
        agents=[AgentSpec(node_id="main_orchestrator", parent_id=None, responsibility="x", depends_on=[])],
    )
    client = make_fake_client(output=fake_output)

    decompose_task("x", project_root, client)

    sent_context = client.messages.calls[0]["messages"][0]["content"]
    assert "settings.json" not in sent_context
    assert "config" not in sent_context
    assert "new, empty codebase" in sent_context


def test_decompose_task_never_sends_env_file_contents(project_root: Path, make_fake_client) -> None:
    """A `.env` file under project_root must never appear in the content sent
    to `client.messages.parse` -- secret-bearing filenames are excluded from
    the project context regardless of directory."""
    (project_root / ".env").write_text("SUPER_SECRET_API_KEY=sk-fake-0000000000\n", encoding="utf-8")
    (project_root / "app.py").write_text("print('hello')", encoding="utf-8")
    fake_output = DagBlueprint(
        intent="x",
        agents=[AgentSpec(node_id="main_orchestrator", parent_id=None, responsibility="x", depends_on=[])],
    )
    client = make_fake_client(output=fake_output)

    decompose_task("x", project_root, client)

    sent_context = client.messages.calls[0]["messages"][0]["content"]
    assert "SUPER_SECRET_API_KEY" not in sent_context
    assert "sk-fake-0000000000" not in sent_context
    assert "app.py" in sent_context


# ---- blank intent ----------------------------------------------------------


@pytest.mark.parametrize("blank", ["", "   ", "\n\t"])
def test_decompose_task_blank_intent_raises_without_llm_call(blank: str, project_root: Path, make_fake_client) -> None:
    client = make_fake_client(output=None)

    with pytest.raises(MetaPlannerValidationError):
        decompose_task(blank, project_root, client)

    assert client.messages.calls == []


# ---- LLM failure ------------------------------------------------------------


def test_decompose_task_llm_failure_raises_meta_planner_llm_error(project_root: Path, make_fake_client) -> None:
    error = APIConnectionError(request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"))
    client = make_fake_client(error=error)

    with pytest.raises(MetaPlannerLLMError):
        decompose_task("add OAuth2 login", project_root, client)


def test_decompose_task_normalizes_credential_resolution_type_error(project_root: Path, make_fake_client) -> None:
    error = TypeError("Could not resolve authentication method. Expected one of api_key, auth_token, ...")
    client = make_fake_client(error=error)

    with pytest.raises(MetaPlannerLLMError):
        decompose_task("add OAuth2 login", project_root, client)


def test_decompose_task_raises_when_parsed_output_is_none(project_root: Path, make_fake_client) -> None:
    client = make_fake_client(output=None)

    with pytest.raises(MetaPlannerLLMError):
        decompose_task("add OAuth2 login", project_root, client)


def test_meta_planner_llm_error_is_an_anthropic_error(project_root: Path, make_fake_client) -> None:
    """MetaPlannerLLMError must subclass anthropic.AnthropicError (spec Tasks)."""
    assert issubclass(MetaPlannerLLMError, anthropic.AnthropicError)


def test_meta_planner_validation_error_is_a_value_error() -> None:
    assert issubclass(MetaPlannerValidationError, ValueError)


# ---- node_id sanitization / dedup -----------------------------------------


def test_decompose_task_sanitizes_node_id_slugs(project_root: Path, make_fake_client) -> None:
    fake_output = DagBlueprint(
        intent="x",
        agents=[AgentSpec(node_id="Main Orchestrator!!", parent_id=None, responsibility="x", depends_on=[])],
    )
    client = make_fake_client(output=fake_output)

    result = decompose_task("x", project_root, client)

    assert result.agents[0].node_id == "main-orchestrator"


def test_decompose_task_dedupes_colliding_slugs_and_remaps_references(project_root: Path, make_fake_client) -> None:
    """Two agents whose node_id hints sanitize to the same slug must resolve to
    distinct node_ids -- and any parent_id/depends_on referencing the original
    (untrusted) node_id string must be remapped to the deduped slug."""
    fake_output = DagBlueprint(
        intent="x",
        agents=[
            AgentSpec(node_id="main_orchestrator", parent_id=None, responsibility="root", depends_on=[]),
            AgentSpec(node_id="Worker!!!", parent_id="main_orchestrator", responsibility="first", depends_on=[]),
            AgentSpec(
                node_id="worker",
                parent_id="main_orchestrator",
                responsibility="second",
                depends_on=["Worker!!!"],
            ),
        ],
    )
    client = make_fake_client(output=fake_output)

    result = decompose_task("x", project_root, client)

    node_ids = [a.node_id for a in result.agents]
    assert len(node_ids) == len(set(node_ids)), f"expected distinct node_ids, got {node_ids}"
    assert node_ids == ["main-orchestrator", "worker", "worker-2"]
    # The third agent's depends_on ("Worker!!!") must now point at the first
    # worker's resolved slug ("worker"), not the raw, untrusted string.
    third = result.agents[2]
    assert third.depends_on == ["worker"]
    assert third.parent_id == "main-orchestrator"


def test_decompose_task_drops_dangling_depends_on_reference(project_root: Path, make_fake_client) -> None:
    """A depends_on entry that doesn't match any node_id in the response is
    dropped rather than passed through as a dangling reference (Boundaries)."""
    fake_output = DagBlueprint(
        intent="x",
        agents=[
            AgentSpec(node_id="main_orchestrator", parent_id=None, responsibility="root", depends_on=[]),
            AgentSpec(
                node_id="worker",
                parent_id="main_orchestrator",
                responsibility="x",
                depends_on=["nonexistent_agent"],
            ),
        ],
    )
    client = make_fake_client(output=fake_output)

    result = decompose_task("x", project_root, client)

    worker = next(a for a in result.agents if a.node_id == "worker")
    assert worker.depends_on == []


def test_decompose_task_raises_on_dangling_parent_id_reference(project_root: Path, make_fake_client) -> None:
    """A subagent's parent_id that doesn't match any node_id in the response
    must not be silently remapped to None (that would manufacture a second
    apparent root) -- it's an invalid/unparseable response (Boundaries)."""
    fake_output = DagBlueprint(
        intent="x",
        agents=[
            AgentSpec(node_id="main_orchestrator", parent_id=None, responsibility="root", depends_on=[]),
            AgentSpec(
                node_id="worker",
                parent_id="nonexistent_agent",
                responsibility="x",
                depends_on=[],
            ),
        ],
    )
    client = make_fake_client(output=fake_output)

    with pytest.raises(MetaPlannerLLMError):
        decompose_task("x", project_root, client)


def test_decompose_task_raises_when_zero_agents_have_null_parent_id(project_root: Path, make_fake_client) -> None:
    """AC #1: exactly one agent must have parent_id=null. Zero is invalid."""
    fake_output = DagBlueprint(
        intent="x",
        agents=[
            AgentSpec(node_id="worker_a", parent_id="worker_b", responsibility="a", depends_on=[]),
            AgentSpec(node_id="worker_b", parent_id="worker_a", responsibility="b", depends_on=[]),
        ],
    )
    client = make_fake_client(output=fake_output)

    with pytest.raises(MetaPlannerLLMError):
        decompose_task("x", project_root, client)


def test_decompose_task_raises_when_multiple_agents_have_null_parent_id(project_root: Path, make_fake_client) -> None:
    """AC #1: exactly one agent must have parent_id=null. More than one is invalid."""
    fake_output = DagBlueprint(
        intent="x",
        agents=[
            AgentSpec(node_id="main_orchestrator", parent_id=None, responsibility="root one", depends_on=[]),
            AgentSpec(node_id="second_root", parent_id=None, responsibility="root two", depends_on=[]),
        ],
    )
    client = make_fake_client(output=fake_output)

    with pytest.raises(MetaPlannerLLMError):
        decompose_task("x", project_root, client)


# ---- context-graph nodes (Story 2.2, I/O matrix) ---------------------------


def test_decompose_task_existing_codebase_preserves_codebase_file_node(
    project_root: Path, make_fake_client, make_node
) -> None:
    """I/O matrix row 1: existing codebase -- every agent's nodes is
    non-empty, and at least one node has source=codebase_file with a real
    path as source_ref."""
    (project_root / "app.py").write_text("print('hello')", encoding="utf-8")
    fake_output = DagBlueprint(
        intent="add OAuth2 login",
        agents=[
            AgentSpec(
                node_id="main_orchestrator",
                parent_id=None,
                responsibility="Coordinate auth rollout",
                depends_on=[],
                nodes=[make_node("app_entrypoint", source="codebase_file", source_ref="app.py")],
            ),
        ],
    )
    client = make_fake_client(output=fake_output)

    result = decompose_task("add OAuth2 login", project_root, client)

    for agent in result.agents:
        assert len(agent.nodes) > 0
    codebase_nodes = [n for agent in result.agents for n in agent.nodes if n.source == "codebase_file"]
    assert len(codebase_nodes) == 1
    assert codebase_nodes[0].source_ref == "app.py"


def test_decompose_task_new_empty_codebase_has_no_codebase_file_node(
    project_root: Path, make_fake_client, make_node
) -> None:
    """I/O matrix row 2: new/empty codebase -- no node cites
    source=codebase_file; other sources are still allowed."""
    fake_output = DagBlueprint(
        intent="scaffold a new service",
        agents=[
            AgentSpec(
                node_id="main_orchestrator",
                parent_id=None,
                responsibility="Coordinate scaffolding",
                depends_on=[],
                nodes=[make_node("project_conventions", source="claude_context")],
            ),
        ],
    )
    client = make_fake_client(output=fake_output)

    result = decompose_task("scaffold a new service", project_root, client)

    codebase_nodes = [n for agent in result.agents for n in agent.nodes if n.source == "codebase_file"]
    assert codebase_nodes == []
    assert len(result.agents[0].nodes) == 1


def test_decompose_task_drops_dangling_neighbor_reference(project_root: Path, make_fake_client, make_node) -> None:
    """I/O matrix row 3: a neighbor entry that doesn't match any node_id on
    that same agent is dropped silently, never passed through raw."""
    fake_output = DagBlueprint(
        intent="x",
        agents=[
            AgentSpec(
                node_id="main_orchestrator",
                parent_id=None,
                responsibility="root",
                depends_on=[],
                nodes=[make_node("auth_docs", neighbors=["nonexistent_node"])],
            ),
        ],
    )
    client = make_fake_client(output=fake_output)

    result = decompose_task("x", project_root, client)

    assert result.agents[0].nodes[0].neighbors == []


def test_decompose_task_dedupes_colliding_node_ids_within_one_agent(
    project_root: Path, make_fake_client, make_node
) -> None:
    """I/O matrix row 4: two nodes on the same agent that sanitize to the
    same slug are deduped (-2/-3 suffixing) and neighbor references remapped
    to the deduped slug."""
    fake_output = DagBlueprint(
        intent="x",
        agents=[
            AgentSpec(
                node_id="main_orchestrator",
                parent_id=None,
                responsibility="root",
                depends_on=[],
                nodes=[
                    make_node("Auth Docs!!!"),
                    make_node("auth_docs", neighbors=["Auth Docs!!!"]),
                ],
            ),
        ],
    )
    client = make_fake_client(output=fake_output)

    result = decompose_task("x", project_root, client)

    node_ids = [n.node_id for n in result.agents[0].nodes]
    assert node_ids == ["auth-docs", "auth-docs-2"]
    second = result.agents[0].nodes[1]
    assert second.neighbors == ["auth-docs"]


def test_decompose_task_node_namespaces_are_per_agent_not_global(project_root: Path, make_fake_client, make_node) -> None:
    """Design Notes: node_id only needs to be unique within its own agent's
    nodes list -- two different agents can each have a node with the same
    name without triggering cross-agent dedup suffixing."""
    fake_output = DagBlueprint(
        intent="x",
        agents=[
            AgentSpec(
                node_id="main_orchestrator",
                parent_id=None,
                responsibility="root",
                depends_on=[],
                nodes=[make_node("auth_docs")],
            ),
            AgentSpec(
                node_id="worker",
                parent_id="main_orchestrator",
                responsibility="x",
                depends_on=[],
                nodes=[make_node("auth_docs")],
            ),
        ],
    )
    client = make_fake_client(output=fake_output)

    result = decompose_task("x", project_root, client)

    orchestrator = next(a for a in result.agents if a.node_id == "main-orchestrator")
    worker = next(a for a in result.agents if a.node_id == "worker")
    assert orchestrator.nodes[0].node_id == "auth-docs"
    assert worker.nodes[0].node_id == "auth-docs"


def test_node_model_execution_fields_default_to_none() -> None:
    """AD-2/AD-8: execution/telemetry fields are pre-provisioned but always
    unset from the Meta-Planner -- the Engine writes them once a run
    executes."""
    node = Node(node_id="x", topic="X", source="claude_context")
    assert node.status is None
    assert node.telemetry is None
    assert node.live_stream is None
    assert node.checkpoint_ref is None
    assert node.source_ref is None
    assert node.neighbors == []


def test_node_codebase_file_source_requires_non_empty_source_ref() -> None:
    """`source_ref` must be a non-empty (post-strip) string when
    `source='codebase_file'` -- a codebase_file node with no real path to
    cite is an invalid response, not a silently-accepted null."""
    with pytest.raises(ValidationError):
        Node(node_id="x", topic="X", source="codebase_file")

    with pytest.raises(ValidationError):
        Node(node_id="x", topic="X", source="codebase_file", source_ref="   ")


# ---- node_id/neighbors edge cases (post-review hardening) ------------------


def test_decompose_task_duplicate_raw_node_id_resolves_neighbor_to_first_node(
    project_root: Path, make_fake_client, make_node
) -> None:
    """Two nodes on the same agent that share the exact same raw (untrusted)
    node_id must not let the second overwrite the first's mapping -- a
    neighbor reference to that shared raw id resolves to the *first* node's
    slug, not the second's."""
    fake_output = DagBlueprint(
        intent="x",
        agents=[
            AgentSpec(
                node_id="main_orchestrator",
                parent_id=None,
                responsibility="root",
                depends_on=[],
                nodes=[
                    make_node("auth_docs", topic="First"),
                    make_node("auth_docs", topic="Second"),
                    make_node("referrer", neighbors=["auth_docs"]),
                ],
            ),
        ],
    )
    client = make_fake_client(output=fake_output)

    result = decompose_task("x", project_root, client)

    nodes = result.agents[0].nodes
    node_ids = [n.node_id for n in nodes]
    assert node_ids == ["auth-docs", "auth-docs-2", "referrer"]
    referrer = next(n for n in nodes if n.node_id == "referrer")
    assert referrer.neighbors == ["auth-docs"]


def test_decompose_task_drops_self_reference_from_neighbors(
    project_root: Path, make_fake_client, make_node
) -> None:
    """A node should never list itself as a neighbor -- a self-reference is
    dropped, not passed through."""
    fake_output = DagBlueprint(
        intent="x",
        agents=[
            AgentSpec(
                node_id="main_orchestrator",
                parent_id=None,
                responsibility="root",
                depends_on=[],
                nodes=[make_node("auth_docs", neighbors=["auth_docs"])],
            ),
        ],
    )
    client = make_fake_client(output=fake_output)

    result = decompose_task("x", project_root, client)

    assert result.agents[0].nodes[0].neighbors == []


def test_decompose_task_dedupes_duplicate_neighbor_entries(
    project_root: Path, make_fake_client, make_node
) -> None:
    """A `neighbors` list with a duplicate entry surfaces only one instance,
    preserving order."""
    fake_output = DagBlueprint(
        intent="x",
        agents=[
            AgentSpec(
                node_id="main_orchestrator",
                parent_id=None,
                responsibility="root",
                depends_on=[],
                nodes=[
                    make_node("auth_docs"),
                    make_node("referrer", neighbors=["auth_docs", "auth_docs"]),
                ],
            ),
        ],
    )
    client = make_fake_client(output=fake_output)

    result = decompose_task("x", project_root, client)

    referrer = next(n for n in result.agents[0].nodes if n.node_id == "referrer")
    assert referrer.neighbors == ["auth-docs"]


def test_decompose_task_forces_engine_owned_node_fields_to_none(
    project_root: Path, make_fake_client, make_node
) -> None:
    """AD-2/AD-8: `status`/`telemetry`/`live_stream`/`checkpoint_ref` are
    Engine-owned and must always come back null from the Meta-Planner, even
    if a hallucinated LLM response sets them to a non-null value -- never
    trust the LLM for Engine-owned fields (mirrors Settings Router's
    treatment of `file_path`)."""
    fake_output = DagBlueprint(
        intent="x",
        agents=[
            AgentSpec(
                node_id="main_orchestrator",
                parent_id=None,
                responsibility="root",
                depends_on=[],
                nodes=[
                    make_node(
                        "auth_docs",
                        status="running",
                        telemetry={"events": 3},
                        live_stream={"url": "wss://example"},
                        checkpoint_ref="ckpt-123",
                    )
                ],
            ),
        ],
    )
    client = make_fake_client(output=fake_output)

    result = decompose_task("x", project_root, client)

    node = result.agents[0].nodes[0]
    assert node.status is None
    assert node.telemetry is None
    assert node.live_stream is None
    assert node.checkpoint_ref is None


def test_decompose_task_existing_codebase_multi_agent_every_agent_has_nodes(
    project_root: Path, make_fake_client, make_node
) -> None:
    """I/O matrix row 1, multi-agent: an existing codebase with more than one
    agent in the response -- every agent's nodes list is non-empty, not just
    a single orchestrator's."""
    (project_root / "app.py").write_text("print('hello')", encoding="utf-8")
    fake_output = DagBlueprint(
        intent="add OAuth2 login",
        agents=[
            AgentSpec(
                node_id="main_orchestrator",
                parent_id=None,
                responsibility="Coordinate auth rollout",
                depends_on=[],
                nodes=[make_node("app_entrypoint", source="codebase_file", source_ref="app.py")],
            ),
            AgentSpec(
                node_id="auth_scaffold_worker",
                parent_id="main_orchestrator",
                responsibility="Add OAuth2/JWT middleware",
                depends_on=[],
                nodes=[make_node("auth_conventions", source="claude_context")],
            ),
        ],
    )
    client = make_fake_client(output=fake_output)

    result = decompose_task("add OAuth2 login", project_root, client)

    assert len(result.agents) == 2
    for agent in result.agents:
        assert len(agent.nodes) > 0
