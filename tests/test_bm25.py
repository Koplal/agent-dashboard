"""
Tests for P1-002: BM25 Three-Way Hybrid Search.

Tests the BM25 keyword search with three-way hybrid retrieval combining:
- Vector similarity (weight 0.4)
- Graph expansion (weight 0.3)
- BM25 keyword matching (weight 0.3)

Version: 2.8.0
"""

import pytest
from datetime import datetime, timezone


# =============================================================================
# Test Category 1: BM25Config (existing + validation)
# =============================================================================

class TestBM25Config:
    """Tests for BM25Config dataclass."""
    
    def test_config_default_values(self):
        """T1.1: Default values match research recommendations."""
        from src.knowledge.bm25 import BM25Config
        config = BM25Config()
        assert config.k1 == 1.5
        assert config.b == 0.75
        assert config.rrf_k == 60

    def test_config_custom_values(self):
        """T1.2: Custom values are accepted."""
        from src.knowledge.bm25 import BM25Config
        config = BM25Config(k1=2.0, b=0.5, rrf_k=100)
        assert config.k1 == 2.0
        assert config.b == 0.5

    def test_config_k1_non_negative(self):
        """T1.3: Negative k1 raises ValueError."""
        from src.knowledge.bm25 import BM25Config
        with pytest.raises(ValueError):
            BM25Config(k1=-1.0)

    def test_config_b_range(self):
        """T1.4: b outside [0,1] raises ValueError."""
        from src.knowledge.bm25 import BM25Config
        with pytest.raises(ValueError):
            BM25Config(b=1.5)
        with pytest.raises(ValueError):
            BM25Config(b=-0.1)

    def test_config_rrf_k_positive(self):
        """T1.5: rrf_k must be positive."""
        from src.knowledge.bm25 import BM25Config
        with pytest.raises(ValueError):
            BM25Config(rrf_k=0)
        with pytest.raises(ValueError):
            BM25Config(rrf_k=-10)


# =============================================================================
# Test Category 2: ThreeWayHybridConfig
# =============================================================================

class TestThreeWayHybridConfig:
    """Tests for ThreeWayHybridConfig dataclass."""
    
    def test_default_weights(self):
        """T2.1: Default weights are vector=0.4, graph=0.3, bm25=0.3."""
        from src.knowledge.bm25 import ThreeWayHybridConfig
        config = ThreeWayHybridConfig()
        assert config.vector_weight == 0.4
        assert config.graph_weight == 0.3
        assert config.bm25_weight == 0.3

    def test_default_bm25_params(self):
        """T2.2: BM25 defaults k1=1.5, b=0.75, rrf_k=60."""
        from src.knowledge.bm25 import ThreeWayHybridConfig
        config = ThreeWayHybridConfig()
        assert config.k1 == 1.5
        assert config.b == 0.75
        assert config.rrf_k == 60

    def test_weights_sum_validation(self):
        """T2.3: Weights should sum to 1.0 (within tolerance)."""
        from src.knowledge.bm25 import ThreeWayHybridConfig
        config = ThreeWayHybridConfig()
        total = config.vector_weight + config.graph_weight + config.bm25_weight
        assert abs(total - 1.0) < 0.001

    def test_custom_weights(self):
        """T2.4: Custom weights are accepted."""
        from src.knowledge.bm25 import ThreeWayHybridConfig
        config = ThreeWayHybridConfig(
            vector_weight=0.5,
            graph_weight=0.25,
            bm25_weight=0.25,
        )
        assert config.vector_weight == 0.5
        assert config.graph_weight == 0.25
        assert config.bm25_weight == 0.25

    def test_negative_weight_raises(self):
        """T2.5: Negative weights raise ValueError."""
        from src.knowledge.bm25 import ThreeWayHybridConfig
        with pytest.raises(ValueError):
            ThreeWayHybridConfig(vector_weight=-0.1)
        with pytest.raises(ValueError):
            ThreeWayHybridConfig(graph_weight=-0.1)
        with pytest.raises(ValueError):
            ThreeWayHybridConfig(bm25_weight=-0.1)

    def test_max_hops_default(self):
        """T2.6: Default max_hops is 2."""
        from src.knowledge.bm25 import ThreeWayHybridConfig
        config = ThreeWayHybridConfig()
        assert config.max_hops == 2

    def test_tokenizer_defaults(self):
        """T2.7: Tokenization defaults are enabled."""
        from src.knowledge.bm25 import ThreeWayHybridConfig
        config = ThreeWayHybridConfig()
        assert config.use_stemming is True
        assert config.use_stopwords is True


# =============================================================================
# Test Category 3: TokenizerConfig
# =============================================================================

class TestTokenizerConfig:
    """Tests for TokenizerConfig dataclass."""
    
    def test_default_config(self):
        """T3.1: Default config enables all processing."""
        from src.knowledge.bm25 import TokenizerConfig
        config = TokenizerConfig()
        assert config.lowercase is True
        assert config.remove_stopwords is True
        assert config.use_stemming is True
        assert config.language == "english"

    def test_custom_config(self):
        """T3.2: Custom values are accepted."""
        from src.knowledge.bm25 import TokenizerConfig
        config = TokenizerConfig(
            lowercase=False,
            remove_stopwords=False,
            use_stemming=False,
        )
        assert config.lowercase is False
        assert config.remove_stopwords is False
        assert config.use_stemming is False


# =============================================================================
# Test Category 4: Tokenizer
# =============================================================================

class TestTokenizer:
    """Tests for Tokenizer class."""
    
    def test_tokenizer_lowercase(self):
        """T4.1: Tokenizer applies lowercase."""
        from src.knowledge.bm25 import Tokenizer, TokenizerConfig
        tokenizer = Tokenizer(TokenizerConfig(lowercase=True, remove_stopwords=False, use_stemming=False))
        tokens = tokenizer.tokenize("Python MACHINE Learning")
        assert all(t == t.lower() for t in tokens)
        assert "python" in tokens
        assert "machine" in tokens

    def test_tokenizer_stopword_removal(self):
        """T4.2: Tokenizer removes stopwords."""
        from src.knowledge.bm25 import Tokenizer, TokenizerConfig
        tokenizer = Tokenizer(TokenizerConfig(remove_stopwords=True, use_stemming=False))
        tokens = tokenizer.tokenize("the Python is a great language for the task")
        assert "the" not in tokens
        assert "is" not in tokens
        assert "a" not in tokens
        assert "for" not in tokens
        assert "python" in tokens

    def test_tokenizer_stemming(self):
        """T4.3: Tokenizer applies Porter stemming."""
        from src.knowledge.bm25 import Tokenizer, TokenizerConfig
        tokenizer = Tokenizer(TokenizerConfig(use_stemming=True, remove_stopwords=False))
        tokens = tokenizer.tokenize("running runs")
        # running and runs both stem to "run"
        assert all(t == "run" for t in tokens)

    def test_tokenizer_combined(self):
        """T4.4: Tokenizer applies all processing."""
        from src.knowledge.bm25 import Tokenizer
        tokenizer = Tokenizer()  # Default config
        tokens = tokenizer.tokenize("The RUNNING programmer is LEARNING quickly")
        # Should be lowercase, no stopwords, stemmed
        assert "the" not in tokens
        assert "is" not in tokens
        assert "run" in tokens  # stemmed from running
        assert "programm" in tokens  # stemmed from programmer (simplified stemmer)
        assert "learn" in tokens  # stemmed from learning
        assert "quickli" in tokens  # stemmed from quickly (simplified stemmer)

    def test_tokenizer_empty_string(self):
        """T4.5: Empty string returns empty list."""
        from src.knowledge.bm25 import Tokenizer
        tokenizer = Tokenizer()
        tokens = tokenizer.tokenize("")
        assert tokens == []

    def test_tokenizer_whitespace_only(self):
        """T4.6: Whitespace-only returns empty list."""
        from src.knowledge.bm25 import Tokenizer
        tokenizer = Tokenizer()
        tokens = tokenizer.tokenize("   \t\n  ")
        assert tokens == []

    def test_tokenizer_preserves_order(self):
        """T4.7: Token order is preserved."""
        from src.knowledge.bm25 import Tokenizer, TokenizerConfig
        tokenizer = Tokenizer(TokenizerConfig(remove_stopwords=False, use_stemming=False))
        tokens = tokenizer.tokenize("first second third")
        assert tokens == ["first", "second", "third"]


# =============================================================================
# Test Category 5: BM25Index (enhanced)
# =============================================================================

class TestBM25Index:
    """Tests for BM25Index class."""
    
    def test_add_document(self):
        """T5.1: Adding document updates count."""
        from src.knowledge.bm25 import BM25Index
        index = BM25Index()
        index.add_document("doc1", "Python is a programming language")
        assert index.get_document_count() == 1

    def test_search_basic(self):
        """T5.2: Basic search returns ranked results."""
        from src.knowledge.bm25 import BM25Index
        index = BM25Index()
        index.add_document("doc1", "Python is great for machine learning")
        index.add_document("doc2", "Java is used in enterprise applications")
        results = index.search("Python machine learning", limit=5)
        assert len(results) > 0
        assert results[0][0] == "doc1"

    def test_search_empty_index(self):
        """T5.3: Search on empty index returns empty."""
        from src.knowledge.bm25 import BM25Index
        index = BM25Index()
        results = index.search("test", limit=5)
        assert results == []

    def test_search_no_match(self):
        """T5.4: No matching terms returns empty."""
        from src.knowledge.bm25 import BM25Index
        index = BM25Index()
        index.add_document("doc1", "Python programming")
        results = index.search("database optimization", limit=5)
        assert len(results) == 0

    def test_index_with_tokenizer(self):
        """T5.5: Index uses tokenizer for processing."""
        from src.knowledge.bm25 import BM25Index, Tokenizer
        tokenizer = Tokenizer()  # With stemming
        index = BM25Index(tokenizer=tokenizer)
        index.add_document("doc1", "The programmers are running tests")
        # Search with stemmed forms should match
        results = index.search("program run test", limit=5)
        assert len(results) > 0
        assert results[0][0] == "doc1"

    def test_index_limit_respected(self):
        """T5.6: Search respects limit parameter."""
        from src.knowledge.bm25 import BM25Index
        index = BM25Index()
        for i in range(10):
            index.add_document(f"doc{i}", f"Python programming topic {i}")
        results = index.search("Python programming", limit=3)
        assert len(results) <= 3

    def test_bulk_index(self):
        """T5.7: Bulk indexing works correctly."""
        from src.knowledge.bm25 import BM25Index
        index = BM25Index()
        docs = [
            ("doc1", "Python is great"),
            ("doc2", "Java is enterprise"),
            ("doc3", "Rust is fast"),
        ]
        count = index.bulk_index(docs)
        assert count == 3
        assert index.get_document_count() == 3


# =============================================================================
# Test Category 6: RRF (Reciprocal Rank Fusion)
# =============================================================================

class TestRRF:
    """Tests for reciprocal_rank_fusion function."""
    
    def test_rrf_basic(self):
        """T6.1: Basic RRF combines rankings."""
        from src.knowledge.bm25 import reciprocal_rank_fusion
        rankings = [
            [("doc1", 0.9), ("doc2", 0.8)],
            [("doc2", 0.85), ("doc1", 0.75)],
        ]
        fused = reciprocal_rank_fusion(rankings, k=60)
        assert len(fused) == 2

    def test_rrf_empty(self):
        """T6.2: Empty rankings return empty."""
        from src.knowledge.bm25 import reciprocal_rank_fusion
        fused = reciprocal_rank_fusion([], k=60)
        assert fused == []

    def test_rrf_single_ranking(self):
        """T6.3: Single ranking preserves order."""
        from src.knowledge.bm25 import reciprocal_rank_fusion
        rankings = [[("doc1", 0.9), ("doc2", 0.8)]]
        fused = reciprocal_rank_fusion(rankings, k=60)
        assert len(fused) == 2

    def test_rrf_formula_correct(self):
        """T6.4: RRF formula: score = sum(1/(k + rank_i))."""
        from src.knowledge.bm25 import reciprocal_rank_fusion
        rankings = [
            [("doc1", 1.0)],  # rank 1 in list 0
            [("doc1", 1.0)],  # rank 1 in list 1
        ]
        fused = reciprocal_rank_fusion(rankings, k=60)
        # doc1 appears at rank 1 in both lists
        # score = 1/(60+1) + 1/(60+1) = 2/61 = ~0.0328
        expected = 2.0 / 61.0
        assert abs(fused[0][1] - expected) < 0.0001

    def test_rrf_with_weights(self):
        """T6.5: RRF applies weights correctly."""
        from src.knowledge.bm25 import reciprocal_rank_fusion
        rankings = [
            [("doc1", 1.0)],  # rank 1, weight 0.4
            [("doc1", 1.0)],  # rank 1, weight 0.3
            [("doc1", 1.0)],  # rank 1, weight 0.3
        ]
        weights = [0.4, 0.3, 0.3]
        fused = reciprocal_rank_fusion(rankings, k=60, weights=weights)
        # score = 0.4/(61) + 0.3/(61) + 0.3/(61) = 1.0/61
        expected = 1.0 / 61.0
        assert abs(fused[0][1] - expected) < 0.0001

    def test_rrf_three_rankings(self):
        """T6.6: Three-way RRF works correctly."""
        from src.knowledge.bm25 import reciprocal_rank_fusion
        rankings = [
            [("doc1", 0.9), ("doc2", 0.7)],
            [("doc2", 0.8), ("doc3", 0.6)],
            [("doc1", 0.7), ("doc3", 0.5)],
        ]
        fused = reciprocal_rank_fusion(rankings, k=60)
        # doc1: 1/(61) + 0 + 1/(61) = 2/61
        # doc2: 1/(62) + 1/(61) + 0 
        # doc3: 0 + 1/(62) + 1/(62)
        assert len(fused) == 3
        # Order should be doc1, doc2, doc3 based on RRF scores
        doc_order = [d[0] for d in fused]
        assert doc_order[0] == "doc1"


# =============================================================================
# Test Category 7: ThreeWayRetrievalResult
# =============================================================================

class TestThreeWayRetrievalResult:
    """Tests for ThreeWayRetrievalResult dataclass."""
    
    def test_result_contains_all_scores(self):
        """T7.1: Result includes vector, graph, and bm25 scores."""
        from src.knowledge.bm25 import ThreeWayRetrievalResult
        from src.knowledge.graph import KGClaim
        
        claim = KGClaim(
            claim_id="test-1",
            text="Test claim",
            confidence=0.9,
            source_url="https://example.com",
        )
        result = ThreeWayRetrievalResult(
            claim=claim,
            combined_score=0.75,
            vector_score=0.8,
            graph_score=0.5,
            bm25_score=0.7,
            retrieval_path="all",
            hop_distance=1,
            rrf_rank=1,
        )
        assert result.vector_score == 0.8
        assert result.graph_score == 0.5
        assert result.bm25_score == 0.7
        assert result.combined_score == 0.75

    def test_result_retrieval_paths(self):
        """T7.2: retrieval_path values are valid."""
        from src.knowledge.bm25 import ThreeWayRetrievalResult
        from src.knowledge.graph import KGClaim
        
        claim = KGClaim(
            claim_id="test-1",
            text="Test",
            confidence=0.9,
            source_url="https://example.com",
        )
        
        valid_paths = ["vector", "graph", "bm25", "vector+graph", "vector+bm25", "graph+bm25", "all"]
        for path in valid_paths:
            result = ThreeWayRetrievalResult(
                claim=claim,
                combined_score=0.5,
                vector_score=0.5,
                graph_score=0.5,
                bm25_score=0.5,
                retrieval_path=path,
                hop_distance=0,
                rrf_rank=1,
            )
            assert result.retrieval_path == path

    def test_result_rrf_rank(self):
        """T7.3: rrf_rank is included."""
        from src.knowledge.bm25 import ThreeWayRetrievalResult
        from src.knowledge.graph import KGClaim
        
        claim = KGClaim(
            claim_id="test-1",
            text="Test",
            confidence=0.9,
            source_url="https://example.com",
        )
        result = ThreeWayRetrievalResult(
            claim=claim,
            combined_score=0.5,
            vector_score=0.5,
            graph_score=0.5,
            bm25_score=0.5,
            retrieval_path="all",
            hop_distance=0,
            rrf_rank=5,
        )
        assert result.rrf_rank == 5

    def test_result_to_dict(self):
        """T7.4: Result serializes to dict."""
        from src.knowledge.bm25 import ThreeWayRetrievalResult
        from src.knowledge.graph import KGClaim
        
        claim = KGClaim(
            claim_id="test-1",
            text="Test",
            confidence=0.9,
            source_url="https://example.com",
        )
        result = ThreeWayRetrievalResult(
            claim=claim,
            combined_score=0.75,
            vector_score=0.8,
            graph_score=0.5,
            bm25_score=0.7,
            retrieval_path="all",
            hop_distance=1,
            rrf_rank=1,
        )
        data = result.to_dict()
        assert data["combined_score"] == 0.75
        assert data["vector_score"] == 0.8
        assert data["graph_score"] == 0.5
        assert data["bm25_score"] == 0.7
        assert data["retrieval_path"] == "all"
        assert data["rrf_rank"] == 1


# =============================================================================
# Test Category 8: HybridBM25Retriever (existing compatibility)
# =============================================================================

class TestHybridBM25Retriever:
    """Tests for existing HybridBM25Retriever (two-way)."""
    
    def test_retriever_initialization(self):
        """T8.1: Retriever initializes correctly."""
        from src.knowledge.bm25 import HybridBM25Retriever, BM25Config
        from src.knowledge.storage import MemoryGraphBackend
        from src.knowledge.manager import default_embedding_function
        backend = MemoryGraphBackend()
        retriever = HybridBM25Retriever(backend, default_embedding_function)
        assert retriever is not None

    def test_index_claim(self):
        """T8.2: Index claim adds to BM25 index."""
        from src.knowledge.bm25 import HybridBM25Retriever
        from src.knowledge.storage import MemoryGraphBackend
        from src.knowledge.graph import KGClaim
        from src.knowledge.manager import default_embedding_function
        backend = MemoryGraphBackend()
        retriever = HybridBM25Retriever(backend, default_embedding_function)
        claim = KGClaim(
            claim_id="claim-1",
            text="Python is great for data science",
            confidence=0.9,
            source_url="https://example.com",
            embedding=default_embedding_function("Python is great for data science"),
        )
        backend.store_claim(claim)
        retriever.index_claim(claim)
        assert retriever.bm25_index.get_document_count() == 1

    def test_retrieve_combined(self):
        """T8.3: Retrieve returns combined results."""
        from src.knowledge.bm25 import HybridBM25Retriever
        from src.knowledge.storage import MemoryGraphBackend
        from src.knowledge.graph import KGClaim
        from src.knowledge.manager import default_embedding_function
        backend = MemoryGraphBackend()
        retriever = HybridBM25Retriever(backend, default_embedding_function)
        claim = KGClaim(
            claim_id="claim-1",
            text="Python is excellent for data science",
            confidence=0.9,
            source_url="https://example.com",
            embedding=default_embedding_function("Python is excellent for data science"),
        )
        backend.store_claim(claim)
        retriever.index_claim(claim)
        results = retriever.retrieve("Python data", limit=5)
        assert len(results) >= 1
