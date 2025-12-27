#!/usr/bin/env python3
"""Tests for P2-003: Tiered Token Counting. Version: 2.7.0"""
import pytest
import time

class TestTokenCountResult:
    def test_result_has_count(self):
        from src.utils.tiered_token_counter import TokenCountResult
        r = TokenCountResult(count=100, method="estimation", confidence=0.7, cached=False)
        assert r.count == 100

    def test_result_has_method(self):
        from src.utils.tiered_token_counter import TokenCountResult
        r = TokenCountResult(count=100, method="tiktoken", confidence=0.95, cached=False)
        assert r.method == "tiktoken"

    def test_result_has_confidence(self):
        from src.utils.tiered_token_counter import TokenCountResult
        r = TokenCountResult(count=100, method="xenova", confidence=0.999, cached=False)
        assert r.confidence == 0.999

    def test_result_has_cached(self):
        from src.utils.tiered_token_counter import TokenCountResult
        r = TokenCountResult(count=100, method="estimation", confidence=0.7, cached=True)
        assert r.cached is True

class TestTokenCounterConfig:
    def test_config_default_values(self):
        from src.utils.tiered_token_counter import TokenCounterConfig
        c = TokenCounterConfig()
        assert c.enable_xenova is True
        assert c.enable_tiktoken is True
        assert c.short_text_threshold == 1000
        assert c.cache_ttl == 3600

    def test_config_custom_values(self):
        from src.utils.tiered_token_counter import TokenCounterConfig
        c = TokenCounterConfig(enable_xenova=False, short_text_threshold=500)
        assert c.enable_xenova is False
        assert c.short_text_threshold == 500

    def test_config_xenova_timeout(self):
        from src.utils.tiered_token_counter import TokenCounterConfig
        c = TokenCounterConfig(xenova_timeout=60)
        assert c.xenova_timeout == 60

class TestCharacterEstimation:
    def test_estimate_basic(self):
        from src.utils.tiered_token_counter import TieredTokenCounter
        counter = TieredTokenCounter()
        result = counter._count_with_estimation("Hello world")
        assert result.count > 0
        assert result.method == "estimation"
        assert result.confidence == 0.70

    def test_estimate_empty_string(self):
        from src.utils.tiered_token_counter import TieredTokenCounter
        counter = TieredTokenCounter()
        result = counter._count_with_estimation("")
        assert result.count == 0

    def test_estimate_formula(self):
        from src.utils.tiered_token_counter import TieredTokenCounter
        counter = TieredTokenCounter()
        text = "a" * 100
        result = counter._count_with_estimation(text)
        assert result.count == 25  # 100 / 4

    def test_estimate_unicode(self):
        from src.utils.tiered_token_counter import TieredTokenCounter
        counter = TieredTokenCounter()
        result = counter._count_with_estimation("Hello world emoji")
        assert result.count >= 0

class TestFallbackChain:
    def test_short_text_uses_estimation(self):
        from src.utils.tiered_token_counter import TieredTokenCounter, TokenCounterConfig
        config = TokenCounterConfig(short_text_threshold=1000)
        counter = TieredTokenCounter(config)
        result = counter.count("Short text")
        assert result.method == "estimation"

    def test_fallback_always_succeeds(self):
        from src.utils.tiered_token_counter import TieredTokenCounter, TokenCounterConfig
        config = TokenCounterConfig(enable_xenova=False, enable_tiktoken=False)
        counter = TieredTokenCounter(config)
        result = counter.count("Any text should work")
        assert result.count >= 0
        assert result.method == "estimation"

    def test_count_returns_result(self):
        from src.utils.tiered_token_counter import TieredTokenCounter, TokenCountResult
        counter = TieredTokenCounter()
        result = counter.count("Test text")
        assert isinstance(result, TokenCountResult)

    def test_count_consistency(self):
        from src.utils.tiered_token_counter import TieredTokenCounter
        counter = TieredTokenCounter()
        text = "The quick brown fox jumps over the lazy dog"
        r1 = counter.count(text)
        r2 = counter.count(text)
        assert r1.count == r2.count


class TestResultCaching:
    def test_cache_stores_result(self):
        from src.utils.tiered_token_counter import TieredTokenCounter
        counter = TieredTokenCounter()
        text = "Cached text example"
        r1 = counter.count(text)
        r2 = counter.count(text)
        assert r2.cached is True

    def test_cache_returns_same_count(self):
        from src.utils.tiered_token_counter import TieredTokenCounter
        counter = TieredTokenCounter()
        text = "Same count expected"
        r1 = counter.count(text)
        r2 = counter.count(text)
        assert r1.count == r2.count

    def test_cache_different_texts(self):
        from src.utils.tiered_token_counter import TieredTokenCounter
        counter = TieredTokenCounter()
        r1 = counter.count("Text one")
        r2 = counter.count("Text two")
        assert r1.cached is False
        assert r2.cached is False

    def test_cache_clear(self):
        from src.utils.tiered_token_counter import TieredTokenCounter
        counter = TieredTokenCounter()
        counter.count("Cache this")
        counter.clear_cache()
        r = counter.count("Cache this")
        assert r.cached is False

class TestBatchCounting:
    def test_batch_returns_list(self):
        from src.utils.tiered_token_counter import TieredTokenCounter
        counter = TieredTokenCounter()
        texts = ["One", "Two", "Three"]
        results = counter.count_batch(texts)
        assert len(results) == 3

    def test_batch_empty_list(self):
        from src.utils.tiered_token_counter import TieredTokenCounter
        counter = TieredTokenCounter()
        results = counter.count_batch([])
        assert results == []

    def test_batch_with_empty_strings(self):
        from src.utils.tiered_token_counter import TieredTokenCounter
        counter = TieredTokenCounter()
        texts = ["", "Hello", ""]
        results = counter.count_batch(texts)
        assert len(results) == 3
        assert results[0].count == 0
        assert results[1].count > 0
        assert results[2].count == 0

class TestEdgeCases:
    def test_very_long_text(self):
        from src.utils.tiered_token_counter import TieredTokenCounter
        counter = TieredTokenCounter()
        text = "word " * 10000
        result = counter.count(text)
        assert result.count > 0

    def test_special_characters(self):
        from src.utils.tiered_token_counter import TieredTokenCounter
        counter = TieredTokenCounter()
        text = "!@#$%^&*()_+-=[]{}|;:,./<>?"
        result = counter.count(text)
        assert result.count >= 0

    def test_newlines_and_tabs(self):
        from src.utils.tiered_token_counter import TieredTokenCounter
        counter = TieredTokenCounter()
        text = "Line1\nLine2\tTabbed"
        result = counter.count(text)
        assert result.count > 0

    def test_code_text(self):
        from src.utils.tiered_token_counter import TieredTokenCounter
        counter = TieredTokenCounter()
        code = "def foo(x):\n    return x * 2"
        result = counter.count(code)
        assert result.count > 0

class TestIntegration:
    def test_ac001_short_text_fast(self):
        from src.utils.tiered_token_counter import TieredTokenCounter
        counter = TieredTokenCounter()
        start = time.time()
        counter.count("Short")
        elapsed = time.time() - start
        assert elapsed < 0.001

    def test_ac004_cache_speedup(self):
        from src.utils.tiered_token_counter import TieredTokenCounter
        counter = TieredTokenCounter()
        text = "Performance test text for caching"
        counter.count(text)
        start = time.time()
        for _ in range(100):
            counter.count(text)
        elapsed = time.time() - start
        assert elapsed < 0.1

    def test_ac005_estimation_for_short_text(self):
        from src.utils.tiered_token_counter import TieredTokenCounter, TokenCounterConfig
        config = TokenCounterConfig(short_text_threshold=1000)
        counter = TieredTokenCounter(config)
        result = counter.count("Under threshold")
        assert result.method == "estimation"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
