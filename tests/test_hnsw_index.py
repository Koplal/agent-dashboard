#!/usr/bin/env python3
"""Tests for P2-002: HNSW Index Support. Version: 2.7.0"""
import pytest
import tempfile
import os
import math

# Check if hnswlib is available
try:
    import hnswlib
    HNSWLIB_AVAILABLE = True
except ImportError:
    HNSWLIB_AVAILABLE = False

class TestHNSWConfig:
    def test_config_default_dim(self):
        from src.knowledge.hnsw_index import HNSWConfig
        assert HNSWConfig(dim=384).dim == 384

    def test_config_default_max_elements(self):
        from src.knowledge.hnsw_index import HNSWConfig
        assert HNSWConfig(dim=384).max_elements == 1_000_000

    def test_config_default_M(self):
        from src.knowledge.hnsw_index import HNSWConfig
        assert HNSWConfig(dim=384).M == 16

    def test_config_custom_values(self):
        from src.knowledge.hnsw_index import HNSWConfig
        c = HNSWConfig(dim=512, max_elements=100000, M=32, ef_construction=400)
        assert c.dim == 512 and c.max_elements == 100000 and c.M == 32 and c.ef_construction == 400

class TestIndexInit:
    def test_init_creates_index(self):
        from src.knowledge.hnsw_index import HNSWIndex, HNSWConfig
        index = HNSWIndex(HNSWConfig(dim=384, max_elements=1000))
        assert index.count == 0

    def test_init_validates_dim(self):
        from src.knowledge.hnsw_index import HNSWConfig
        with pytest.raises(ValueError, match="dim"):
            HNSWConfig(dim=0)

    def test_init_validates_M(self):
        from src.knowledge.hnsw_index import HNSWConfig
        with pytest.raises(ValueError, match="M"):
            HNSWConfig(dim=384, M=1)

    def test_init_validates_ef(self):
        from src.knowledge.hnsw_index import HNSWConfig
        with pytest.raises(ValueError, match="ef"):
            HNSWConfig(dim=384, ef_construction=0)

    def test_init_space_cosine(self):
        from src.knowledge.hnsw_index import HNSWConfig
        assert HNSWConfig(dim=384).space == "cosine"

class TestVectorAddition:
    def test_add_single_vector(self):
        from src.knowledge.hnsw_index import HNSWIndex, HNSWConfig
        index = HNSWIndex(HNSWConfig(dim=4, max_elements=100))
        index.add("id-1", [1.0, 0.0, 0.0, 0.0])
        assert index.count == 1

    def test_add_multiple_vectors(self):
        from src.knowledge.hnsw_index import HNSWIndex, HNSWConfig
        index = HNSWIndex(HNSWConfig(dim=4, max_elements=100))
        for i in range(10):
            vec = [0.0] * 4
            vec[i % 4] = 1.0
            index.add(f"id-{i}", vec)
        assert index.count == 10

    def test_add_normalizes_vector(self):
        from src.knowledge.hnsw_index import HNSWIndex, HNSWConfig
        index = HNSWIndex(HNSWConfig(dim=4, max_elements=100))
        index.add("id-1", [2.0, 0.0, 0.0, 0.0])
        results = index.search([1.0, 0.0, 0.0, 0.0], k=1)
        assert len(results) == 1 and results[0][1] > 0.99

    def test_add_duplicate_updates(self):
        from src.knowledge.hnsw_index import HNSWIndex, HNSWConfig
        index = HNSWIndex(HNSWConfig(dim=4, max_elements=100))
        index.add("id-1", [1.0, 0.0, 0.0, 0.0])
        index.add("id-1", [0.0, 1.0, 0.0, 0.0])
        assert index.count == 1

    def test_add_batch(self):
        from src.knowledge.hnsw_index import HNSWIndex, HNSWConfig
        index = HNSWIndex(HNSWConfig(dim=4, max_elements=100))
        ids = [f"id-{i}" for i in range(4)]
        # Use non-zero vectors that can be normalized
        vecs = [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
        index.add_batch(ids, vecs)
        assert index.count == 4


class TestVectorSearch:
    def test_search_returns_results(self):
        from src.knowledge.hnsw_index import HNSWIndex, HNSWConfig
        index = HNSWIndex(HNSWConfig(dim=4, max_elements=100))
        index.add("id-1", [1.0, 0.0, 0.0, 0.0])
        index.add("id-2", [0.0, 1.0, 0.0, 0.0])
        results = index.search([1.0, 0.0, 0.0, 0.0], k=2)
        assert len(results) == 2

    def test_search_returns_tuples(self):
        from src.knowledge.hnsw_index import HNSWIndex, HNSWConfig
        index = HNSWIndex(HNSWConfig(dim=4, max_elements=100))
        index.add("id-1", [1.0, 0.0, 0.0, 0.0])
        results = index.search([1.0, 0.0, 0.0, 0.0], k=1)
        assert len(results) == 1
        assert isinstance(results[0], tuple)
        assert results[0][0] == "id-1"
        assert 0.0 <= results[0][1] <= 1.0

    def test_search_sorted_by_similarity(self):
        from src.knowledge.hnsw_index import HNSWIndex, HNSWConfig
        index = HNSWIndex(HNSWConfig(dim=4, max_elements=100))
        index.add("close", [0.9, 0.1, 0.0, 0.0])
        index.add("far", [0.0, 0.0, 1.0, 0.0])
        index.add("exact", [1.0, 0.0, 0.0, 0.0])
        results = index.search([1.0, 0.0, 0.0, 0.0], k=3)
        sims = [r[1] for r in results]
        assert sims == sorted(sims, reverse=True)

    def test_search_respects_k(self):
        from src.knowledge.hnsw_index import HNSWIndex, HNSWConfig
        index = HNSWIndex(HNSWConfig(dim=4, max_elements=100))
        for i in range(10):
            vec = [0.0] * 4
            vec[i % 4] = 1.0
            index.add(f"id-{i}", vec)
        results = index.search([1.0, 0.0, 0.0, 0.0], k=3)
        assert len(results) <= 3

    def test_search_empty_index(self):
        from src.knowledge.hnsw_index import HNSWIndex, HNSWConfig
        index = HNSWIndex(HNSWConfig(dim=4, max_elements=100))
        results = index.search([1.0, 0.0, 0.0, 0.0], k=5)
        assert results == []

    def test_search_similarity_range(self):
        from src.knowledge.hnsw_index import HNSWIndex, HNSWConfig
        index = HNSWIndex(HNSWConfig(dim=4, max_elements=100))
        index.add("id-1", [1.0, 0.0, 0.0, 0.0])
        index.add("id-2", [0.0, 1.0, 0.0, 0.0])
        results = index.search([1.0, 0.0, 0.0, 0.0], k=2)
        for _, sim in results:
            assert 0.0 <= sim <= 1.0


class TestPersistence:
    def test_save_and_load(self):
        from src.knowledge.hnsw_index import HNSWIndex, HNSWConfig
        index = HNSWIndex(HNSWConfig(dim=4, max_elements=100))
        index.add("id-1", [1.0, 0.0, 0.0, 0.0])
        index.add("id-2", [0.0, 1.0, 0.0, 0.0])
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.hnsw")
            index.save(path)
            index2 = HNSWIndex.load(path)
            assert index2.count == 2

    def test_load_preserves_search(self):
        from src.knowledge.hnsw_index import HNSWIndex, HNSWConfig
        index = HNSWIndex(HNSWConfig(dim=4, max_elements=100))
        index.add("id-1", [1.0, 0.0, 0.0, 0.0])
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.hnsw")
            index.save(path)
            index2 = HNSWIndex.load(path)
            results = index2.search([1.0, 0.0, 0.0, 0.0], k=1)
            assert len(results) == 1 and results[0][0] == "id-1"

    def test_load_nonexistent_raises(self):
        from src.knowledge.hnsw_index import HNSWIndex
        with pytest.raises(FileNotFoundError):
            HNSWIndex.load("/nonexistent/path/index.hnsw")

    def test_incremental_add_after_load(self):
        from src.knowledge.hnsw_index import HNSWIndex, HNSWConfig
        index = HNSWIndex(HNSWConfig(dim=4, max_elements=100))
        index.add("id-1", [1.0, 0.0, 0.0, 0.0])
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.hnsw")
            index.save(path)
            index2 = HNSWIndex.load(path)
            index2.add("id-2", [0.0, 1.0, 0.0, 0.0])
            assert index2.count == 2

class TestFilteredSearch:
    def test_search_with_filter(self):
        from src.knowledge.hnsw_index import HNSWIndex, HNSWConfig
        index = HNSWIndex(HNSWConfig(dim=4, max_elements=100))
        index.add("a", [1.0, 0.0, 0.0, 0.0])
        index.add("b", [0.9, 0.1, 0.0, 0.0])
        index.add("c", [0.8, 0.2, 0.0, 0.0])
        results = index.search([1.0, 0.0, 0.0, 0.0], k=3, filter_ids={"a", "c"})
        ids = [r[0] for r in results]
        assert "b" not in ids
        assert len(results) <= 2

    def test_search_filter_empty_result(self):
        from src.knowledge.hnsw_index import HNSWIndex, HNSWConfig
        index = HNSWIndex(HNSWConfig(dim=4, max_elements=100))
        index.add("a", [1.0, 0.0, 0.0, 0.0])
        index.add("b", [0.0, 1.0, 0.0, 0.0])
        results = index.search([1.0, 0.0, 0.0, 0.0], k=3, filter_ids={"c"})
        assert results == []


class TestEdgeCases:
    def test_zero_vector_error(self):
        from src.knowledge.hnsw_index import HNSWIndex, HNSWConfig
        index = HNSWIndex(HNSWConfig(dim=4, max_elements=100))
        with pytest.raises(ValueError, match="zero"):
            index.add("id-1", [0.0, 0.0, 0.0, 0.0])

    def test_wrong_dimension_error(self):
        from src.knowledge.hnsw_index import HNSWIndex, HNSWConfig
        index = HNSWIndex(HNSWConfig(dim=4, max_elements=100))
        with pytest.raises(ValueError, match="dimension"):
            index.add("id-1", [1.0, 0.0])

    def test_high_k_returns_all(self):
        from src.knowledge.hnsw_index import HNSWIndex, HNSWConfig
        index = HNSWIndex(HNSWConfig(dim=4, max_elements=100))
        index.add("id-1", [1.0, 0.0, 0.0, 0.0])
        index.add("id-2", [0.0, 1.0, 0.0, 0.0])
        results = index.search([1.0, 0.0, 0.0, 0.0], k=100)
        assert len(results) == 2

class TestErrors:
    @pytest.mark.skipif(not HNSWLIB_AVAILABLE, reason="Capacity limit only enforced with hnswlib")
    def test_capacity_error(self):
        from src.knowledge.hnsw_index import HNSWIndex, HNSWConfig, CapacityError
        index = HNSWIndex(HNSWConfig(dim=4, max_elements=2))
        index.add("id-1", [1.0, 0.0, 0.0, 0.0])
        index.add("id-2", [0.0, 1.0, 0.0, 0.0])
        with pytest.raises(CapacityError):
            index.add("id-3", [0.0, 0.0, 1.0, 0.0])

    def test_capacity_error_fallback(self):
        """Test that fallback mode can exceed capacity (no enforcement)."""
        from src.knowledge.hnsw_index import HNSWIndex, HNSWConfig, HNSWLIB_AVAILABLE
        if HNSWLIB_AVAILABLE:
            pytest.skip("Only test fallback mode without hnswlib")
        index = HNSWIndex(HNSWConfig(dim=4, max_elements=2))
        index.add("id-1", [1.0, 0.0, 0.0, 0.0])
        index.add("id-2", [0.0, 1.0, 0.0, 0.0])
        # Fallback mode does not enforce capacity
        index.add("id-3", [0.0, 0.0, 1.0, 0.0])
        assert index.count == 3

class TestIntegration:
    def test_ac001_build_performance(self):
        import time
        from src.knowledge.hnsw_index import HNSWIndex, HNSWConfig
        import random
        index = HNSWIndex(HNSWConfig(dim=128, max_elements=1000))
        start = time.time()
        for i in range(1000):
            vec = [random.random() for _ in range(128)]
            norm = math.sqrt(sum(x*x for x in vec))
            vec = [x/norm for x in vec]
            index.add(f"id-{i}", vec)
        elapsed = time.time() - start
        assert elapsed < 60.0 and index.count == 1000

    def test_ac002_search_performance(self):
        import time
        from src.knowledge.hnsw_index import HNSWIndex, HNSWConfig
        import random
        index = HNSWIndex(HNSWConfig(dim=128, max_elements=1000))
        for i in range(1000):
            vec = [random.random() for _ in range(128)]
            norm = math.sqrt(sum(x*x for x in vec))
            vec = [x/norm for x in vec]
            index.add(f"id-{i}", vec)
        query = [random.random() for _ in range(128)]
        norm = math.sqrt(sum(x*x for x in query))
        query = [x/norm for x in query]
        start = time.time()
        for _ in range(100):
            index.search(query, k=10)
        elapsed = time.time() - start
        assert elapsed < 1.0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
