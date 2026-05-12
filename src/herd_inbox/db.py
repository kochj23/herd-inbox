"""Database connection and initialization for Herd-Inbox."""

import sqlite3
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent.parent.parent / "migrations"
DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "herd_inbox.db"


def get_db_path() -> Path:
    """Return the database path from env or default."""
    import os
    return Path(os.environ.get("HERD_INBOX_DB", str(DEFAULT_DB_PATH)))


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Get a SQLite connection with WAL mode and foreign keys enabled.

    Args:
        db_path: Path to the database file. Uses default if not provided.

    Returns:
        sqlite3.Connection with row factory for dict-like access.
    """
    path = db_path or get_db_path()
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-64000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _ensure_schema_version_table(conn: sqlite3.Connection) -> None:
    """Create the schema_versions table if it does not exist."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_versions (
            version     INTEGER PRIMARY KEY,
            filename    TEXT    NOT NULL,
            applied_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()


def _applied_versions(conn: sqlite3.Connection) -> set[int]:
    """Return the set of already-applied migration version numbers."""
    _ensure_schema_version_table(conn)
    rows = conn.execute("SELECT version FROM schema_versions").fetchall()
    return {row[0] for row in rows}


def _migration_version(path: Path) -> int:
    """Parse the leading integer from a migration filename like '001_initial_schema.sql'."""
    stem = path.stem  # e.g. "001_initial_schema"
    prefix = stem.split("_")[0]
    return int(prefix)


def run_migrations(db_path: Path | None = None) -> None:
    """Run pending migrations in order, skipping already-applied ones.

    Each migration is recorded in `schema_versions` after a successful run,
    so this function is safe to call on every startup.

    Args:
        db_path: Path to the database file. Uses default if not provided.
    """
    conn = get_connection(db_path)
    try:
        migration_files = sorted(MIGRATIONS_DIR.glob("[0-9]*_*.sql"))
        migration_files = [f for f in migration_files if "rollback" not in f.stem]

        applied = _applied_versions(conn)

        for migration_file in migration_files:
            version = _migration_version(migration_file)
            if version in applied:
                continue
            sql = migration_file.read_text()
            # executescript commits any open transaction first, then runs DDL.
            conn.executescript(sql)
            # Record the version (executescript closes implicit transactions,
            # so we need a fresh execute+commit here).
            conn.execute(
                "INSERT INTO schema_versions (version, filename) VALUES (?, ?)",
                (version, migration_file.name),
            )
            conn.commit()
    finally:
        conn.close()


def init_db(db_path: Path | None = None) -> sqlite3.Connection:
    """Initialize the database: run pending migrations and return a connection.

    Args:
        db_path: Path to the database file. Uses default if not provided.

    Returns:
        sqlite3.Connection ready for use.
    """
    path = db_path or get_db_path()
    run_migrations(path)
    return get_connection(path)


def drop_tables(db_path: Path | None = None) -> None:
    """Drop all tables. For testing only.

    Args:
        db_path: Path to the database file. Uses default if not provided.
    """
    conn = get_connection(db_path)
    try:
        rollback_file = MIGRATIONS_DIR / "001_rollback.sql"
        if rollback_file.exists():
            conn.executescript(rollback_file.read_text())
        # Also drop the version tracking table so tests start clean.
        conn.executescript("DROP TABLE IF EXISTS schema_versions;")
    finally:
        conn.close()
