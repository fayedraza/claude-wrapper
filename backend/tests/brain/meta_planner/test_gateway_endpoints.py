"""API-level tests for `POST /api/meta-planner/decompose` (Story 2.1, I/O matrix)."""

from pathlib import Path

import httpx2
import pytest
from anthropic import APIConnectionError
from fastapi.testclient import TestClient

from brain.meta_planner.models import AgentSpec, DagBlueprint, Node
from gateway.main import app, get_anthropic_client, get_claude_dir


@pytest.fixture
def api_client(claude_dir: Path) -> TestClient:
    app.dependency_overrides[get_claude_dir] = lambda: claude_dir
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_claude_dir, None)
        app.dependency_overrides.pop(get_anthropic_client, None)


@pytest.fixture
def mock_anthropic(make_fake_client):
    """Overrides the gateway's Anthropic dependency for the duration of one test."""

    def _mock(output: DagBlueprint | None = None, error: Exception | None = None) -> None:
        app.dependency_overrides[get_anthropic_client] = lambda: make_fake_client(output=output, error=error)

    return _mock


def test_decompose_existing_codebase_returns_blueprint(api_client: TestClient, claude_dir: Path, mock_anthropic) -> None:
    (claude_dir.parent / "app.py").write_text("print('hi')", encoding="utf-8")
    mock_anthropic(
        output=DagBlueprint(
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
    )

    response = api_client.post("/api/meta-planner/decompose", json={"intent": "add OAuth2 login"})

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "add OAuth2 login"
    roots = [a for a in body["agents"] if a["parent_id"] is None]
    assert len(roots) == 1
    subagents = [a for a in body["agents"] if a["parent_id"] is not None]
    assert len(subagents) == 1
    assert subagents[0]["parent_id"] == roots[0]["node_id"]
    # Read-only: nothing written under .claude/.
    assert list(claude_dir.iterdir()) == []


def test_decompose_new_empty_codebase_returns_same_shape(api_client: TestClient, mock_anthropic) -> None:
    mock_anthropic(
        output=DagBlueprint(
            intent="scaffold a new service",
            agents=[
                AgentSpec(node_id="main_orchestrator", parent_id=None, responsibility="Coordinate scaffolding", depends_on=[]),
            ],
        )
    )

    response = api_client.post("/api/meta-planner/decompose", json={"intent": "scaffold a new service"})

    assert response.status_code == 200
    body = response.json()
    assert len(body["agents"]) == 1
    assert body["agents"][0]["parent_id"] is None


@pytest.mark.parametrize("blank", ["", "   ", "\n"])
def test_decompose_blank_intent_returns_400_without_llm_call(blank: str, api_client: TestClient, mock_anthropic) -> None:
    mock_anthropic(output=None)

    response = api_client.post("/api/meta-planner/decompose", json={"intent": blank})

    assert response.status_code == 400
    body = response.json()
    assert set(body.keys()) == {"error_code", "message", "node_id"}
    assert body["error_code"] == "meta_planner.invalid_intent"
    assert body["node_id"] is None


def test_decompose_llm_failure_returns_502(api_client: TestClient, mock_anthropic) -> None:
    mock_anthropic(error=APIConnectionError(request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages")))

    response = api_client.post("/api/meta-planner/decompose", json={"intent": "add OAuth2 login"})

    assert response.status_code == 502
    body = response.json()
    assert set(body.keys()) == {"error_code", "message", "node_id"}
    assert body["error_code"] == "meta_planner.llm_error"
    assert body["node_id"] is None


def test_decompose_missing_credentials_returns_502(api_client: TestClient, mock_anthropic) -> None:
    mock_anthropic(error=TypeError("Could not resolve authentication method."))

    response = api_client.post("/api/meta-planner/decompose", json={"intent": "add OAuth2 login"})

    assert response.status_code == 502
    body = response.json()
    assert body["error_code"] == "meta_planner.llm_error"


def test_decompose_returns_502_when_parsed_output_is_none(api_client: TestClient, mock_anthropic) -> None:
    mock_anthropic(output=None)

    response = api_client.post("/api/meta-planner/decompose", json={"intent": "add OAuth2 login"})

    assert response.status_code == 502
    body = response.json()
    assert body["error_code"] == "meta_planner.llm_error"


def test_decompose_returns_502_on_dangling_parent_id_reference(api_client: TestClient, mock_anthropic) -> None:
    """A subagent's parent_id referencing a node_id absent from the response
    must not be silently remapped to None -- it's a 502, not a malformed
    200 with two apparent roots."""
    mock_anthropic(
        output=DagBlueprint(
            intent="x",
            agents=[
                AgentSpec(node_id="main_orchestrator", parent_id=None, responsibility="root", depends_on=[]),
                AgentSpec(node_id="worker", parent_id="nonexistent_agent", responsibility="x", depends_on=[]),
            ],
        )
    )

    response = api_client.post("/api/meta-planner/decompose", json={"intent": "x"})

    assert response.status_code == 502
    assert response.json()["error_code"] == "meta_planner.llm_error"


def test_decompose_returns_502_when_zero_agents_have_null_parent_id(api_client: TestClient, mock_anthropic) -> None:
    mock_anthropic(
        output=DagBlueprint(
            intent="x",
            agents=[
                AgentSpec(node_id="worker_a", parent_id="worker_b", responsibility="a", depends_on=[]),
                AgentSpec(node_id="worker_b", parent_id="worker_a", responsibility="b", depends_on=[]),
            ],
        )
    )

    response = api_client.post("/api/meta-planner/decompose", json={"intent": "x"})

    assert response.status_code == 502
    assert response.json()["error_code"] == "meta_planner.llm_error"


def test_decompose_returns_502_when_multiple_agents_have_null_parent_id(api_client: TestClient, mock_anthropic) -> None:
    mock_anthropic(
        output=DagBlueprint(
            intent="x",
            agents=[
                AgentSpec(node_id="main_orchestrator", parent_id=None, responsibility="root one", depends_on=[]),
                AgentSpec(node_id="second_root", parent_id=None, responsibility="root two", depends_on=[]),
            ],
        )
    )

    response = api_client.post("/api/meta-planner/decompose", json={"intent": "x"})

    assert response.status_code == 502
    assert response.json()["error_code"] == "meta_planner.llm_error"


def test_decompose_response_includes_context_graph_nodes(api_client: TestClient, claude_dir: Path, mock_anthropic) -> None:
    """I/O matrix row 1 (existing codebase), API level: the response includes
    each agent's nodes, with a codebase_file node's source_ref intact."""
    (claude_dir.parent / "app.py").write_text("print('hi')", encoding="utf-8")
    mock_anthropic(
        output=DagBlueprint(
            intent="add OAuth2 login",
            agents=[
                AgentSpec(
                    node_id="main_orchestrator",
                    parent_id=None,
                    responsibility="Coordinate auth rollout",
                    depends_on=[],
                    nodes=[Node(node_id="app_entrypoint", topic="App entrypoint", source="codebase_file", source_ref="app.py")],
                ),
            ],
        )
    )

    response = api_client.post("/api/meta-planner/decompose", json={"intent": "add OAuth2 login"})

    assert response.status_code == 200
    nodes = response.json()["agents"][0]["nodes"]
    assert len(nodes) == 1
    assert nodes[0]["source"] == "codebase_file"
    assert nodes[0]["source_ref"] == "app.py"
    # Execution fields are pre-provisioned but unset from the Meta-Planner.
    assert nodes[0]["status"] is None


def test_decompose_drops_dangling_neighbor_reference_end_to_end(api_client: TestClient, mock_anthropic) -> None:
    """I/O matrix row 3, API level: a dangling neighbor reference never
    reaches the response."""
    mock_anthropic(
        output=DagBlueprint(
            intent="x",
            agents=[
                AgentSpec(
                    node_id="main_orchestrator",
                    parent_id=None,
                    responsibility="root",
                    depends_on=[],
                    nodes=[
                        Node(
                            node_id="auth_docs",
                            topic="Auth docs",
                            source="claude_context",
                            neighbors=["nonexistent_node"],
                        )
                    ],
                ),
            ],
        )
    )

    response = api_client.post("/api/meta-planner/decompose", json={"intent": "x"})

    assert response.status_code == 200
    assert response.json()["agents"][0]["nodes"][0]["neighbors"] == []


def test_decompose_dedupes_duplicate_node_ids_within_one_agent_end_to_end(
    api_client: TestClient, mock_anthropic
) -> None:
    """I/O matrix row 4, API level: duplicate node_id hints on the same
    agent are deduped and neighbor references remapped."""
    mock_anthropic(
        output=DagBlueprint(
            intent="x",
            agents=[
                AgentSpec(
                    node_id="main_orchestrator",
                    parent_id=None,
                    responsibility="root",
                    depends_on=[],
                    nodes=[
                        Node(node_id="Auth Docs!!!", topic="Auth docs", source="claude_context"),
                        Node(
                            node_id="auth_docs",
                            topic="Auth docs 2",
                            source="claude_context",
                            neighbors=["Auth Docs!!!"],
                        ),
                    ],
                ),
            ],
        )
    )

    response = api_client.post("/api/meta-planner/decompose", json={"intent": "x"})

    assert response.status_code == 200
    nodes = response.json()["agents"][0]["nodes"]
    node_ids = [n["node_id"] for n in nodes]
    assert node_ids == ["auth-docs", "auth-docs-2"]
    assert nodes[1]["neighbors"] == ["auth-docs"]


def test_decompose_new_empty_codebase_has_no_codebase_file_node_end_to_end(
    api_client: TestClient, mock_anthropic
) -> None:
    """I/O matrix row 2, API level: new/empty codebase -- no node cites
    source=codebase_file."""
    mock_anthropic(
        output=DagBlueprint(
            intent="scaffold a new service",
            agents=[
                AgentSpec(
                    node_id="main_orchestrator",
                    parent_id=None,
                    responsibility="Coordinate scaffolding",
                    depends_on=[],
                    nodes=[Node(node_id="conventions", topic="Conventions", source="claude_context")],
                ),
            ],
        )
    )

    response = api_client.post("/api/meta-planner/decompose", json={"intent": "scaffold a new service"})

    assert response.status_code == 200
    nodes = response.json()["agents"][0]["nodes"]
    assert all(n["source"] != "codebase_file" for n in nodes)


def test_decompose_dedupes_duplicate_slugs_end_to_end(api_client: TestClient, mock_anthropic) -> None:
    mock_anthropic(
        output=DagBlueprint(
            intent="x",
            agents=[
                AgentSpec(node_id="main_orchestrator", parent_id=None, responsibility="root", depends_on=[]),
                AgentSpec(node_id="Worker!!!", parent_id="main_orchestrator", responsibility="first", depends_on=[]),
                AgentSpec(node_id="worker", parent_id="main_orchestrator", responsibility="second", depends_on=[]),
            ],
        )
    )

    response = api_client.post("/api/meta-planner/decompose", json={"intent": "x"})

    assert response.status_code == 200
    node_ids = [a["node_id"] for a in response.json()["agents"]]
    assert len(node_ids) == len(set(node_ids))
    assert node_ids == ["main-orchestrator", "worker", "worker-2"]
