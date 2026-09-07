"""API-level test for the gateway's /health endpoint."""

from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    # Given the gateway app
    # When GET /health is requested
    response = client.get("/health")

    # Then it returns 200 with the expected status body
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
