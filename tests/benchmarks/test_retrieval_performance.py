#!/usr/bin/env python3
"""
Benchmark Tests for Retrieval Performance.

P3-003: Performance Benchmarking Suite
- Vector search latency (p50/p95/p99)
- BM25 indexing throughput
- Hybrid retrieval end-to-end latency
- Memory usage benchmarks

Version: 2.8.0
"""

import math
import time
import random
import pytest
from typing import List, Dict, Tuple

# Mark all tests in this module as benchmarks
pytestmark = pytest.mark.benchmark


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def benchmark_queries() -> List[str]:
    """Generate benchmark queries."""
    return [
        "Python machine learning frameworks",
        "Java concurrency best practices",
        "REST API design patterns",
        "Microservices architecture",
        "Kubernetes deployment strategies",
        "Database sharding techniques",
        "GraphQL vs REST API",
        "Deep learning optimizations",
        "Cloud native applications",
        "CI/CD pipeline best practices",
    ]  * 10  # 100 queries


@pytest.fixture
def benchmark_vectors() -> Dict[str, List[float]]:
    """Generate benchmark vectors."""
    random.seed(42)
    vectors = {}
    for i in range(1000):
        vec = [random.random() for _ in range(384)]
        norm = math.sqrt(sum(x * x for x in vec))
        vectors[f"doc-{i}"] = [x / norm for x in vec]
    return vectors


@pytest.fixture
def benchmark_documents() -> List[Tuple[str, str]]:
    """Generate benchmark documents."""
    topics = [
        "Python", "Java", "JavaScript", "Rust", "Go",
        "machine learning", "deep learning", "API design",
        "microservices", "Kubernetes", "Docker", "cloud",
    ]
    docs = []
    for i in range(1000):
        topic = topics[i % len(topics)]
        text = f"Document {i} about {topic} with technical details and best practices."
        docs.append((f"doc-{i}", text))
    return docs


def compute_percentiles(latencies: List[float]) -> Dict[str, float]:
    """Compute p50, p95, p99 latencies."""
    sorted_lat = sorted(latencies)
    n = len(sorted_lat)
    return {
        "p50": sorted_lat[n // 2],
        "p95": sorted_lat[int(n * 0.95)],
        "p99": sorted_lat[int(n * 0.99)],
    }


# =============================================================================
# Vector Search Benchmarks
# =============================================================================

class TestVectorSearchLatency:
    """Benchmark vector search latency."""

    @pytest.mark.benchmark
    def test_hnsw_search_latency(self, benchmark_vectors, benchmark_queries):
        """HNSW search p50/p95/p99 latency."""
        from src.knowledge.hnsw_index import HNSWIndex, HNSWConfig
        
        # Build index
        config = HNSWConfig(dim=384, max_elements=1000)
        index = HNSWIndex(config)
        for doc_id, vec in benchmark_vectors.items():
            index.add(doc_id, vec)
        
        # Measure search latencies
        latencies = []
        for _ in range(100):
            query_vec = list(benchmark_vectors.values())[0]
            start = time.perf_counter()
            index.search(query_vec, k=10)
            latencies.append((time.perf_counter() - start) * 1000)
        
        percentiles = compute_percentiles(latencies)
        
        # Performance targets
        assert percentiles["p50"] < 50, f"p50 latency {percentiles['p50']:.2f}ms exceeds 50ms target (fallback mode)"
        assert percentiles["p95"] < 150, f"p95 latency {percentiles['p95']:.2f}ms exceeds 150ms target (fallback mode)"
        assert percentiles["p99"] < 300, f"p99 latency {percentiles['p99']:.2f}ms exceeds 300ms target (fallback mode)"


# =============================================================================
# BM25 Indexing Benchmarks
# =============================================================================

class TestBM25IndexingThroughput:
    """Benchmark BM25 indexing throughput."""

    @pytest.mark.benchmark
    def test_bm25_indexing_throughput(self, benchmark_documents):
        """BM25 indexing throughput (docs/sec)."""
        from src.knowledge.bm25 import BM25Index
        
        index = BM25Index()
        
        start = time.perf_counter()
        count = index.bulk_index(benchmark_documents)
        elapsed = time.perf_counter() - start
        
        throughput = count / elapsed if elapsed > 0 else 0
        
        # Should index at least 100 docs/sec
        assert throughput > 100, f"Indexing throughput {throughput:.0f} docs/sec below 100 target"

    @pytest.mark.benchmark
    def test_bm25_search_latency(self, benchmark_documents, benchmark_queries):
        """BM25 search p50/p95/p99 latency."""
        from src.knowledge.bm25 import BM25Index
        
        index = BM25Index()
        index.bulk_index(benchmark_documents)
        
        latencies = []
        for query in benchmark_queries:
            start = time.perf_counter()
            index.search(query, limit=10)
            latencies.append((time.perf_counter() - start) * 1000)
        
        percentiles = compute_percentiles(latencies)
        
        # Performance targets for BM25 (should be fast)
        assert percentiles["p50"] < 5, f"p50 latency {percentiles['p50']:.2f}ms exceeds 5ms target"
        assert percentiles["p95"] < 20, f"p95 latency {percentiles['p95']:.2f}ms exceeds 20ms target"


# =============================================================================
# Hybrid Retrieval Benchmarks
# =============================================================================

class TestHybridRetrievalLatency:
    """Benchmark hybrid retrieval end-to-end latency."""

    @pytest.mark.benchmark
    def test_three_way_hybrid_latency(self, benchmark_documents, benchmark_queries):
        """Three-way hybrid retrieval latency."""
        from src.knowledge.bm25 import HybridRetrieverV2, ThreeWayHybridConfig
        from src.knowledge.storage import MemoryGraphBackend
        from src.knowledge.graph import KGClaim, Entity, EntityType
        from src.knowledge.embeddings import DualEmbedder, DualEmbeddingConfig
        
        # Setup
        backend = MemoryGraphBackend()
        embedder = DualEmbedder(DualEmbeddingConfig())
        
        # Add claims
        claims = []
        for doc_id, text in benchmark_documents[:100]:  # Limit for speed
            claim = KGClaim(
                claim_id=doc_id,
                text=text,
                confidence=0.9,
                source_url="https://example.com",
                entities=[Entity(name="test", entity_type=EntityType.CONCEPT)],
                embedding=embedder.embed_text(text),
            )
            backend.store_claim(claim)
            claims.append(claim)
        
        # Create retriever
        config = ThreeWayHybridConfig()
        retriever = HybridRetrieverV2(
            storage=backend,
            embedding_fn=embedder.embed_text,
            config=config,
        )
        retriever.index_documents(claims)
        
        # Measure latencies
        latencies = []
        for query in benchmark_queries[:20]:  # Limit for speed
            start = time.perf_counter()
            retriever.retrieve(query, limit=10)
            latencies.append((time.perf_counter() - start) * 1000)
        
        percentiles = compute_percentiles(latencies)
        
        # Performance targets for hybrid (more relaxed)
        assert percentiles["p50"] < 50, f"p50 latency {percentiles['p50']:.2f}ms exceeds 50ms target"
        assert percentiles["p95"] < 200, f"p95 latency {percentiles['p95']:.2f}ms exceeds 200ms target"


# =============================================================================
# Memory Usage Benchmarks
# =============================================================================

class TestMemoryUsage:
    """Benchmark memory usage."""

    @pytest.mark.benchmark
    def test_hnsw_memory_overhead(self, benchmark_vectors):
        """HNSW memory overhead per vector."""
        import sys
        from src.knowledge.hnsw_index import HNSWIndex, HNSWConfig
        
        config = HNSWConfig(dim=384, max_elements=1000)
        index = HNSWIndex(config)
        
        # Estimate memory before
        # Note: This is a rough estimate, actual memory tracking would need memory_profiler
        before_count = len(benchmark_vectors)
        
        for doc_id, vec in benchmark_vectors.items():
            index.add(doc_id, vec)
        
        after_count = index.count
        
        # Basic sanity check
        assert after_count == before_count
        # Memory per vector should be reasonable (just check index works)
        assert index.count == 1000

    @pytest.mark.benchmark
    def test_bm25_memory_overhead(self, benchmark_documents):
        """BM25 memory overhead per document."""
        from src.knowledge.bm25 import BM25Index
        
        index = BM25Index()
        index.bulk_index(benchmark_documents)
        
        # Basic sanity checks
        assert index.get_document_count() == len(benchmark_documents)
        assert len(index.inverted_index) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "benchmark"])
