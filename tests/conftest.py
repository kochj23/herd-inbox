"""Shared pytest fixtures."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from herd_inbox.db import init_db
from herd_inbox.main import app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Test client backed by an initialized temporary database.

    The web routes read ``HERD_INBOX_DB`` per request, so pointing it at a
    fresh, migrated temp database keeps route tests isolated.
    """
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("HERD_INBOX_DB", str(db_path))
    init_db(db_path)
    return TestClient(app)
