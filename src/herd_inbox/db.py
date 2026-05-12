"""Database connection and session management for Herd-Inbox (PostgreSQL)."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from herd_inbox.models import Base

MIGRATIONS_DIR = Path(__file__).parent.parent.parent / "migrations"

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Example: postgresql://herd_inbox:password@localhost:5432/herd_inbox"
        )
    # SQLAlchemy requires postgresql+psycopg2:// but accepts the shorthand too.
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://") and "+psycopg2" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def get_engine(database_url: str | None = None) -> Engine:
    global _engine
    if _engine is None:
        url = database_url or get_database_url()
        _engine = create_engine(
            url,
            pool_pre_ping=True,      # detect stale connections
            pool_size=5,
            max_overflow=10,
        )
    return _engine


def get_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine(database_url)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal


def get_session(database_url: str | None = None) -> Session:
    """Return a new SQLAlchemy Session. Caller is responsible for closing it."""
    factory = get_session_factory(database_url)
    return factory()


def _migration_version(path: Path) -> int:
    return int(path.stem.split("_")[0])


def run_migrations(database_url: str | None = None) -> None:
    """Run pending SQL migrations in order, recording each in schema_versions.

    Safe to call on every startup — already-applied versions are skipped.
    """
    engine = get_engine(database_url)
    with engine.connect() as conn:
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS schema_versions (
                version     INTEGER PRIMARY KEY,
                filename    TEXT    NOT NULL,
                applied_at  TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        ))
        conn.commit()

        applied_rows = conn.execute(text("SELECT version FROM schema_versions")).fetchall()
        applied = {row[0] for row in applied_rows}

        migration_files = sorted(MIGRATIONS_DIR.glob("[0-9]*_*.sql"))
        migration_files = [f for f in migration_files if "rollback" not in f.stem]

        for mf in migration_files:
            version = _migration_version(mf)
            if version in applied:
                continue
            sql = mf.read_text()
            conn.execute(text(sql))
            conn.execute(
                text("INSERT INTO schema_versions (version, filename) VALUES (:v, :f)"),
                {"v": version, "f": mf.name},
            )
            conn.commit()


def init_db(database_url: str | None = None) -> None:
    """Create tables (SQLAlchemy metadata) and run SQL migrations.

    Call once at application startup.
    """
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)
    run_migrations(database_url)


def drop_all(database_url: str | None = None) -> None:
    """Drop all tables. For testing only."""
    engine = get_engine(database_url)
    Base.metadata.drop_all(engine)
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS schema_versions CASCADE"))
        conn.commit()


def reset_engine() -> None:
    """Reset the module-level engine and session factory. For testing only."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
