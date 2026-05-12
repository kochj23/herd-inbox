"""Token estimation utilities for Herd-Inbox.

Supports multiple tokenizer backends so token cost estimates are accurate
for the model family actually being used. The default is a character-based
heuristic that works without any external dependency.

Set the HERD_TOKENIZER env var to select a backend:
  - "chars"   (default) — ~4 chars/token heuristic, no dependencies
  - "cl100k"  — tiktoken cl100k_base (GPT-4/Claude approximation)
  - "qwen"    — tiktoken o200k_base (closer to Qwen3 BPE vocabulary)

The qwen backend falls back to chars if tiktoken is unavailable.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

TOKENIZER = os.environ.get("HERD_TOKENIZER", "chars").lower()

# Lazy-loaded tiktoken encoder (None if not available / not requested)
_encoder = None


def _load_encoder(encoding_name: str) -> object | None:
    try:
        import tiktoken  # type: ignore[import]
        return tiktoken.get_encoding(encoding_name)
    except Exception as exc:
        logger.warning("tiktoken unavailable (%s) — falling back to chars heuristic", exc)
        return None


def _get_encoder() -> object | None:
    global _encoder
    if _encoder is not None:
        return _encoder
    if TOKENIZER == "cl100k":
        _encoder = _load_encoder("cl100k_base")
    elif TOKENIZER == "qwen":
        # o200k_base is the closest publicly available BPE to Qwen3's tokenizer.
        # Token counts will still be approximate but significantly more accurate
        # than cl100k_base for CJK-heavy or code-heavy content.
        _encoder = _load_encoder("o200k_base")
    return _encoder


def estimate_tokens(text: str) -> int:
    """Return an estimated token count for *text*.

    Uses the backend selected by HERD_TOKENIZER. All backends are approximate —
    the goal is a cheap pre-read signal, not a billing-grade count.
    """
    if not text:
        return 0

    enc = _get_encoder()
    if enc is not None:
        try:
            return len(enc.encode(text))  # type: ignore[attr-defined]
        except Exception as exc:
            logger.warning("Tokenizer encode failed (%s) — falling back to chars", exc)

    # Chars heuristic: ~4 chars per token is a reasonable average for English prose.
    # Adjust for code (denser) vs. natural language (sparser) if needed.
    return max(1, len(text) // 4)
