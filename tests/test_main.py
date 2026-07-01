"""Tests for main FastAPI app."""

from fastapi.testclient import TestClient


def test_health_check(client: TestClient) -> None:
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_root(client: TestClient) -> None:
    """Root endpoint now serves the server-rendered inbox view."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Herd-Inbox" in response.text
