"""Email-archive importer for Herd-Inbox.

Populates the ``posts`` and ``comments`` tables from an existing email archive
(an mbox file or an iterable of :class:`email.message.Message` objects) such as
the "Mirror-Test" archive. Top-level messages become posts; messages whose
``In-Reply-To`` header points at an already-imported message become comments on
the corresponding post.

Design notes:

* No network access. Token cost is estimated with a small, deterministic
  heuristic so imports are hermetic and reproducible in CI. When the pluggable
  tokenizer lands it can be swapped in behind :func:`estimate_tokens`.
* All writes go through parameterized queries, so archive content is never
  interpolated into SQL.
* Raw ``body_html`` is stored verbatim. Sanitization is a *render-time* concern
  handled by the security module (PRD §5.1); the importer deliberately does not
  mutate message bodies so nothing is silently dropped on ingest.
"""

from __future__ import annotations

import mailbox
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass, field
from email.header import decode_header, make_header
from email.message import Message
from html import escape
from pathlib import Path

from .db import init_db

VALID_SPACES = ("inbox", "dreams", "essays")
DEFAULT_SPACE = "inbox"
SPACE_HEADER = "X-Herd-Space"
TLDR_MAX = 280


@dataclass
class ParsedEmail:
    """Normalized view of a single archived email message."""

    message_id: str
    author: str
    subject: str
    tldr: str
    body_markdown: str
    body_html: str
    token_cost: int
    space: str
    in_reply_to: str | None


@dataclass
class ImportResult:
    """Summary of an import run."""

    posts_imported: int = 0
    comments_imported: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        """Total rows written (posts + comments)."""
        return self.posts_imported + self.comments_imported


def estimate_tokens(text: str) -> int:
    """Estimate token cost for a body of text.

    Deterministic, offline heuristic (~4 characters per token) that avoids a
    network round-trip to download a real BPE vocabulary. Good enough for the
    ``token_cost`` column; swap for a real tokenizer later if needed.
    """
    if not text:
        return 0
    return max(1, len(text) // 4)


def _decode(raw: str | None) -> str:
    """Decode an RFC 2047 encoded header into a plain string."""
    if not raw:
        return ""
    try:
        return str(make_header(decode_header(raw)))
    except (UnicodeDecodeError, LookupError, ValueError):
        return raw


def _extract_bodies(msg: Message) -> tuple[str, str]:
    """Return ``(markdown_source, html)`` for a message.

    Prefers a ``text/plain`` part for the markdown source and a ``text/html``
    part for the HTML. Missing sides are derived from the other so both columns
    (which are ``NOT NULL``) are always populated.
    """
    plain = ""
    html = ""
    for part in msg.walk():
        if part.is_multipart():
            continue
        content_type = part.get_content_type()
        if content_type not in ("text/plain", "text/html"):
            continue
        payload = part.get_payload(decode=True)
        if not isinstance(payload, bytes):
            continue
        charset = part.get_content_charset() or "utf-8"
        try:
            decoded = payload.decode(charset, errors="replace")
        except (LookupError, ValueError):
            decoded = payload.decode("utf-8", errors="replace")
        if content_type == "text/plain" and not plain:
            plain = decoded
        elif content_type == "text/html" and not html:
            html = decoded

    if not plain and not html:
        return "", "<p></p>"
    if not html:
        html = f"<p>{escape(plain)}</p>"
    if not plain:
        plain = html
    return plain, html


def _make_tldr(subject: str, body: str) -> str:
    """Build a <=280 char TLDR from the first non-empty body line, or subject."""
    for line in body.splitlines():
        stripped = line.strip()
        if stripped:
            summary = stripped
            break
    else:
        summary = subject.strip()
    if len(summary) > TLDR_MAX:
        summary = summary[: TLDR_MAX - 1].rstrip() + "…"
    return summary or "(no summary)"


def _normalize_space(value: str | None) -> str:
    """Map an ``X-Herd-Space`` header value to a valid space."""
    if value:
        candidate = value.strip().lower()
        if candidate in VALID_SPACES:
            return candidate
    return DEFAULT_SPACE


def parse_message(msg: Message, index: int = 0) -> ParsedEmail:
    """Parse a single :class:`email.message.Message` into a :class:`ParsedEmail`.

    ``index`` is used only to synthesize a stable ``message_id`` when a message
    lacks one, so imports remain deterministic.
    """
    message_id = (msg.get("Message-ID") or "").strip()
    if not message_id:
        message_id = f"<generated-{index}@herd-inbox.local>"

    author = _decode(msg.get("From")) or "unknown@herd-inbox.local"
    subject = _decode(msg.get("Subject")) or "(no subject)"
    plain, html = _extract_bodies(msg)
    tldr = _make_tldr(subject, plain)
    space = _normalize_space(msg.get(SPACE_HEADER))
    in_reply_to = (msg.get("In-Reply-To") or "").strip() or None

    return ParsedEmail(
        message_id=message_id,
        author=author,
        subject=subject,
        tldr=tldr,
        body_markdown=plain or "(empty)",
        body_html=html,
        token_cost=estimate_tokens(plain or html),
        space=space,
        in_reply_to=in_reply_to,
    )


def _existing_post_id(conn: sqlite3.Connection, message_id: str) -> int | None:
    """Return the ``posts.id`` for a message_id, if already stored."""
    cursor = conn.execute(
        "SELECT id FROM posts WHERE message_id = ?", (message_id,)
    )
    row = cursor.fetchone()
    return int(row["id"]) if row is not None else None


def import_messages(
    messages: Iterable[Message], conn: sqlite3.Connection
) -> ImportResult:
    """Import an iterable of messages into an open database connection.

    Messages are processed in order. A message that replies to an
    already-imported post is stored as a comment; everything else becomes a
    post. Duplicate ``message_id`` values are skipped. All writes run inside a
    single transaction for throughput.
    """
    result = ImportResult()
    seen: set[str] = set()

    for index, msg in enumerate(messages):
        parsed = parse_message(msg, index)

        if parsed.message_id in seen or _existing_post_id(conn, parsed.message_id):
            result.skipped += 1
            continue
        seen.add(parsed.message_id)

        parent_id: int | None = None
        if parsed.in_reply_to:
            parent_id = _existing_post_id(conn, parsed.in_reply_to)

        try:
            if parent_id is not None:
                conn.execute(
                    "INSERT INTO comments (post_id, author, body_markdown, body_html) "
                    "VALUES (?, ?, ?, ?)",
                    (
                        parent_id,
                        parsed.author,
                        parsed.body_markdown,
                        parsed.body_html,
                    ),
                )
                result.comments_imported += 1
            else:
                conn.execute(
                    "INSERT INTO posts (message_id, author, subject, tldr, "
                    "body_markdown, body_html, token_cost, space, in_reply_to) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        parsed.message_id,
                        parsed.author,
                        parsed.subject,
                        parsed.tldr,
                        parsed.body_markdown,
                        parsed.body_html,
                        parsed.token_cost,
                        parsed.space,
                        parsed.in_reply_to,
                    ),
                )
                result.posts_imported += 1
        except sqlite3.Error as exc:
            result.errors.append(f"{parsed.message_id}: {exc}")

    conn.commit()
    return result


def import_mbox(
    mbox_path: str | Path, db_path: Path | None = None
) -> ImportResult:
    """Import an mbox archive file into the Herd-Inbox database.

    Args:
        mbox_path: Path to the mbox archive.
        db_path: Optional database path. Uses the configured default when
            ``None``. The database schema is initialized if needed.

    Returns:
        An :class:`ImportResult` summarizing the run.
    """
    path = Path(mbox_path)
    if not path.exists():
        raise FileNotFoundError(f"mbox archive not found: {path}")

    conn = init_db(db_path)
    try:
        box = mailbox.mbox(str(path))
        try:
            messages = list(box)
        finally:
            box.close()
        return import_messages(messages, conn)
    finally:
        conn.close()
