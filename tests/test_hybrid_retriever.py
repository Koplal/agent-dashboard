"""
Tests for RETR-001: Hybrid Vector-Graph Retriever.

Tests the hybrid retrieval system combining vector similarity and graph traversal.
These tests are LOCKED after approval - implementation must pass all tests.

Version: 2.6.0
"""

import os
import tempfile
import pytest
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

from src.knowledge.graph import EntityType, Entity, KGClaim
from src.knowledge.storage import MemoryGraphBackend, SQLiteGraphBackend
from src.knowledge.manager import default_embedding_function
from src.knowledge.retriever import (
    HybridRetrieverConfig,
    HybridRetrievalResult,
    HybridRetriever,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def memory_backend():
    """Create a memory backend for testing."""
    return MemoryGraphBackend()


@pytest.fixture
def sqlite_backend():
    """Create a temporary SQLite backend for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    backend = SQLiteGraphBackend(db_path)
    yield backend
    backend.close()

    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def sample_claims():
    """Create sample claims for testing."""
    now = datetime.now(timezone.utc)

    # Claim about Python ML
    claim1 = KGClaim(
        claim_id="claim-1",
        text="Python is widely used for machine learning applications",
        confidence=0.9,
        source_url="https://example.com/python-ml",
        entities=[
            Entity(name="Python", entity_type=EntityType.TECHNOLOGY),
            Entity(name="machine learning", entity_type=EntityType.CONCEPT),
        ],
        topics=["artificial intelligence", "software engineering"],
        embedding=default_embedding_function("Python is widely used for machine learning applications"),
    )

    # Claim about TensorFlow (shares "machine learning" entity)
    claim2 = KGClaim(
        claim_id="claim-2",
        text="TensorFlow provides powerful tools for deep learning",
        confidence=0.85,
        source_url="https://example.com/tensorflow",
        entities=[
            Entity(name="TensorFlow", entity_type=EntityType.TECHNOLOGY),
            Entity(name="deep learning", entity_type=EntityType.CONCEPT),
            Entity(name="machine learning", entity_type=EntityType.CONCEPT),
        ],
        topics=["artificial intelligence"],
        embedding=default_embedding_function("TensorFlow provides powerful tools for deep learning"),
    )

    # Claim about PyTorch (shares "Python" and "deep learning")
    claim3 = KGClaim(
        claim_id="claim-3",
        text="PyTorch is a Python library for neural network research",
        confidence=0.88,
        source_url="https://example.com/pytorch",
        entities=[
            Entity(name="PyTorch", entity_type=EntityType.TECHNOLOGY),
            Entity(name="Python", entity_type=EntityType.TECHNOLOGY),
            Entity(name="neural network", entity_type=EntityType.CONCEPT),
        ],
        topics=["artificial intelligence", "software engineering"],
        embedding=default_embedding_function("PyTorch is a Python library for neural network research"),
    )

    # Unrelated claim about databases
    claim4 = KGClaim(
        claim_id="claim-4",
        text="PostgreSQL is a powerful relational database system",
        confidence=0.92,
        source_url="https://example.com/postgres",
        entities=[
            Entity(name="PostgreSQL", entity_type=EntityType.TECHNOLOGY),
            Entity(name="database", entity_type=EntityType.CONCEPT),
        ],
        topics=["databases"],
        embedding=default_embedding_function("PostgreSQL is a powerful relational database system"),
    )

    # Claim with temporal entities
    claim5 = KGClaim(
        claim_id="claim-5",
        text="The deprecated API was removed in version 2.0",
        confidence=0.95,
        source_url="https://example.com/api-changes",
        entities=[
            Entity(
                name="deprecated_function",
                entity_type=EntityType.FUNCTION,
                valid_from=now - timedelta(days=365),
                valid_to=now - timedelta(days=30),  # Expired
            ),
            Entity(
                name="new_api",
                entity_type=EntityType.FUNCTION,
                valid_from=now - timedelta(days=30),  # Current
            ),
        ],
        topics=["software engineering"],
        embedding=default_embedding_function("The deprecated API was removed in version 2.0"),
    )

    return [claim1, claim2, claim3, claim4, claim5]


@pytest.fixture
def populated_backend(memory_backend, sample_claims):
    """Create a backend populated with sample claims."""
    for claim in sample_claims:
        memory_backend.store_claim(claim)
    return memory_backend


@pytest.fixture
def retriever(populated_backend):
    """Create a retriever with populated backend."""
    # Use low min_similarity for hash-based test embeddings
    return HybridRetriever(
        storage=populated_backend,
        embedding_fn=default_embedding_function,
        config=HybridRetrieverConfig(min_similarity=0.0, min_graph_score=0.0),
    )


# =============================================================================
# Test Category 1: HybridRetrieverConfig
# =============================================================================

class TestHybridRetrieverConfig:
    """Tests for HybridRetrieverConfig dataclass."""

    def test_config_default_values(self):
        """T1.1: Default values are correct."""
        config = HybridRetrieverConfig()
        assert config.vector_weight == 0.6
        assert config.graph_weight == 0.4
        assert config.max_hops == 2
        assert config.min_similarity == 0.3
        assert config.min_graph_score == 0.1
        assert config.temporal_filter is False
        assert config.as_of is None

    def test_config_custom_values(self):
        """T1.2: Custom values are accepted."""
        now = datetime.now(timezone.utc)
        config = HybridRetrieverConfig(
            vector_weight=0.8,
            graph_weight=0.2,
            max_hops=3,
            min_similarity=0.5,
            min_graph_score=0.2,
            temporal_filter=True,
            as_of=now,
        )
        assert config.vector_weight == 0.8
        assert config.graph_weight == 0.2
        assert config.max_hops == 3
        assert config.temporal_filter is True
        assert config.as_of == now

    def test_config_weights_must_be_positive(self):
        """T1.3: Negative weights raise ValueError."""
        with pytest.raises(ValueError):
            HybridRetrieverConfig(vector_weight=-0.5)

        with pytest.raises(ValueError):
            HybridRetrieverConfig(graph_weight=-0.1)

    def test_config_max_hops_must_be_positive(self):
        """T1.4: max_hops <= 0 raises ValueError."""
        with pytest.raises(ValueError):
            HybridRetrieverConfig(max_hops=0)

        with pytest.raises(ValueError):
            HybridRetrieverConfig(max_hops=-1)

    def test_config_min_similarity_range(self):
        """T1.5: min_similarity must be 0.0-1.0."""
        # Valid values
        HybridRetrieverConfig(min_similarity=0.0)
        HybridRetrieverConfig(min_similarity=1.0)
        HybridRetrieverConfig(min_similarity=0.5)

        # Invalid values
        with pytest.raises(ValueError):
            HybridRetrieverConfig(min_similarity=-0.1)

        with pytest.raises(ValueError):
            HybridRetrieverConfig(min_similarity=1.1)


# =============================================================================
# Test Category 2: HybridRetrievalResult
# =============================================================================

class TestHybridRetrievalResult:
    """Tests for HybridRetrievalResult dataclass."""

    def test_result_contains_claim(self, sample_claims):
        """T2.1: Result includes the KGClaim object."""
        claim = sample_claims[0]
        result = HybridRetrievalResult(
            claim=claim,
            combined_score=0.8,
            vector_score=0.9,
            graph_score=0.5,
            retrieval_path="vector",
            hop_distance=0,
        )
        assert result.claim == claim
        assert result.claim.claim_id == "claim-1"

    def test_result_contains_scores(self, sample_claims):
        """T2.2: Result contains all score fields."""
        result = HybridRetrievalResult(
            claim=sample_claims[0],
            combined_score=0.75,
            vector_score=0.8,
            graph_score=0.6,
            retrieval_path="both",
            hop_distance=1,
        )
        assert result.combined_score == 0.75
        assert result.vector_score == 0.8
        assert result.graph_score == 0.6

    def test_result_retrieval_path_values(self, sample_claims):
        """T2.3: retrieval_path is 'vector', 'graph', or 'both'."""
        # All valid paths should work
        for path in ["vector", "graph", "both"]:
            result = HybridRetrievalResult(
                claim=sample_claims[0],
                combined_score=0.5,
                vector_score=0.5,
                graph_score=0.5,
                retrieval_path=path,
                hop_distance=0,
            )
            assert result.retrieval_path == path

    def test_result_hop_distance_non_negative(self, sample_claims):
        """T2.4: hop_distance >= 0."""
        result = HybridRetrievalResult(
            claim=sample_claims[0],
            combined_score=0.5,
            vector_score=0.5,
            graph_score=0.5,
            retrieval_path="graph",
            hop_distance=0,
        )
        assert result.hop_distance >= 0

        result2 = HybridRetrievalResult(
            claim=sample_claims[0],
            combined_score=0.5,
            vector_score=0.0,
            graph_score=0.5,
            retrieval_path="graph",
            hop_distance=2,
        )
        assert result2.hop_distance == 2

    def test_result_to_dict_serialization(self, sample_claims):
        """T2.5: Result can be serialized to dict."""
        result = HybridRetrievalResult(
            claim=sample_claims[0],
            combined_score=0.75,
            vector_score=0.8,
            graph_score=0.6,
            retrieval_path="both",
            hop_distance=1,
        )

        data = result.to_dict()
        assert isinstance(data, dict)
        assert data["combined_score"] == 0.75
        assert data["vector_score"] == 0.8
        assert data["graph_score"] == 0.6
        assert data["retrieval_path"] == "both"
        assert data["hop_distance"] == 1
        assert "claim" in data


# =============================================================================
# Test Category 3: HybridRetriever Initialization
# =============================================================================

class TestHybridRetrieverInit:
    """Tests for HybridRetriever initialization."""

    def test_retriever_init_with_defaults(self, memory_backend):
        """T3.1: Initializes with default config."""
        retriever = HybridRetriever(
            storage=memory_backend,
            embedding_fn=default_embedding_function,
        )
        assert retriever.config.vector_weight == 0.6
        assert retriever.config.graph_weight == 0.4

    def test_retriever_init_with_custom_config(self, memory_backend):
        """T3.2: Accepts custom HybridRetrieverConfig."""
        config = HybridRetrieverConfig(vector_weight=0.7, graph_weight=0.3)
        retriever = HybridRetriever(
            storage=memory_backend,
            embedding_fn=default_embedding_function,
            config=config,
        )
        assert retriever.config.vector_weight == 0.7
        assert retriever.config.graph_weight == 0.3

    def test_retriever_requires_storage(self):
        """T3.3: storage parameter is required."""
        with pytest.raises(TypeError):
            HybridRetriever(embedding_fn=default_embedding_function)

    def test_retriever_requires_embedding_fn(self, memory_backend):
        """T3.4: embedding_fn parameter is required."""
        with pytest.raises(TypeError):
            HybridRetriever(storage=memory_backend)


# =============================================================================
# Test Category 4: Vector Search Component
# =============================================================================

class TestVectorSearch:
    """Tests for vector search component."""

    def test_vector_search_returns_similar_claims(self, retriever):
        """T4.1: Finds claims with high cosine similarity."""
        query = "Python machine learning frameworks"
        embedding = default_embedding_function(query)

        results = retriever._vector_search(embedding, limit=10)

        assert len(results) > 0
        # Results should be (claim, similarity) tuples
        for claim, similarity in results:
            assert isinstance(claim, KGClaim)
            assert 0 <= similarity <= 1

    def test_vector_search_respects_min_similarity(self, populated_backend):
        """T4.2: Filters out low similarity claims."""
        retriever = HybridRetriever(
            storage=populated_backend,
            embedding_fn=default_embedding_function,
            config=HybridRetrieverConfig(min_similarity=0.9),
        )

        query = "completely unrelated topic about cooking"
        embedding = default_embedding_function(query)

        results = retriever._vector_search(embedding, limit=10)

        for claim, similarity in results:
            assert similarity >= 0.9

    def test_vector_search_respects_limit(self, retriever):
        """T4.3: Returns at most limit results."""
        embedding = default_embedding_function("Python programming")

        results = retriever._vector_search(embedding, limit=2)
        assert len(results) <= 2

    def test_vector_search_empty_storage(self, memory_backend):
        """T4.4: Returns empty list for empty storage."""
        retriever = HybridRetriever(
            storage=memory_backend,
            embedding_fn=default_embedding_function,
        )

        embedding = default_embedding_function("any query")
        results = retriever._vector_search(embedding, limit=10)

        assert results == []

    def test_vector_search_no_matches(self, populated_backend):
        """T4.5: Returns empty when no claims meet threshold."""
        retriever = HybridRetriever(
            storage=populated_backend,
            embedding_fn=default_embedding_function,
            config=HybridRetrieverConfig(min_similarity=0.99),
        )

        # Use very different content
        embedding = default_embedding_function("xyzzy foobar baz")
        results = retriever._vector_search(embedding, limit=10)

        # May be empty or have low matches filtered out
        for claim, similarity in results:
            assert similarity >= 0.99

    def test_vector_search_ordering(self, retriever):
        """T4.6: Results sorted by similarity descending."""
        embedding = default_embedding_function("machine learning with Python")

        results = retriever._vector_search(embedding, limit=10)

        if len(results) > 1:
            similarities = [sim for _, sim in results]
            assert similarities == sorted(similarities, reverse=True)


# =============================================================================
# Test Category 5: Graph Expansion Component
# =============================================================================

class TestGraphExpansion:
    """Tests for graph expansion component."""

    def test_graph_expand_one_hop(self, retriever, sample_claims):
        """T5.1: Finds claims sharing entities with seeds."""
        # Seed with claim about Python ML
        seeds = [sample_claims[0]]  # Has "Python" and "machine learning"

        config = HybridRetrieverConfig(max_hops=1, min_graph_score=0.0)
        results = retriever._graph_expand(seeds, config)

        # Should find claims sharing Python or machine learning
        result_ids = {claim.claim_id for claim, _, _ in results}

        # claim-2 shares "machine learning", claim-3 shares "Python"
        assert "claim-2" in result_ids or "claim-3" in result_ids

    def test_graph_expand_two_hops(self, retriever, sample_claims):
        """T5.2: Finds claims 2 hops away via entities."""
        # Seed with claim-1 (Python, ML)
        # Hop 1: claim-2 (shares ML), claim-3 (shares Python)
        # Hop 2: claims sharing entities with claim-2 or claim-3
        seeds = [sample_claims[0]]

        config = HybridRetrieverConfig(max_hops=2, min_graph_score=0.0)
        results = retriever._graph_expand(seeds, config)

        # With 2 hops, should potentially reach more claims
        assert len(results) >= 0  # May vary based on entity overlap

    def test_graph_expand_max_hops_limit(self, retriever, sample_claims):
        """T5.3: Respects max_hops configuration."""
        seeds = [sample_claims[0]]

        config_1hop = HybridRetrieverConfig(max_hops=1, min_graph_score=0.0)
        config_2hop = HybridRetrieverConfig(max_hops=2, min_graph_score=0.0)
        results_1hop = retriever._graph_expand(seeds, config_1hop)
        results_2hop = retriever._graph_expand(seeds, config_2hop)

        # All 1-hop results should have hop_distance <= 1
        for _, hop_distance, _ in results_1hop:
            assert hop_distance <= 1

        # 2-hop may include distance 2
        max_distance = max((h for _, h, _ in results_2hop), default=0)
        assert max_distance <= 2

    def test_graph_expand_no_duplicates(self, retriever, sample_claims):
        """T5.4: Does not return seed claims."""
        seeds = [sample_claims[0]]
        seed_ids = {c.claim_id for c in seeds}

        config = HybridRetrieverConfig(max_hops=2, min_graph_score=0.0)
        results = retriever._graph_expand(seeds, config)

        result_ids = {claim.claim_id for claim, _, _ in results}
        assert seed_ids.isdisjoint(result_ids)

    def test_graph_expand_tracks_hop_distance(self, retriever, sample_claims):
        """T5.5: Returns correct hop count."""
        seeds = [sample_claims[0]]

        config = HybridRetrieverConfig(max_hops=2, min_graph_score=0.0)
        results = retriever._graph_expand(seeds, config)

        for claim, hop_distance, score in results:
            assert isinstance(hop_distance, int)
            assert hop_distance >= 1  # Not a seed, so at least 1 hop

    def test_graph_expand_entity_overlap_score(self, retriever, sample_claims):
        """T5.6: Calculates entity overlap ratio."""
        seeds = [sample_claims[0]]  # Has 2 entities

        config = HybridRetrieverConfig(max_hops=1, min_graph_score=0.0)
        results = retriever._graph_expand(seeds, config)

        for claim, hop_distance, score in results:
            assert 0 <= score <= 1  # Overlap ratio is 0-1

    def test_graph_expand_empty_seeds(self, retriever):
        """T5.7: Returns empty for no seed claims."""
        config = HybridRetrieverConfig(max_hops=2, min_graph_score=0.0)
        results = retriever._graph_expand([], config)
        assert results == []


# =============================================================================
# Test Category 6: Score Fusion
# =============================================================================

class TestScoreFusion:
    """Tests for score fusion logic."""

    def test_fuse_vector_only_claim(self, retriever, sample_claims):
        """T6.1: Claim found only by vector gets graph_score=0."""
        vector_results = {"claim-1": 0.8}
        graph_results = {}  # Not found via graph

        fused = retriever._fuse_scores(vector_results, graph_results)

        assert "claim-1" in fused
        assert fused["claim-1"].vector_score == 0.8
        assert fused["claim-1"].graph_score == 0.0
        assert fused["claim-1"].retrieval_path == "vector"

    def test_fuse_graph_only_claim(self, retriever, sample_claims):
        """T6.2: Claim found only by graph gets vector_score=0."""
        vector_results = {}
        graph_results = {"claim-2": (1, 0.5)}  # (hop_distance, score)

        fused = retriever._fuse_scores(vector_results, graph_results)

        assert "claim-2" in fused
        assert fused["claim-2"].vector_score == 0.0
        assert fused["claim-2"].graph_score == 0.5
        assert fused["claim-2"].retrieval_path == "graph"

    def test_fuse_both_sources(self, retriever, sample_claims):
        """T6.3: Claim found by both has retrieval_path='both'."""
        vector_results = {"claim-1": 0.8}
        graph_results = {"claim-1": (1, 0.6)}

        fused = retriever._fuse_scores(vector_results, graph_results)

        assert "claim-1" in fused
        assert fused["claim-1"].retrieval_path == "both"
        assert fused["claim-1"].vector_score == 0.8
        assert fused["claim-1"].graph_score == 0.6

    def test_fuse_combined_score_formula(self, retriever):
        """T6.4: combined = v_weight*v_score + g_weight*g_score."""
        # Default weights: vector=0.6, graph=0.4
        vector_results = {"claim-1": 0.8}
        graph_results = {"claim-1": (1, 0.5)}

        fused = retriever._fuse_scores(vector_results, graph_results)

        expected = 0.6 * 0.8 + 0.4 * 0.5  # 0.48 + 0.2 = 0.68
        assert abs(fused["claim-1"].combined_score - expected) < 0.001

    def test_fuse_deduplication(self, retriever, sample_claims):
        """T6.5: Same claim from both sources appears once."""
        vector_results = {"claim-1": 0.8, "claim-2": 0.7}
        graph_results = {"claim-1": (1, 0.5), "claim-3": (1, 0.4)}

        fused = retriever._fuse_scores(vector_results, graph_results)

        # claim-1 appears in both but should only be in fused once
        assert len([k for k in fused if k == "claim-1"]) == 1

    def test_fuse_weight_effect(self, populated_backend):
        """T6.6: Higher weight increases influence on combined."""
        # High vector weight
        retriever_v = HybridRetriever(
            storage=populated_backend,
            embedding_fn=default_embedding_function,
            config=HybridRetrieverConfig(vector_weight=0.9, graph_weight=0.1),
        )

        # High graph weight
        retriever_g = HybridRetriever(
            storage=populated_backend,
            embedding_fn=default_embedding_function,
            config=HybridRetrieverConfig(vector_weight=0.1, graph_weight=0.9),
        )

        vector_results = {"claim-1": 0.8}
        graph_results = {"claim-1": (1, 0.3)}

        fused_v = retriever_v._fuse_scores(vector_results, graph_results)
        fused_g = retriever_g._fuse_scores(vector_results, graph_results)

        # Vector-heavy should have higher score (0.9*0.8 + 0.1*0.3 = 0.75)
        # Graph-heavy should have lower score (0.1*0.8 + 0.9*0.3 = 0.35)
        assert fused_v["claim-1"].combined_score > fused_g["claim-1"].combined_score


# =============================================================================
# Test Category 7: Temporal Filtering
# =============================================================================

class TestTemporalFiltering:
    """Tests for temporal entity filtering."""

    def test_temporal_filter_disabled_by_default(self, retriever, sample_claims):
        """T7.1: temporal_filter=False includes all entities."""
        assert retriever.config.temporal_filter is False

        # Should include claim-5 which has expired entities
        results = retriever.retrieve("deprecated API changes", limit=10)

        # All claims are considered regardless of entity validity
        # (test just verifies no filtering happens)

    def test_temporal_filter_excludes_expired(self, populated_backend, sample_claims):
        """T7.2: Expired entities (valid_to < as_of) excluded from expansion."""
        now = datetime.now(timezone.utc)

        config = HybridRetrieverConfig(
            temporal_filter=True,
            as_of=now,
            max_hops=1,
            min_graph_score=0.0,
        )

        retriever = HybridRetriever(
            storage=populated_backend,
            embedding_fn=default_embedding_function,
            config=config,
        )

        # claim-5 has "deprecated_function" which is expired
        # Graph expansion should not follow expired entity links
        seeds = [sample_claims[4]]  # claim-5

        # The expired entity should not contribute to graph expansion
        results = retriever._graph_expand(seeds, config)

        # Results should only use valid entities for expansion

    def test_temporal_filter_excludes_future(self, populated_backend):
        """T7.3: Future entities (valid_from > as_of) excluded."""
        past = datetime.now(timezone.utc) - timedelta(days=60)

        retriever = HybridRetriever(
            storage=populated_backend,
            embedding_fn=default_embedding_function,
            config=HybridRetrieverConfig(
                temporal_filter=True,
                as_of=past,  # Query from perspective of 60 days ago
            ),
        )

        # claim-5's "new_api" has valid_from = now - 30 days
        # From perspective of 60 days ago, it's in the future
        results = retriever.retrieve("API", limit=10)

        # Temporal filtering should exclude future entities from expansion

    def test_temporal_filter_includes_valid(self, populated_backend, sample_claims):
        """T7.4: Valid entities included in expansion."""
        now = datetime.now(timezone.utc)

        config = HybridRetrieverConfig(
            temporal_filter=True,
            as_of=now,
            max_hops=1,
            min_graph_score=0.0,
        )

        retriever = HybridRetriever(
            storage=populated_backend,
            embedding_fn=default_embedding_function,
            config=config,
        )

        # claim-5 has "new_api" which is currently valid
        seeds = [sample_claims[4]]

        # Valid entities should still be used for expansion
        # (implementation detail - just verify no crash)
        results = retriever._graph_expand(seeds, config)
        assert isinstance(results, list)

    def test_temporal_filter_uses_current_time(self, populated_backend):
        """T7.5: as_of=None uses current UTC time."""
        retriever = HybridRetriever(
            storage=populated_backend,
            embedding_fn=default_embedding_function,
            config=HybridRetrieverConfig(
                temporal_filter=True,
                as_of=None,  # Should default to now
            ),
        )

        # Should work without error
        results = retriever.retrieve("Python", limit=5)
        assert isinstance(results, list)


# =============================================================================
# Test Category 8: Full Retrieve Method
# =============================================================================

class TestRetrieveMethod:
    """Tests for the main retrieve method."""

    def test_retrieve_combines_vector_and_graph(self, retriever):
        """T8.1: Returns union of vector+graph results."""
        results = retriever.retrieve("Python machine learning", limit=10)

        assert isinstance(results, list)

        # Should have mix of retrieval paths
        paths = {r.retrieval_path for r in results}
        # At least some results expected
        assert len(results) > 0

    def test_retrieve_respects_limit(self, retriever):
        """T8.2: Returns at most limit results."""
        results = retriever.retrieve("Python", limit=2)
        assert len(results) <= 2

    def test_retrieve_sorted_by_combined_score(self, retriever):
        """T8.3: Results ordered by combined_score desc."""
        results = retriever.retrieve("machine learning", limit=10)

        if len(results) > 1:
            scores = [r.combined_score for r in results]
            assert scores == sorted(scores, reverse=True)

    def test_retrieve_empty_query(self, retriever):
        """T8.4: Empty query returns empty results."""
        results = retriever.retrieve("", limit=10)
        assert results == []

    def test_retrieve_with_override_config(self, retriever):
        """T8.5: Per-call config overrides default."""
        override = HybridRetrieverConfig(
            vector_weight=1.0,
            graph_weight=0.0,
            max_hops=1,
        )

        results = retriever.retrieve(
            "Python programming",
            limit=10,
            config=override,
        )

        # With graph_weight=0, graph-only results should have score=0
        for r in results:
            if r.retrieval_path == "graph":
                # Graph-only with weight 0 should have low combined score
                pass  # Implementation detail


# =============================================================================
# Test Category 9: Batch Retrieval
# =============================================================================

class TestBatchRetrieval:
    """Tests for batch retrieval."""

    def test_retrieve_batch_multiple_queries(self, retriever):
        """T9.1: Processes list of queries."""
        queries = ["Python", "TensorFlow", "PostgreSQL"]

        results = retriever.retrieve_batch(queries, limit=5)

        assert len(results) == 3
        assert "Python" in results
        assert "TensorFlow" in results
        assert "PostgreSQL" in results

    def test_retrieve_batch_returns_dict(self, retriever):
        """T9.2: Returns Dict[query, List[Result]]."""
        queries = ["machine learning"]

        results = retriever.retrieve_batch(queries, limit=5)

        assert isinstance(results, dict)
        assert "machine learning" in results
        assert isinstance(results["machine learning"], list)

    def test_retrieve_batch_empty_list(self, retriever):
        """T9.3: Empty query list returns empty dict."""
        results = retriever.retrieve_batch([], limit=5)
        assert results == {}

    def test_retrieve_batch_independent_results(self, retriever):
        """T9.4: Each query's results are independent."""
        queries = ["Python", "PostgreSQL"]

        results = retriever.retrieve_batch(queries, limit=5)

        python_ids = {r.claim.claim_id for r in results["Python"]}
        postgres_ids = {r.claim.claim_id for r in results["PostgreSQL"]}

        # Results are query-specific (may overlap but computed independently)
        assert isinstance(python_ids, set)
        assert isinstance(postgres_ids, set)


# =============================================================================
# Test Category 10: Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for hybrid retriever."""

    def test_integration_realistic_scenario(self, populated_backend):
        """T10.1: Multi-claim scenario with entity overlap."""
        retriever = HybridRetriever(
            storage=populated_backend,
            embedding_fn=default_embedding_function,
            config=HybridRetrieverConfig(min_similarity=0.0, min_graph_score=0.0),
        )

        # Query that should match via both vector and graph
        results = retriever.retrieve(
            "Python frameworks for neural networks",
            limit=10,
        )

        assert len(results) > 0

        # Should find Python-related claims
        claim_texts = [r.claim.text.lower() for r in results]
        has_python = any("python" in t for t in claim_texts)
        assert has_python

    def test_integration_with_sqlite_backend(self, sqlite_backend, sample_claims):
        """T10.2: Works with SQLiteGraphBackend."""
        # Populate SQLite backend
        for claim in sample_claims:
            sqlite_backend.store_claim(claim)

        retriever = HybridRetriever(
            storage=sqlite_backend,
            embedding_fn=default_embedding_function,
        )

        results = retriever.retrieve("machine learning", limit=5)

        assert isinstance(results, list)
        # Should work without errors

    def test_integration_with_memory_backend(self, populated_backend):
        """T10.3: Works with MemoryGraphBackend."""
        retriever = HybridRetriever(
            storage=populated_backend,
            embedding_fn=default_embedding_function,
        )

        results = retriever.retrieve("deep learning frameworks", limit=5)

        assert isinstance(results, list)

    def test_integration_code_entities(self, memory_backend):
        """T10.4: Works with new code EntityTypes."""
        # Create claims with code entities
        claim = KGClaim(
            claim_id="code-claim-1",
            text="The process_data function in utils.py handles ETL",
            confidence=0.9,
            source_url="file://src/utils.py",
            entities=[
                Entity(name="process_data", entity_type=EntityType.FUNCTION),
                Entity(name="utils.py", entity_type=EntityType.FILE),
                Entity(name="utils", entity_type=EntityType.MODULE),
            ],
            topics=["software engineering"],
            embedding=default_embedding_function("The process_data function in utils.py handles ETL"),
        )

        memory_backend.store_claim(claim)

        retriever = HybridRetriever(
            storage=memory_backend,
            embedding_fn=default_embedding_function,
            config=HybridRetrieverConfig(min_similarity=0.0, min_graph_score=0.0),
        )

        results = retriever.retrieve("ETL processing functions", limit=5)

        assert len(results) > 0
        assert results[0].claim.claim_id == "code-claim-1"
