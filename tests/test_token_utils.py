"""Tests for token estimation utilities."""

from __future__ import annotations

import os
import pytest

from herd_inbox.token_utils import estimate_tokens


class TestEstimateTokens:
    def test_empty_string_returns_zero(self):
        assert estimate_tokens("") == 0

    def test_non_empty_returns_positive(self):
        assert estimate_tokens("Hello, world!") > 0

    def test_longer_text_more_tokens(self):
        short = "Hello"
        long = "Hello " * 100
        assert estimate_tokens(long) > estimate_tokens(short)

    def test_chars_backend_heuristic(self, monkeypatch):
        monkeypatch.setenv("HERD_TOKENIZER", "chars")
        # Force module reload so TOKENIZER constant picks up env var
        import importlib
        import herd_inbox.token_utils as tu
        monkeypatch.setattr(tu, "TOKENIZER", "chars")
        monkeypatch.setattr(tu, "_encoder", None)
        text = "a" * 400
        assert tu.estimate_tokens(text) == 100  # 400 // 4

    def test_single_char_returns_one(self):
        # Even a single character should return at least 1 token
        assert estimate_tokens("x") >= 1

    def test_whitespace_only(self):
        assert estimate_tokens("   ") >= 1


class TestTokenizerBackendSelection:
    """Test that the HERD_TOKENIZER env var controls backend selection."""

    def test_chars_backend_uses_heuristic(self, monkeypatch):
        import herd_inbox.token_utils as tu
        monkeypatch.setattr(tu, "TOKENIZER", "chars")
        monkeypatch.setattr(tu, "_encoder", None)
        # 800 chars → 200 tokens under the 4-chars/token heuristic
        text = "w" * 800
        assert tu.estimate_tokens(text) == 200

    def test_unknown_backend_falls_back_to_chars(self, monkeypatch):
        import herd_inbox.token_utils as tu
        monkeypatch.setattr(tu, "TOKENIZER", "unknown_backend")
        monkeypatch.setattr(tu, "_encoder", None)
        result = tu.estimate_tokens("hello world")
        assert result > 0

    def test_tiktoken_unavailable_falls_back_gracefully(self, monkeypatch):
        """If tiktoken raises on import, estimate_tokens should not crash."""
        import herd_inbox.token_utils as tu
        monkeypatch.setattr(tu, "TOKENIZER", "qwen")
        monkeypatch.setattr(tu, "_encoder", None)

        original_load = tu._load_encoder

        def broken_load(name: str) -> None:
            return None

        monkeypatch.setattr(tu, "_load_encoder", broken_load)
        result = tu.estimate_tokens("test text")
        assert result > 0
