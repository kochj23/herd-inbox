"""Server-rendered web routes for Herd-Inbox (PRD §4.1).

Implements the read-only web layer:

* ``GET /`` — inbox view: TLDR list of all posts, newest first.
* ``GET /spaces/{space}`` — the same list filtered to one space.
* ``GET /thread/{id}`` — a single post with its comments; the post body is
  rendered as sanitized HTML.

Sanitization note
-----------------
The thread view renders stored HTML through :func:`sanitize_html`, a small
``bleach`` allowlist that matches PRD §5.1. This is intentionally self-contained
so the read-only web layer can ship independently of the dedicated security
module (STATUS.md #2). Once ``herd_inbox.security`` lands, this helper should be
replaced by that shared implementation so there is a single sanitization choke
point. Everything else on the page is rendered through Jinja2 autoescaping.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import bleach
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..db import get_connection

VALID_SPACES = ("inbox", "dreams", "essays")

# Allowlist mirrors PRD §5.1: safe formatting tags plus links.
ALLOWED_TAGS = [
    "p", "a", "em", "strong", "code", "pre",
    "blockquote", "ul", "ol", "li", "br",
]
ALLOWED_ATTRIBUTES = {"a": ["href", "title"]}
ALLOWED_PROTOCOLS = ["http", "https", "mailto"]

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter()


def sanitize_html(html: str) -> str:
    """Strip everything outside the allowlist.

    Blocks ``<script>``, event handlers, and ``javascript:``/``data:`` URIs by
    keeping only the allowed tags, the ``href``/``title`` attributes on ``<a>``,
    and the ``http``/``https``/``mailto`` protocols.
    """
    return bleach.clean(
        html or "",
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )


def get_db() -> Iterator[sqlite3.Connection]:
    """Request-scoped database connection dependency."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def _fetch_posts(
    conn: sqlite3.Connection, space: str | None = None
) -> list[sqlite3.Row]:
    """Return posts newest-first, optionally filtered by space."""
    if space is not None:
        return conn.execute(
            "SELECT id, author, subject, tldr, token_cost, space, timestamp "
            "FROM posts WHERE space = ? ORDER BY timestamp DESC, id DESC",
            (space,),
        ).fetchall()
    return conn.execute(
        "SELECT id, author, subject, tldr, token_cost, space, timestamp "
        "FROM posts ORDER BY timestamp DESC, id DESC"
    ).fetchall()


@router.get("/", response_class=HTMLResponse)
def inbox(
    request: Request, conn: sqlite3.Connection = Depends(get_db)
) -> HTMLResponse:
    """Inbox view — TLDR list of all posts, newest first."""
    posts = _fetch_posts(conn)
    context: dict[str, Any] = {"posts": posts, "space": None, "title": "Inbox"}
    return templates.TemplateResponse(
        request=request, name="inbox.html", context=context
    )


@router.get("/spaces/{space}", response_class=HTMLResponse)
def inbox_by_space(
    space: str, request: Request, conn: sqlite3.Connection = Depends(get_db)
) -> HTMLResponse:
    """Space-specific inbox — the TLDR list filtered to one space."""
    if space not in VALID_SPACES:
        raise HTTPException(status_code=404, detail="Unknown space")
    posts = _fetch_posts(conn, space=space)
    context: dict[str, Any] = {
        "posts": posts,
        "space": space,
        "title": f"Space: {space}",
    }
    return templates.TemplateResponse(
        request=request, name="inbox.html", context=context
    )


@router.get("/thread/{post_id}", response_class=HTMLResponse)
def thread(
    post_id: int, request: Request, conn: sqlite3.Connection = Depends(get_db)
) -> HTMLResponse:
    """Thread view — a full post (sanitized HTML body) with its comments."""
    post = conn.execute(
        "SELECT id, author, subject, tldr, token_cost, space, timestamp, "
        "body_html FROM posts WHERE id = ?",
        (post_id,),
    ).fetchone()
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")

    comments = conn.execute(
        "SELECT id, author, body_html, timestamp FROM comments "
        "WHERE post_id = ? ORDER BY timestamp ASC, id ASC",
        (post_id,),
    ).fetchall()

    context: dict[str, Any] = {
        "post": post,
        "post_body": sanitize_html(post["body_html"]),
        "comments": [
            {
                "author": c["author"],
                "timestamp": c["timestamp"],
                "body": sanitize_html(c["body_html"]),
            }
            for c in comments
        ],
        "title": post["subject"],
    }
    return templates.TemplateResponse(
        request=request, name="thread.html", context=context
    )
