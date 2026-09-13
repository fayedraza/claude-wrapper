"""Shared fixtures for Meta-Planner tests.

`FakeAnthropicClient` stands in for `anthropic.Anthropic()` everywhere in
this test package -- no test here calls the live Anthropic API (mirrors
`tests/brain/settings_router/conftest.py`, swapping in `DagBlueprint`).
"""

from pathlib import Path

import pytest

from brain.meta_planner.models import DagBlueprint


class _FakeParsedResponse:
    def __init__(self, parsed_output: DagBlueprint | None) -> None:
        self.parsed_output = parsed_output


class _FakeMessages:
    """Stands in for `client.messages`; `.parse()` mimics the real SDK shape."""

    def __init__(self, output: DagBlueprint | None = None, error: Exception | None = None) -> None:
        self._output = output
        self._error = error
        self.calls: list[dict] = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        return _FakeParsedResponse(self._output)


class FakeAnthropicClient:
    """Minimal stand-in for `anthropic.Anthropic()` -- only `.messages.parse()` is used."""

    def __init__(self, output: DagBlueprint | None = None, error: Exception | None = None) -> None:
        self.messages = _FakeMessages(output=output, error=error)


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """An empty project root under pytest's tmp_path -- never the real repo's."""
    return tmp_path


@pytest.fixture
def claude_dir(tmp_path: Path) -> Path:
    """An empty `.claude/` directory under the same project root, for the
    gateway-level tests that override `get_claude_dir`."""
    d = tmp_path / ".claude"
    d.mkdir()
    return d


@pytest.fixture
def make_fake_client():
    """Factory fixture: `make_fake_client(output=..., error=...)` -> `FakeAnthropicClient`."""

    def _make(output: DagBlueprint | None = None, error: Exception | None = None) -> FakeAnthropicClient:
        return FakeAnthropicClient(output=output, error=error)

    return _make
