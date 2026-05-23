"""Shared pytest fixtures for PostgreSQL-backed tests.

Test isolation strategy: each test runs inside a transaction that is rolled
back at the end, so no test data ever persists between tests. This is fast
(no DROP/CREATE per test) and correct (no cross-test contamination).

Requires a running PostgreSQL instance. Set TEST_DATABASE_URL in the
environment, or it defaults to a local `herd_inbox_test` database:

    TEST_DATABASE_URL=postgresql://localhost/herd_inbox_test pytest
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session

from herd_inbox.main import app
from herd_inbox.models import Base


TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://localhost/herd_inbox_test",
)


@pytest.fixture(scope="session")
def pg_engine():
    """Session-scoped engine — one connection pool for the whole test run."""
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    with engine.connect() as conn:
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS schema_versions (
                version     INTEGER PRIMARY KEY,
                filename    TEXT NOT NULL,
                applied_at  TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        ))
        conn.commit()
    yield engine
    Base.metadata.drop_all(engine)
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS schema_versions CASCADE"))
        conn.commit()
    engine.dispose()


@pytest.fixture
def db_session(pg_engine) -> Session:
    """Per-test transactional session — rolled back after each test.

    Uses a nested SAVEPOINT so tests that call session.rollback() internally
    don't collapse the outer transaction.
    """
    connection = pg_engine.connect()
    transaction = connection.begin()
    # join_transaction_mode="create_savepoint" is the SQLAlchemy 2.0 replacement
    # for the legacy Session(bind=connection) pattern.
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):  # type: ignore[override]
        nonlocal nested
        if transaction.nested and not transaction._parent.nested:
            nested = connection.begin_nested()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client() -> TestClient:
    """Test client for FastAPI app."""
    return TestClient(app)
