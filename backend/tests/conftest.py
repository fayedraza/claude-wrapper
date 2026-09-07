"""Shared pytest fixtures for the backend test suite."""

import pytest
from fastapi.testclient import TestClient

from gateway.main import app


@pytest.fixture
def client() -> TestClient:
    """A TestClient wired to the FastAPI gateway app, for API-level tests."""
    return TestClient(app)
