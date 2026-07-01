"""Tests for the email-archive importer (STATUS.md #6).

Covers all seven mandated categories: Security, Performance, Retry, Unit,
Integration, Functional, and Frame (smoke).
"""

from __future__ import annotations

import time
from email.message import EmailMessage
from pathlib import Path

import pytest

from herd_inbox.db import drop_tables, get_connection, init_db
from herd_inbox.importer import (
    ImportResult,
    estimate_tokens,
    import_mbox,
    import_messages,
    parse_message,
)


# --------------------------------------------------------------------------- #
# Fixtures / helpers
# --------------------------------------------------------------------------- #
@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    """Temporary database path."""
    return tmp_path / "importer.db"


@pytest.fixture
def db_conn(tmp_db: Path):
    """Initialized connection, cleaned up after the test."""
    conn = init_db(tmp_db)
    yield conn
    conn.close()
    drop_tables(tmp_db)


def make_email(
    *,
    message_id: str,
    subject: str = "Subject",
    sender: str = "author@herd.test",
    plain: str = "Hello herd, this is the body.",
    html: str | None = None,
    in_reply_to: str | None = None,
    space: str | None = None,
) -> EmailMessage:
    """Build an EmailMessage for tests."""
    msg = EmailMessage()
    msg["Message-ID"] = message_id
    msg["Subject"] = subject
    msg["From"] = sender
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
    if space:
        msg["X-Herd-Space"] = space
    msg.set_content(plain)
    if html:
        msg.add_alternative(html, subtype="html")
    return msg


def write_mbox(path: Path, messages: list[EmailMessage]) -> None:
    """Serialize messages into a simple mbox file."""
    lines = []
    for msg in messages:
        lines.append("From herd@herd.test Thu Jan  1 00:00:00 2026")
        lines.append(msg.as_string())
        lines.append("")
    path.write_text("\n".join(lines))


# --------------------------------------------------------------------------- #
# Unit
# --------------------------------------------------------------------------- #
class TestUnit:
    """Pure parsing / helper logic."""

    def test_parse_extracts_core_fields(self) -> None:
        msg = make_email(message_id="<u1@herd.test>", subject="Hi", sender="a@b.c")
        parsed = parse_message(msg)
        assert parsed.message_id == "<u1@herd.test>"
        assert parsed.author == "a@b.c"
        assert parsed.subject == "Hi"
        assert parsed.token_cost > 0
        assert parsed.space == "inbox"
        assert parsed.in_reply_to is None

    def test_space_header_recognized(self) -> None:
        msg = make_email(message_id="<u2@herd.test>", space="dreams")
        assert parse_message(msg).space == "dreams"

    def test_invalid_space_falls_back_to_inbox(self) -> None:
        msg = make_email(message_id="<u3@herd.test>", space="not-a-space")
        assert parse_message(msg).space == "inbox"

    def test_tldr_truncated_to_280(self) -> None:
        parsed = parse_message(
            make_email(message_id="<u4@herd.test>", plain="x" * 500)
        )
        assert len(parsed.tldr) <= 280

    def test_missing_message_id_is_synthesized(self) -> None:
        msg = EmailMessage()
        msg["Subject"] = "no id"
        msg["From"] = "x@y.z"
        msg.set_content("body")
        parsed = parse_message(msg, index=7)
        assert "generated-7" in parsed.message_id

    def test_estimate_tokens_monotonic(self) -> None:
        assert estimate_tokens("") == 0
        assert estimate_tokens("a") >= 1
        assert estimate_tokens("a" * 400) > estimate_tokens("a" * 40)

    def test_in_reply_to_captured(self) -> None:
        msg = make_email(message_id="<u5@herd.test>", in_reply_to="<parent@herd.test>")
        assert parse_message(msg).in_reply_to == "<parent@herd.test>"


# --------------------------------------------------------------------------- #
# Integration
# --------------------------------------------------------------------------- #
class TestIntegration:
    """Importer against a real SQLite database."""

    def test_import_single_post(self, db_conn) -> None:
        result = import_messages(
            [make_email(message_id="<i1@herd.test>", subject="First")], db_conn
        )
        assert result.posts_imported == 1
        row = db_conn.execute(
            "SELECT subject, space FROM posts WHERE message_id = ?", ("<i1@herd.test>",)
        ).fetchone()
        assert row["subject"] == "First"
        assert row["space"] == "inbox"

    def test_reply_becomes_comment(self, db_conn) -> None:
        msgs = [
            make_email(message_id="<p1@herd.test>", subject="Root"),
            make_email(
                message_id="<c1@herd.test>",
                subject="Re: Root",
                in_reply_to="<p1@herd.test>",
            ),
        ]
        result = import_messages(msgs, db_conn)
        assert result.posts_imported == 1
        assert result.comments_imported == 1
        post_id = db_conn.execute(
            "SELECT id FROM posts WHERE message_id = ?", ("<p1@herd.test>",)
        ).fetchone()["id"]
        cnt = db_conn.execute(
            "SELECT COUNT(*) AS n FROM comments WHERE post_id = ?", (post_id,)
        ).fetchone()["n"]
        assert cnt == 1

    def test_duplicate_message_id_skipped(self, db_conn) -> None:
        msg = make_email(message_id="<dup@herd.test>")
        import_messages([msg], db_conn)
        result = import_messages([make_email(message_id="<dup@herd.test>")], db_conn)
        assert result.skipped == 1
        assert result.posts_imported == 0

    def test_token_cost_and_columns_populated(self, db_conn) -> None:
        import_messages([make_email(message_id="<i2@herd.test>")], db_conn)
        row = db_conn.execute(
            "SELECT token_cost, body_markdown, body_html FROM posts "
            "WHERE message_id = ?",
            ("<i2@herd.test>",),
        ).fetchone()
        assert row["token_cost"] > 0
        assert row["body_markdown"]
        assert row["body_html"]


# --------------------------------------------------------------------------- #
# Functional
# --------------------------------------------------------------------------- #
class TestFunctional:
    """End-to-end import from an mbox archive file."""

    def test_import_mbox_file(self, tmp_path: Path, tmp_db: Path) -> None:
        mbox_path = tmp_path / "archive.mbox"
        write_mbox(
            mbox_path,
            [
                make_email(message_id="<f1@herd.test>", subject="Post", space="essays"),
                make_email(
                    message_id="<f2@herd.test>",
                    subject="Re: Post",
                    in_reply_to="<f1@herd.test>",
                ),
            ],
        )
        result = import_mbox(mbox_path, db_path=tmp_db)
        assert result.posts_imported == 1
        assert result.comments_imported == 1
        conn = get_connection(tmp_db)
        try:
            space = conn.execute(
                "SELECT space FROM posts WHERE message_id = ?", ("<f1@herd.test>",)
            ).fetchone()["space"]
            assert space == "essays"
        finally:
            conn.close()
        drop_tables(tmp_db)

    def test_import_mbox_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            import_mbox(tmp_path / "does-not-exist.mbox")


# --------------------------------------------------------------------------- #
# Security
# --------------------------------------------------------------------------- #
class TestSecurity:
    """Importer must not be an injection vector."""

    def test_sql_injection_in_headers_is_inert(self, db_conn) -> None:
        """Malicious subject/author are stored verbatim via parameterized SQL,
        never executed — the posts table survives intact."""
        payload = "Robert'); DROP TABLE posts;--"
        import_messages(
            [make_email(message_id="<s1@herd.test>", subject=payload)],
            db_conn,
        )
        # Table still exists (query succeeds) and holds the literal payload
        # verbatim — proof the value was bound as a parameter, not executed.
        row = db_conn.execute(
            "SELECT subject FROM posts WHERE message_id = ?", ("<s1@herd.test>",)
        ).fetchone()
        assert row["subject"] == payload
        assert (
            db_conn.execute("SELECT COUNT(*) AS n FROM posts").fetchone()["n"] == 1
        )

    @pytest.mark.parametrize(
        "xss",
        [
            '<script>alert("XSS")</script>',
            '<img src="x" onerror="alert(1)">',
            '<a href="javascript:alert(1)">link</a>',
            '<a href="data:text/html,<script>alert(1)</script>">link</a>',
        ],
    )
    def test_raw_html_preserved_for_downstream_sanitization(
        self, db_conn, xss: str
    ) -> None:
        """The importer stores raw HTML unchanged; sanitization is a render-time
        concern (PRD §5.1). This guarantees nothing is silently dropped on
        ingest and the four mandated XSS payloads reach storage intact so the
        security layer — not the importer — is the single choke point."""
        import_messages(
            [make_email(message_id="<s2@herd.test>", html=f"<div>{xss}</div>")],
            db_conn,
        )
        stored = db_conn.execute(
            "SELECT body_html FROM posts WHERE message_id = ?", ("<s2@herd.test>",)
        ).fetchone()["body_html"]
        assert xss in stored


# --------------------------------------------------------------------------- #
# Performance
# --------------------------------------------------------------------------- #
class TestPerformance:
    """Bulk import stays within a generous time budget (single transaction)."""

    def test_bulk_import_under_budget(self, db_conn) -> None:
        msgs = [
            make_email(message_id=f"<perf-{i}@herd.test>", subject=f"P{i}")
            for i in range(500)
        ]
        start = time.perf_counter()
        result = import_messages(msgs, db_conn)
        elapsed = time.perf_counter() - start
        assert result.posts_imported == 500
        assert elapsed < 5.0, f"import took {elapsed:.2f}s"


# --------------------------------------------------------------------------- #
# Retry
# --------------------------------------------------------------------------- #
class TestRetry:
    """N/A: the importer reads a local file and makes no network/IMAP calls,
    so there is nothing to retry with backoff. Placeholder kept for parity with
    the mandated test-category matrix; retry logic lives with the IMAP
    ingestion path instead."""

    def test_importer_has_no_external_calls(self) -> None:
        import inspect

        from herd_inbox import importer

        source = inspect.getsource(importer)
        for forbidden in ("requests", "httpx", "urllib", "imaplib", "socket"):
            assert forbidden not in source


# --------------------------------------------------------------------------- #
# Frame (smoke)
# --------------------------------------------------------------------------- #
class TestFrame:
    """Cheap smoke tests that the module wires together."""

    def test_empty_import_is_noop(self, db_conn) -> None:
        result = import_messages([], db_conn)
        assert isinstance(result, ImportResult)
        assert result.total == 0

    def test_import_result_total(self) -> None:
        assert ImportResult(posts_imported=2, comments_imported=3).total == 5
