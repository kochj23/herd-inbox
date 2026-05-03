"""Shared pytest fixtures."""

import pytest
from fastapi.testclient import TestClient

from herd_inbox.main import app


@pytest.fixture
def client() -> TestClient:
    """Test client for FastAPI app."""
    return TestClient(app)
