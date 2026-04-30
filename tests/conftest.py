"""Shared pytest fixtures."""

import pytest
from fastapi.testclient import TestClient

from src.herd_inbox.main import app


@pytest.fixture
def client() -> TestClient:
    """Test client for FastAPI app."""
    return TestClient(app)
