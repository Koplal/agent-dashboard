#!/usr/bin/env python3
"""Tests for P3-002: Cross-Encoder Re-Ranking. Version: 2.8.0"""

import pytest
from typing import List

try:
    from sentence_transformers import CrossEncoder
    CROSSENCODER_AVAILABLE = True
except ImportError:
    CROSSENCODER_AVAILABLE = False


@pytest.fixture
def sample_query():
    return "Python programming language features"


@pytest.fixture
def sample_candidates():
    return [
        "Java is an object-oriented programming language",
        "Python has dynamic typing and is easy to learn",
        "Cooking recipes for beginners",
        "Python features include list comprehensions and generators",
        "Machine learning with Python",
    ]


class TestReRankerConfig:
    def test_default_config(self):
        from src.knowledge.reranker import ReRankerConfig
        config = ReRankerConfig()
        assert "cross-encoder" in config.model_name
        assert config.batch_size == 32
        assert config.top_k == 10

    def test_custom_config(self):
        from src.knowledge.reranker import ReRankerConfig
        config = ReRankerConfig(batch_size=16, top_k=5, max_length=256)
        assert config.batch_size == 16 and config.top_k == 5

    def test_validation_batch_size(self):
        from src.knowledge.reranker import ReRankerConfig
        with pytest.raises(ValueError, match="batch_size"):
            ReRankerConfig(batch_size=0)

    def test_validation_top_k(self):
        from src.knowledge.reranker import ReRankerConfig
        with pytest.raises(ValueError, match="top_k"):
            ReRankerConfig(top_k=0)


class TestReRankResult:
    def test_result_has_original_index(self):
        from src.knowledge.reranker import ReRankResult
        result = ReRankResult(original_index=2, text="test", score=0.9, new_rank=1)
        assert result.original_index == 2

    def test_result_to_dict(self):
        from src.knowledge.reranker import ReRankResult
        result = ReRankResult(original_index=2, text="test", score=0.9, new_rank=1)
        d = result.to_dict()
        assert d["original_index"] == 2 and d["score"] == 0.9


class TestReRankerInit:
    def test_init_default_config(self):
        from src.knowledge.reranker import ReRanker
        reranker = ReRanker()
        assert reranker.config is not None
        assert reranker.config.top_k == 10

    def test_init_custom_config(self):
        from src.knowledge.reranker import ReRanker, ReRankerConfig
        config = ReRankerConfig(top_k=5)
        reranker = ReRanker(config=config)
        assert reranker.config.top_k == 5


class TestReRanking:
    def test_rerank_returns_results(self, sample_query, sample_candidates):
        from src.knowledge.reranker import ReRanker, ReRankResult
        reranker = ReRanker()
        results = reranker.rerank(sample_query, sample_candidates)
        assert len(results) > 0
        assert all(isinstance(r, ReRankResult) for r in results)

    def test_rerank_respects_top_k(self, sample_query, sample_candidates):
        from src.knowledge.reranker import ReRanker
        reranker = ReRanker()
        results = reranker.rerank(sample_query, sample_candidates, top_k=3)
        assert len(results) <= 3

    def test_rerank_sorted_by_score(self, sample_query, sample_candidates):
        from src.knowledge.reranker import ReRanker
        reranker = ReRanker()
        results = reranker.rerank(sample_query, sample_candidates)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_rerank_assigns_new_ranks(self, sample_query, sample_candidates):
        from src.knowledge.reranker import ReRanker
        reranker = ReRanker()
        results = reranker.rerank(sample_query, sample_candidates)
        ranks = [r.new_rank for r in results]
        assert ranks == list(range(1, len(ranks) + 1))

    def test_rerank_preserves_original_index(self, sample_query, sample_candidates):
        from src.knowledge.reranker import ReRanker
        reranker = ReRanker()
        results = reranker.rerank(sample_query, sample_candidates)
        for r in results:
            assert r.text == sample_candidates[r.original_index]


class TestEdgeCases:
    def test_empty_query(self):
        from src.knowledge.reranker import ReRanker
        reranker = ReRanker()
        results = reranker.rerank("", ["candidate 1", "candidate 2"])
        assert results == []

    def test_empty_candidates(self):
        from src.knowledge.reranker import ReRanker
        reranker = ReRanker()
        results = reranker.rerank("query", [])
        assert results == []

    def test_single_candidate(self):
        from src.knowledge.reranker import ReRanker
        reranker = ReRanker()
        results = reranker.rerank("query", ["single candidate"])
        assert len(results) == 1

    def test_top_k_larger_than_candidates(self):
        from src.knowledge.reranker import ReRanker
        reranker = ReRanker()
        results = reranker.rerank("query", ["a", "b"], top_k=100)
        assert len(results) == 2


class TestFallbackMode:
    def test_fallback_produces_results(self, sample_query, sample_candidates):
        from src.knowledge.reranker import ReRanker
        reranker = ReRanker()
        reranker._use_crossencoder = False
        results = reranker.rerank(sample_query, sample_candidates)
        assert len(results) > 0

    def test_fallback_uses_jaccard(self):
        from src.knowledge.reranker import ReRanker
        reranker = ReRanker()
        reranker._use_crossencoder = False
        results = reranker.rerank(
            "python programming",
            ["python is great for programming", "java coding", "cooking recipes"],
            top_k=3,
        )
        assert results[0].original_index == 0


class TestBatchReRanking:
    def test_rerank_batch_returns_lists(self):
        from src.knowledge.reranker import ReRanker
        reranker = ReRanker()
        reranker._use_crossencoder = False
        queries = ["query 1", "query 2"]
        candidate_lists = [["a", "b"], ["c", "d"]]
        results = reranker.rerank_batch(queries, candidate_lists)
        assert len(results) == 2
        assert all(isinstance(r, list) for r in results)

    def test_rerank_batch_mismatched_lengths(self):
        from src.knowledge.reranker import ReRanker
        reranker = ReRanker()
        with pytest.raises(ValueError):
            reranker.rerank_batch(["q"], [["a"], ["b"]])


class TestPerformance:
    def test_fallback_performance(self):
        import time
        from src.knowledge.reranker import ReRanker
        reranker = ReRanker()
        reranker._use_crossencoder = False
        candidates = [f"candidate {i} with some text content" for i in range(100)]
        start = time.time()
        reranker.rerank("test query", candidates)
        elapsed = time.time() - start
        assert elapsed < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
