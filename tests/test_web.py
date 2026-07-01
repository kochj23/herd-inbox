"""Tests for the server-rendered web routes (STATUS.md #4 / #5).

Covers all seven mandated categories: Security, Performance, Retry, Unit,
Integration, Functional, and Frame (smoke).
"""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from herd_inbox.db import get_connection
from herd_inbox.routes.web import sanitize_html


# --------------------------------------------------------------------------- #
# Seeding helpers (operate on the same temp DB the client is pointed at)
# --------------------------------------------------------------------------- #
def seed_post(
    *,
    message_id: str,
    subject: str = "Subject",
    author: str = "author@herd.test",
    tldr: str = "A short summary.",
    body_html: str = "<p>Body</p>",
    body_markdown: str = "Body",
    token_cost: int = 10,
    space: str = "inbox",
) -> int:
    """Insert a post, returning its id."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO posts (message_id, author, subject, tldr, body_markdown, "
            "body_html, token_cost, space) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (message_id, author, subject, tldr, body_markdown, body_html,
             token_cost, space),
        )
        conn.commit()
        return int(cur.lastrowid or 0)
    finally:
        conn.close()


def seed_comment(post_id: int, *, author: str, body_html: str) -> None:
    """Insert a comment on a post."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO comments (post_id, author, body_markdown, body_html) "
            "VALUES (?, ?, ?, ?)",
            (post_id, author, "md", body_html),
        )
        conn.commit()
    finally:
        conn.close()


XSS_PAYLOADS = [
    '<script>alert("XSS")</script>',
    '<img src="x" onerror="alert(1)">',
    '<a href="javascript:alert(1)">link</a>',
    '<a href="data:text/html,<script>alert(1)</script>">link</a>',
]


# --------------------------------------------------------------------------- #
# Unit — the sanitizer in isolation
# --------------------------------------------------------------------------- #
class TestUnit:
    def test_removes_script_tags(self) -> None:
        result = sanitize_html('<script>alert("XSS")</script><p>Safe</p>')
        assert "<script>" not in result
        assert "<p>Safe</p>" in result

    def test_strips_event_handlers(self) -> None:
        result = sanitize_html('<img src="x" onerror="alert(1)">')
        assert "onerror" not in result

    def test_strips_javascript_uri(self) -> None:
        result = sanitize_html('<a href="javascript:alert(1)">x</a>')
        assert "javascript:" not in result

    def test_strips_data_uri(self) -> None:
        result = sanitize_html('<a href="data:text/html,<script>x</script>">x</a>')
        assert "data:" not in result
        assert "<script>" not in result

    def test_keeps_allowed_formatting(self) -> None:
        html = "<p><strong>bold</strong> <em>i</em> <code>c</code></p>"
        assert sanitize_html(html) == html

    def test_keeps_safe_links(self) -> None:
        result = sanitize_html('<a href="https://herd.test">ok</a>')
        assert 'href="https://herd.test"' in result

    def test_empty_input(self) -> None:
        assert sanitize_html("") == ""


# --------------------------------------------------------------------------- #
# Integration — routes against a live DB
# --------------------------------------------------------------------------- #
class TestIntegration:
    def test_inbox_lists_posts(self, client: TestClient) -> None:
        seed_post(message_id="<w1@herd.test>", subject="Hello World", tldr="Hi there")
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Hello World" in resp.text
        assert "Hi there" in resp.text

    def test_space_filter(self, client: TestClient) -> None:
        seed_post(message_id="<w2@herd.test>", subject="In Inbox", space="inbox")
        seed_post(message_id="<w3@herd.test>", subject="A Dream", space="dreams")
        resp = client.get("/spaces/dreams")
        assert resp.status_code == 200
        assert "A Dream" in resp.text
        assert "In Inbox" not in resp.text

    def test_thread_shows_post_and_comments(self, client: TestClient) -> None:
        pid = seed_post(
            message_id="<w4@herd.test>",
            subject="Threaded",
            body_html="<p>Full <strong>body</strong></p>",
        )
        seed_comment(pid, author="c@herd.test", body_html="<p>Nice post</p>")
        resp = client.get(f"/thread/{pid}")
        assert resp.status_code == 200
        assert "Threaded" in resp.text
        assert "Full <strong>body</strong>" in resp.text
        assert "Nice post" in resp.text

    def test_thread_links_from_inbox(self, client: TestClient) -> None:
        pid = seed_post(message_id="<w5@herd.test>", subject="Clickable")
        resp = client.get("/")
        assert f'/thread/{pid}' in resp.text


# --------------------------------------------------------------------------- #
# Functional — end-to-end read flow
# --------------------------------------------------------------------------- #
class TestFunctional:
    def test_read_flow(self, client: TestClient) -> None:
        pid = seed_post(
            message_id="<f1@herd.test>",
            subject="Weekly Digest",
            tldr="TLDR of the week",
            body_html="<p>Hello <em>herd</em></p>",
            token_cost=123,
            space="essays",
        )
        seed_comment(pid, author="reply@herd.test", body_html="<p>Great read</p>")

        # 1. Inbox shows the TLDR entry with metadata + link.
        inbox = client.get("/")
        assert "Weekly Digest" in inbox.text
        assert "TLDR of the week" in inbox.text
        assert "123 tokens" in inbox.text

        # 2. Thread view renders the sanitized body and the comment.
        thread = client.get(f"/thread/{pid}")
        assert "Hello <em>herd</em>" in thread.text
        assert "Great read" in thread.text


# --------------------------------------------------------------------------- #
# Security — XSS must not survive rendering
# --------------------------------------------------------------------------- #
class TestSecurity:
    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    def test_xss_payload_neutralized_in_thread(
        self, client: TestClient, payload: str
    ) -> None:
        """The four mandated XSS payloads must be stripped from the rendered
        thread body — no executable script, event handler, or dangerous URI."""
        pid = seed_post(
            message_id=f"<x-{hash(payload)}@herd.test>",
            body_html=f"<div>{payload}</div>",
        )
        resp = client.get(f"/thread/{pid}")
        body = resp.text
        assert "<script>" not in body
        assert "onerror=" not in body
        assert "javascript:" not in body
        # The `data:` URI carrying a script must not survive either.
        assert "data:text/html" not in body

    def test_subject_is_autoescaped_on_inbox(self, client: TestClient) -> None:
        """Plain-text fields are escaped by Jinja autoescaping, so a subject
        containing markup cannot inject an element into the inbox list."""
        seed_post(
            message_id="<xss-subj@herd.test>",
            subject='<script>alert(1)</script>',
        )
        resp = client.get("/")
        assert "<script>alert(1)</script>" not in resp.text
        assert "&lt;script&gt;" in resp.text


# --------------------------------------------------------------------------- #
# Performance — list render stays within budget
# --------------------------------------------------------------------------- #
class TestPerformance:
    def test_inbox_with_many_posts(self, client: TestClient) -> None:
        for i in range(300):
            seed_post(message_id=f"<perf-{i}@herd.test>", subject=f"P{i}")
        start = time.perf_counter()
        resp = client.get("/")
        elapsed = time.perf_counter() - start
        assert resp.status_code == 200
        assert elapsed < 2.0, f"inbox render took {elapsed:.2f}s"


# --------------------------------------------------------------------------- #
# Retry — N/A
# --------------------------------------------------------------------------- #
class TestRetry:
    """N/A: the web routes read the local database and make no network/IMAP
    calls, so there is nothing to retry with backoff. Placeholder kept for
    parity with the mandated test-category matrix."""

    def test_web_routes_have_no_external_calls(self) -> None:
        import inspect

        from herd_inbox.routes import web

        source = inspect.getsource(web)
        for forbidden in ("requests", "httpx", "urllib", "imaplib", "socket"):
            assert forbidden not in source


# --------------------------------------------------------------------------- #
# Frame (smoke)
# --------------------------------------------------------------------------- #
class TestFrame:
    def test_health_still_ok(self, client: TestClient) -> None:
        assert client.get("/health").json() == {"ok": True}

    def test_empty_inbox_renders(self, client: TestClient) -> None:
        resp = client.get("/")
        assert resp.status_code == 200
        assert "No posts yet" in resp.text

    def test_unknown_space_404(self, client: TestClient) -> None:
        assert client.get("/spaces/nope").status_code == 404

    def test_missing_thread_404(self, client: TestClient) -> None:
        assert client.get("/thread/999999").status_code == 404
