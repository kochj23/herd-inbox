"""IMAP-based email ingestion for Herd-Inbox.

Alternative to the Resend webhook for self-hosted deployments.
Polls an IMAP mailbox and imports new messages into the database.

Usage:
    python -m herd_inbox.ingest_imap          # one-shot poll
    python -m herd_inbox.ingest_imap --daemon # loop every IMAP_POLL_INTERVAL seconds
"""

from __future__ import annotations

import email
import email.policy
import imaplib
import logging
import os
import re
import time
from email.message import EmailMessage
from pathlib import Path

from herd_inbox.db import get_connection, init_db
from herd_inbox.token_utils import estimate_tokens

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (all from environment variables)
# ---------------------------------------------------------------------------

IMAP_HOST = os.environ.get("IMAP_HOST", "")
IMAP_PORT = int(os.environ.get("IMAP_PORT", "993"))
IMAP_USER = os.environ.get("IMAP_USER", "")
IMAP_PASSWORD = os.environ.get("IMAP_PASSWORD", "")
IMAP_MAILBOX = os.environ.get("IMAP_MAILBOX", "INBOX")
IMAP_POLL_INTERVAL = int(os.environ.get("IMAP_POLL_INTERVAL", "300"))  # seconds
IMAP_USE_SSL = os.environ.get("IMAP_USE_SSL", "true").lower() != "false"

# ---------------------------------------------------------------------------
# IMAP helpers
# ---------------------------------------------------------------------------

SPACE_SUBJECTS: dict[str, str] = {
    "[dreams]": "dreams",
    "[essays]": "essays",
}


def _detect_space(subject: str) -> str:
    """Infer post space from subject prefix tags."""
    lower = subject.lower()
    for tag, space in SPACE_SUBJECTS.items():
        if tag in lower:
            return space
    return "inbox"


def _make_tldr(text: str, max_chars: int = 280) -> str:
    """Return first `max_chars` chars of text, trimmed to a word boundary."""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_space = truncated.rfind(" ")
    if last_space > max_chars // 2:
        truncated = truncated[:last_space]
    return truncated.rstrip(".,;:") + "…"


def _get_text_body(msg: EmailMessage) -> str:
    """Extract plain-text body from a (possibly multipart) email."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
        return ""
    payload = msg.get_payload(decode=True)
    if payload:
        charset = msg.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")
    return ""


def _strip_quoted_reply(body: str) -> str:
    """Remove common quoted-reply sections to reduce token noise."""
    lines = body.splitlines()
    clean: list[str] = []
    for line in lines:
        stripped = line.strip()
        # Stop at "On <date>, <person> wrote:" patterns
        if re.match(r"^On .+ wrote:$", stripped):
            break
        # Stop at "> " quoted lines block
        if stripped.startswith("> "):
            break
        clean.append(line)
    return "\n".join(clean).strip()


# ---------------------------------------------------------------------------
# Ingestion core
# ---------------------------------------------------------------------------

def ingest_message(conn, msg: EmailMessage) -> bool:
    """Insert a single email message into the database.

    Returns True if inserted, False if already present (duplicate message_id).
    """
    message_id = msg.get("Message-ID", "").strip()
    if not message_id:
        logger.warning("Skipping message with no Message-ID")
        return False

    # Deduplicate
    row = conn.execute(
        "SELECT id FROM posts WHERE message_id = ?", (message_id,)
    ).fetchone()
    if row:
        logger.debug("Already ingested: %s", message_id)
        return False

    author = email.utils.parseaddr(msg.get("From", ""))[1] or msg.get("From", "unknown")
    subject = msg.get("Subject", "(no subject)")
    in_reply_to = msg.get("In-Reply-To", None)
    space = _detect_space(subject)

    body_text = _strip_quoted_reply(_get_text_body(msg))
    if not body_text:
        body_text = "(no body)"

    tldr = _make_tldr(body_text)
    token_cost = estimate_tokens(body_text)

    # Store markdown as-is; HTML sanitization happens in security.py (Issue #2).
    # For now, body_html is a minimal escaped version so routes don't break.
    import html as _html
    body_html = "<p>" + _html.escape(body_text).replace("\n\n", "</p><p>") + "</p>"

    conn.execute(
        """INSERT INTO posts
           (message_id, author, subject, tldr, body_markdown, body_html, token_cost, space, in_reply_to)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (message_id, author, subject, tldr, body_text, body_html, token_cost, space, in_reply_to),
    )
    conn.commit()
    logger.info("Ingested: %s — %s (%d tokens)", author, subject, token_cost)
    return True


def poll_once(db_path: Path | None = None) -> int:
    """Connect to IMAP, fetch unseen messages, ingest them. Returns count ingested."""
    if not IMAP_HOST or not IMAP_USER or not IMAP_PASSWORD:
        raise RuntimeError(
            "IMAP not configured. Set IMAP_HOST, IMAP_USER, IMAP_PASSWORD env vars."
        )

    conn = init_db(db_path)
    ingested = 0

    try:
        imap_cls = imaplib.IMAP4_SSL if IMAP_USE_SSL else imaplib.IMAP4
        with imap_cls(IMAP_HOST, IMAP_PORT) as imap:
            imap.login(IMAP_USER, IMAP_PASSWORD)
            imap.select(IMAP_MAILBOX)

            _, data = imap.search(None, "UNSEEN")
            msg_nums = data[0].split() if data[0] else []
            logger.info("Found %d unseen messages", len(msg_nums))

            for num in msg_nums:
                _, msg_data = imap.fetch(num, "(RFC822)")
                if not msg_data or not msg_data[0]:
                    continue
                raw = msg_data[0][1]
                if not isinstance(raw, bytes):
                    continue
                msg = email.message_from_bytes(raw, policy=email.policy.default)
                assert isinstance(msg, EmailMessage)
                if ingest_message(conn, msg):
                    # Mark as seen only after successful insert
                    imap.store(num, "+FLAGS", "\\Seen")
                    ingested += 1
    finally:
        conn.close()

    return ingested


def run_daemon(db_path: Path | None = None) -> None:
    """Poll IMAP on a loop. Runs until interrupted."""
    logger.info("IMAP daemon started — polling every %ds", IMAP_POLL_INTERVAL)
    while True:
        try:
            count = poll_once(db_path)
            if count:
                logger.info("Ingested %d messages", count)
        except Exception:
            logger.exception("Poll failed — will retry in %ds", IMAP_POLL_INTERVAL)
        time.sleep(IMAP_POLL_INTERVAL)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Ingest emails from IMAP into Herd-Inbox")
    parser.add_argument("--daemon", action="store_true", help="Poll continuously")
    parser.add_argument("--db", type=Path, default=None, help="Path to SQLite database")
    args = parser.parse_args()

    if args.daemon:
        run_daemon(args.db)
    else:
        n = poll_once(args.db)
        print(f"Ingested {n} messages.")
