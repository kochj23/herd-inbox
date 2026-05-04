"""Shared pytest fixtures."""

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from herd_inbox.main import app


@pytest.fixture
def client() -> TestClient:
    """Test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def audit_db(tmp_path: Path) -> sqlite3.Connection:
    """Empty test database with the audit_log table only.

    Security tests don't need the full models.py schema — just the audit_log
    surface. Keeps the test independent of unrelated schema migrations.
    """
    db_path = tmp_path / "audit_test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            agent_email TEXT,
            details TEXT,
            timestamp TEXT NOT NULL
        )
        """
    )
    conn.commit()
    yield conn
    conn.close()
