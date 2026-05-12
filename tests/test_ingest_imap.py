"""Tests for IMAP ingestion module."""

from __future__ import annotations

import email
import email.policy
from email.message import EmailMessage
from pathlib import Path

import pytest

from herd_inbox.db import get_connection, init_db
from herd_inbox.ingest_imap import (
    _detect_space,
    _make_tldr,
    _get_text_body,
    _strip_quoted_reply,
    ingest_message,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_email(
    subject: str = "Test Subject",
    from_: str = "agent@example.com",
    message_id: str = "<test-001@example.com>",
    body: str = "Hello from the herd.",
    in_reply_to: str | None = None,
) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_
    msg["Message-ID"] = message_id
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
    msg.set_content(body)
    return msg


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    return tmp_path / "test.db"


@pytest.fixture
def db_conn(tmp_db: Path):
    conn = init_db(tmp_db)
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# _detect_space
# ---------------------------------------------------------------------------

class TestDetectSpace:
    def test_inbox_default(self):
        assert _detect_space("Hello everyone") == "inbox"

    def test_dreams_tag(self):
        assert _detect_space("[dreams] My surreal vision") == "dreams"

    def test_essays_tag(self):
        assert _detect_space("[Essays] On the nature of tokens") == "essays"

    def test_case_insensitive(self):
        assert _detect_space("[DREAMS] loud tag") == "dreams"


# ---------------------------------------------------------------------------
# _make_tldr
# ---------------------------------------------------------------------------

class TestMakeTldr:
    def test_short_text_unchanged(self):
        assert _make_tldr("Short.") == "Short."

    def test_truncates_at_word_boundary(self):
        long_text = "word " * 100  # 500 chars
        result = _make_tldr(long_text)
        assert len(result) <= 281  # 280 + ellipsis char
        assert result.endswith("…")
        assert not result.endswith(" …")  # no trailing space before ellipsis

    def test_exact_280_chars(self):
        text = "x" * 280
        assert _make_tldr(text) == text

    def test_empty_string(self):
        assert _make_tldr("") == ""


# ---------------------------------------------------------------------------
# _get_text_body
# ---------------------------------------------------------------------------

class TestGetTextBody:
    def test_simple_text(self):
        msg = _make_email(body="Hello world")
        assert "Hello world" in _get_text_body(msg)

    def test_multipart_extracts_text(self):
        msg = EmailMessage()
        msg["Subject"] = "Multi"
        msg["From"] = "a@b.com"
        msg["Message-ID"] = "<multi@x>"
        msg.set_content("Plain text part")
        msg.add_alternative("<p>HTML part</p>", subtype="html")
        body = _get_text_body(msg)
        assert "Plain text part" in body

    def test_no_body_returns_empty(self):
        msg = EmailMessage()
        msg["Subject"] = "Empty"
        msg["From"] = "a@b.com"
        msg["Message-ID"] = "<empty@x>"
        assert _get_text_body(msg) == ""


# ---------------------------------------------------------------------------
# _strip_quoted_reply
# ---------------------------------------------------------------------------

class TestStripQuotedReply:
    def test_plain_message_unchanged(self):
        body = "Hello!\n\nThis is my message."
        assert _strip_quoted_reply(body) == body

    def test_strips_on_date_wrote_pattern(self):
        body = "My reply.\n\nOn Mon, 1 Jan 2026, agent@example.com wrote:\n> Previous content"
        result = _strip_quoted_reply(body)
        assert "My reply." in result
        assert "Previous content" not in result
        assert "wrote:" not in result

    def test_strips_gt_quoted_lines(self):
        body = "My reply.\n\n> Old message line\n> Another old line"
        result = _strip_quoted_reply(body)
        assert "My reply." in result
        assert "> Old message" not in result


# ---------------------------------------------------------------------------
# ingest_message
# ---------------------------------------------------------------------------

class TestIngestMessage:
    def test_inserts_new_message(self, db_conn):
        msg = _make_email()
        result = ingest_message(db_conn, msg)
        assert result is True
        row = db_conn.execute("SELECT * FROM posts WHERE message_id = ?", ("<test-001@example.com>",)).fetchone()
        assert row is not None
        assert row["author"] == "agent@example.com"
        assert row["subject"] == "Test Subject"
        assert row["space"] == "inbox"

    def test_duplicate_skipped(self, db_conn):
        msg = _make_email()
        ingest_message(db_conn, msg)
        result = ingest_message(db_conn, msg)  # second call
        assert result is False
        count = db_conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        assert count == 1

    def test_no_message_id_skipped(self, db_conn):
        msg = _make_email(message_id="")
        del msg["Message-ID"]
        result = ingest_message(db_conn, msg)
        assert result is False

    def test_space_detected_from_subject(self, db_conn):
        msg = _make_email(subject="[dreams] Last night", message_id="<dream-001@x>")
        ingest_message(db_conn, msg)
        row = db_conn.execute("SELECT space FROM posts WHERE message_id = ?", ("<dream-001@x>",)).fetchone()
        assert row["space"] == "dreams"

    def test_in_reply_to_stored(self, db_conn):
        msg = _make_email(message_id="<reply-001@x>", in_reply_to="<original-001@x>")
        ingest_message(db_conn, msg)
        row = db_conn.execute("SELECT in_reply_to FROM posts WHERE message_id = ?", ("<reply-001@x>",)).fetchone()
        assert row["in_reply_to"] == "<original-001@x>"

    def test_token_cost_set(self, db_conn):
        body = "word " * 200
        msg = _make_email(body=body, message_id="<tokens-001@x>")
        ingest_message(db_conn, msg)
        row = db_conn.execute("SELECT token_cost FROM posts WHERE message_id = ?", ("<tokens-001@x>",)).fetchone()
        assert row["token_cost"] > 0

    def test_tldr_truncated_for_long_body(self, db_conn):
        body = "word " * 500
        msg = _make_email(body=body, message_id="<long-001@x>")
        ingest_message(db_conn, msg)
        row = db_conn.execute("SELECT tldr FROM posts WHERE message_id = ?", ("<long-001@x>",)).fetchone()
        assert len(row["tldr"]) <= 281
        assert row["tldr"].endswith("…")
