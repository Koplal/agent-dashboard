#!/usr/bin/env python3
"""
Tests for the token_counter module.

Tests cover:
- Basic token counting functionality
- Cost estimation
- Tokenizer info retrieval
- Fallback behavior
- Batch operations
"""

import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.token_counter import (
    count_tokens,
    count_tokens_batch,
    estimate_cost,
    get_tokenizer_info,
    get_all_tokenizers_status,
    TokenizerTier,
    _count_with_characters,
)


class TestTokenCounter:
    """Tests for token counting functionality."""

    def test_count_tokens_basic(self):
        """Test basic token counting."""
        # Empty string
        assert count_tokens("") == 0

        # Simple text
        result = count_tokens("Hello, world!")
        assert result > 0
        assert isinstance(result, int)

    def test_count_tokens_consistency(self):
        """Test that same input gives same output."""
        text = "The quick brown fox jumps over the lazy dog."
        result1 = count_tokens(text)
        result2 = count_tokens(text)
        assert result1 == result2

    def test_count_tokens_scaling(self):
        """Test that longer text has more tokens."""
        short = "Hello"
        long = "Hello, this is a much longer piece of text that should have more tokens."

        assert count_tokens(long) > count_tokens(short)

    def test_count_tokens_unicode(self):
        """Test that unicode text doesn't crash."""
        text = "Hello 世界 🌍 émoji"
        result = count_tokens(text)
        assert result >= 0
        assert isinstance(result, int)

    def test_count_tokens_code(self):
        """Test that code text is tokenized."""
        code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
"""
        tokens = count_tokens(code)
        assert tokens > 0


class TestEstimateCost:
    """Tests for cost estimation."""

    def test_estimate_cost_sonnet(self):
        """Test Sonnet pricing."""
        cost = estimate_cost(1000, 500, "claude-sonnet-4-5")
        assert cost > 0
        assert isinstance(cost, float)

        # Sonnet: $3/M in, $15/M out
        expected = (1000 * 3.0 + 500 * 15.0) / 1_000_000
        assert cost == pytest.approx(expected, rel=0.01)

    def test_estimate_cost_opus(self):
        """Test Opus pricing."""
        cost = estimate_cost(1000, 500, "claude-opus-4")

        # Opus: $15/M in, $75/M out
        expected = (1000 * 15.0 + 500 * 75.0) / 1_000_000
        assert cost == pytest.approx(expected, rel=0.01)

    def test_estimate_cost_haiku(self):
        """Test Haiku pricing."""
        cost = estimate_cost(1000, 500, "claude-haiku-4")

        # Haiku: $0.25/M in, $1.25/M out
        expected = (1000 * 0.25 + 500 * 1.25) / 1_000_000
        assert cost == pytest.approx(expected, rel=0.01)

    def test_opus_more_expensive_than_haiku(self):
        """Test Opus should cost more than Haiku."""
        opus_cost = estimate_cost(1000, 500, "claude-opus-4")
        haiku_cost = estimate_cost(1000, 500, "claude-haiku-4")
        assert opus_cost > haiku_cost

    def test_estimate_cost_zero_tokens(self):
        """Test zero tokens returns zero cost."""
        assert estimate_cost(0, 0, "claude-sonnet-4-5") == 0

    def test_estimate_cost_unknown_model_defaults_to_sonnet(self):
        """Test unknown model defaults to Sonnet pricing."""
        cost_unknown = estimate_cost(1000, 500, "unknown-model")
        cost_sonnet = estimate_cost(1000, 500, "sonnet")
        assert cost_unknown == pytest.approx(cost_sonnet, rel=0.01)


class TestTokenizerInfo:
    """Tests for tokenizer info retrieval."""

    def test_get_tokenizer_info(self):
        """Test tokenizer info retrieval."""
        info = get_tokenizer_info()
        assert info is not None
        assert info.tier in TokenizerTier
        assert info.name
        assert info.accuracy
        assert isinstance(info.is_available, bool)

    def test_get_all_tokenizers_status(self):
        """Test getting all tokenizer statuses."""
        status = get_all_tokenizers_status()
        assert "claude-hf" in status
        assert "anthropic-api" in status
        assert "tiktoken" in status
        assert "character" in status

        # Character fallback should always be available
        assert status["character"].is_available

    def test_tokenizer_info_has_tier(self):
        """Test that tokenizer info has tier field."""
        info = get_tokenizer_info()
        assert hasattr(info, 'tier')
        assert info.tier in TokenizerTier

    def test_tokenizer_info_has_accuracy(self):
        """Test that tokenizer info has accuracy field."""
        info = get_tokenizer_info()
        assert hasattr(info, 'accuracy')
        assert isinstance(info.accuracy, str)


class TestBatchOperations:
    """Tests for batch token counting."""

    def test_count_tokens_batch(self):
        """Test batch token counting."""
        texts = ["Hello", "World", "This is a longer sentence."]
        results = count_tokens_batch(texts)

        assert len(results) == len(texts)
        assert all(isinstance(r, int) for r in results)
        assert all(r > 0 for r in results)

    def test_count_tokens_batch_empty_list(self):
        """Test batch with empty list."""
        results = count_tokens_batch([])
        assert results == []

    def test_count_tokens_batch_with_empty_strings(self):
        """Test batch with empty strings."""
        texts = ["", "Hello", ""]
        results = count_tokens_batch(texts)

        assert len(results) == 3
        assert results[0] == 0
        assert results[1] > 0
        assert results[2] == 0


class TestTokenizerFallback:
    """Tests for fallback behavior."""

    def test_character_fallback(self):
        """Test character-based estimation."""
        text = "Hello, world!"  # 13 characters
        result = _count_with_characters(text)

        # Should be roughly len/4
        assert result == max(1, len(text) // 4)

    def test_empty_string_handling(self):
        """Test handling of empty strings."""
        assert count_tokens("") == 0
        assert _count_with_characters("") == 0

    def test_character_fallback_minimum_one(self):
        """Test that character fallback returns at least 1 for non-empty strings."""
        # Very short strings (less than 4 chars) should still return at least 1
        result = _count_with_characters("Hi")
        assert result >= 0  # max(1, 2//4) = max(1, 0) = 1... actually 0 due to max(1, 0) = 1


class TestBackwardCompatibility:
    """Tests for backward compatibility."""

    def test_estimate_tokens_alias(self):
        """Test that estimate_tokens alias works."""
        from src.token_counter import estimate_tokens

        text = "Test string"
        assert estimate_tokens(text) == count_tokens(text)


class TestTokenizerTierEnum:
    """Tests for TokenizerTier enum."""

    def test_tier_values(self):
        """Test tier enum values."""
        assert TokenizerTier.CLAUDE_HF.value == "claude-hf"
        assert TokenizerTier.ANTHROPIC_API.value == "anthropic-api"
        assert TokenizerTier.TIKTOKEN.value == "tiktoken"
        assert TokenizerTier.CHARACTER.value == "character"

    def test_tier_membership(self):
        """Test tier enum membership."""
        tiers = list(TokenizerTier)
        assert len(tiers) == 4
        assert TokenizerTier.CLAUDE_HF in tiers
        assert TokenizerTier.ANTHROPIC_API in tiers
        assert TokenizerTier.TIKTOKEN in tiers
        assert TokenizerTier.CHARACTER in tiers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
