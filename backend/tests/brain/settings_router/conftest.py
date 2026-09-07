"""Shared fixtures for Settings Router tests.

`FakeAnthropicClient` stands in for `anthropic.Anthropic()` everywhere in
this test package -- no test in `tests/brain/settings_router/` calls the
live Anthropic API (spec Boundaries: "Anthropic call must be mockable").
"""

from pathlib import Path

import pytest

from brain.settings_router.models import SettingsRouterOutput


class _FakeParsedResponse:
    def __init__(self, parsed_output: SettingsRouterOutput) -> None:
        self.parsed_output = parsed_output


class _FakeMessages:
    """Stands in for `client.messages`; `.parse()` mimics the real SDK shape."""

    def __init__(self, output: SettingsRouterOutput | None = None, error: Exception | None = None) -> None:
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

    def __init__(self, output: SettingsRouterOutput | None = None, error: Exception | None = None) -> None:
        self.messages = _FakeMessages(output=output, error=error)


@pytest.fixture
def claude_dir(tmp_path: Path) -> Path:
    """An empty `.claude/` directory under pytest's tmp_path -- never the real repo's."""
    d = tmp_path / ".claude"
    d.mkdir()
    return d


@pytest.fixture
def make_fake_client():
    """Factory fixture: `make_fake_client(output=..., error=...)` -> `FakeAnthropicClient`.

    A fixture (rather than a plain importable helper) so every test module in
    this package gets it for free via pytest's normal conftest discovery --
    this package has no `__init__.py`, matching the rest of `tests/`, so
    cross-module relative imports don't work here.
    """

    def _make(output: SettingsRouterOutput | None = None, error: Exception | None = None) -> FakeAnthropicClient:
        return FakeAnthropicClient(output=output, error=error)

    return _make
