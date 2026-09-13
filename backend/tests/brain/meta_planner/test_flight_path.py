"""Unit tests for `brain.meta_planner.flight_path` (Story 2.3, I/O matrix)."""

from pathlib import Path

from brain.meta_planner.flight_path import _MAX_READ_BYTES, _USD_PER_TOKEN, select_flight_path
from brain.meta_planner.models import AgentSpec


def _agent(nodes: list) -> AgentSpec:
    return AgentSpec(
        node_id="worker",
        parent_id="main-orchestrator",
        responsibility="x",
        depends_on=[],
        nodes=nodes,
    )


# ---- I/O matrix row 1: mixed required/optional nodes -----------------------


def test_flight_path_includes_only_required_nodes_ordered_by_neighbors(make_node) -> None:
    nodes = [
        make_node("a", required=True, neighbors=["b"]),
        make_node("b", required=True),
        make_node("c", required=False),
    ]
    agent = _agent(nodes)

    result = select_flight_path(agent, Path("/nonexistent"))

    assert result.flight_path == ["a", "b"]
    assert result.estimated_tokens == 1000  # two flat-cost nodes (claude_context)
    assert result.estimated_duration_seconds == 1000 / 250.0
    assert result.estimated_cost_usd == 1000 * _USD_PER_TOKEN


def test_flight_path_orders_disconnected_required_nodes_by_original_position(make_node) -> None:
    """Two required nodes with no neighbor edge between them still both
    appear, in their original nodes-list order."""
    nodes = [
        make_node("first", required=True),
        make_node("second", required=True),
    ]
    agent = _agent(nodes)

    result = select_flight_path(agent, Path("/nonexistent"))

    assert result.flight_path == ["first", "second"]


def test_flight_path_does_not_follow_neighbor_into_optional_node(make_node) -> None:
    """A required node's neighbor that is itself not required is never
    pulled into the flight path."""
    nodes = [
        make_node("a", required=True, neighbors=["optional"]),
        make_node("optional", required=False),
    ]
    agent = _agent(nodes)

    result = select_flight_path(agent, Path("/nonexistent"))

    assert result.flight_path == ["a"]


# ---- I/O matrix row 2: required codebase_file node, real file --------------


def test_flight_path_uses_real_file_size_for_resolvable_codebase_file(tmp_path: Path, make_node) -> None:
    real_file = tmp_path / "app.py"
    real_file.write_text("x" * 4000, encoding="utf-8")
    nodes = [make_node("entrypoint", required=True, source="codebase_file", source_ref="app.py")]
    agent = _agent(nodes)

    result = select_flight_path(agent, tmp_path)

    assert result.estimated_tokens == 1000  # 4000 chars / 4
    assert result.flight_path == ["entrypoint"]


def test_flight_path_rounds_up_token_cost_for_small_codebase_file(tmp_path: Path, make_node) -> None:
    """Ceiling division, not floor: a 3-char file must cost 1 token, never 0
    -- underestimating is the riskier direction for a cost estimate."""
    real_file = tmp_path / "tiny.py"
    real_file.write_text("xyz", encoding="utf-8")
    nodes = [make_node("tiny", required=True, source="codebase_file", source_ref="tiny.py")]
    agent = _agent(nodes)

    result = select_flight_path(agent, tmp_path)

    assert result.estimated_tokens == 1  # ceil(3 / 4), not floor(3 / 4) == 0


def test_flight_path_skips_full_read_for_oversized_codebase_file(tmp_path: Path, make_node, monkeypatch) -> None:
    """A required codebase_file node whose real size exceeds the read cap
    must never have its full content loaded into memory -- its cost is
    estimated straight from its on-disk byte size (ceiling division)
    instead."""
    size = _MAX_READ_BYTES + 1
    real_file = tmp_path / "huge.py"
    with real_file.open("wb") as f:
        f.seek(size - 1)
        f.write(b"\0")

    def _fail_if_read(self, *args, **kwargs):
        raise AssertionError("read_text should not be called for an oversized file")

    monkeypatch.setattr(Path, "read_text", _fail_if_read)

    nodes = [make_node("huge", required=True, source="codebase_file", source_ref="huge.py")]
    agent = _agent(nodes)

    result = select_flight_path(agent, tmp_path)

    assert result.estimated_tokens == -(-size // 4)
    assert result.flight_path == ["huge"]


# ---- I/O matrix row 3: required codebase_file node, missing/hallucinated ---


def test_flight_path_falls_back_to_flat_cost_for_missing_codebase_file(tmp_path: Path, make_node) -> None:
    nodes = [make_node("ghost", required=True, source="codebase_file", source_ref="does_not_exist.py")]
    agent = _agent(nodes)

    result = select_flight_path(agent, tmp_path)

    assert result.estimated_tokens == 500  # flat constant, no error raised
    assert result.flight_path == ["ghost"]


def test_flight_path_falls_back_to_flat_cost_for_malformed_source_ref(tmp_path: Path, make_node) -> None:
    """A hallucinated/malformed source_ref that makes `Path.resolve()` raise
    something other than `OSError` (e.g. an embedded null byte, which
    raises `ValueError`) must still fall back to the flat cost, never
    propagate an exception out of `decompose_task`."""
    nodes = [
        make_node(
            "malformed",
            required=True,
            source="codebase_file",
            source_ref="foo\x00bar",
        )
    ]
    agent = _agent(nodes)

    result = select_flight_path(agent, tmp_path)

    assert result.estimated_tokens == 500
    assert result.flight_path == ["malformed"]


def test_flight_path_falls_back_to_flat_cost_for_path_traversal_source_ref(tmp_path: Path, make_node) -> None:
    """A source_ref that resolves outside project_root (e.g. path traversal)
    is treated exactly like a missing file -- never followed."""
    outside = tmp_path.parent / "outside_secret.txt"
    outside.write_text("secret" * 100, encoding="utf-8")
    try:
        nodes = [
            make_node(
                "escape",
                required=True,
                source="codebase_file",
                source_ref="../outside_secret.txt",
            )
        ]
        agent = _agent(nodes)

        result = select_flight_path(agent, tmp_path)

        assert result.estimated_tokens == 500
    finally:
        outside.unlink(missing_ok=True)


# ---- I/O matrix row 4: no required nodes ------------------------------------


def test_flight_path_no_required_nodes_yields_empty_path_and_zero_estimates(make_node) -> None:
    nodes = [make_node("optional_a", required=False), make_node("optional_b", required=False)]
    agent = _agent(nodes)

    result = select_flight_path(agent, Path("/nonexistent"))

    assert result.flight_path == []
    assert result.estimated_tokens == 0
    assert result.estimated_duration_seconds == 0.0
    assert result.estimated_cost_usd == 0.0


def test_flight_path_empty_nodes_list_yields_empty_path_and_zero_estimates() -> None:
    agent = _agent([])

    result = select_flight_path(agent, Path("/nonexistent"))

    assert result.flight_path == []
    assert result.estimated_tokens == 0
    assert result.estimated_duration_seconds == 0.0
    assert result.estimated_cost_usd == 0.0


# ---- mcp round-trip duration -------------------------------------------------


def test_flight_path_adds_round_trip_constant_per_required_mcp_node(make_node) -> None:
    nodes = [
        make_node("tool_a", required=True, source="mcp"),
        make_node("tool_b", required=True, source="mcp"),
    ]
    agent = _agent(nodes)

    result = select_flight_path(agent, Path("/nonexistent"))

    expected_tokens = 500 * 2
    expected_duration = (expected_tokens / 250.0) + (2 * 1.5)
    assert result.estimated_tokens == expected_tokens
    assert result.estimated_duration_seconds == expected_duration
    assert result.estimated_cost_usd == expected_tokens * _USD_PER_TOKEN


# ---- dollar-cost estimate ----------------------------------------------------


def test_flight_path_cost_usd_scales_linearly_with_token_count(tmp_path: Path, make_node) -> None:
    real_file = tmp_path / "app.py"
    real_file.write_text("x" * 40_000, encoding="utf-8")
    nodes = [make_node("entrypoint", required=True, source="codebase_file", source_ref="app.py")]
    agent = _agent(nodes)

    result = select_flight_path(agent, tmp_path)

    assert result.estimated_tokens == 10_000  # 40,000 chars / 4
    assert result.estimated_cost_usd == 10_000 * _USD_PER_TOKEN


# ---- never drops a required node regardless of cost -------------------------


def test_flight_path_covers_every_required_node_regardless_of_cost(make_node) -> None:
    """Design Notes: no budget enforcement -- every required node is always
    included, however large the resulting cost."""
    nodes = [make_node(f"n{i}", required=True) for i in range(25)]
    agent = _agent(nodes)

    result = select_flight_path(agent, Path("/nonexistent"))

    assert set(result.flight_path) == {f"n{i}" for i in range(25)}
    assert len(result.flight_path) == 25
