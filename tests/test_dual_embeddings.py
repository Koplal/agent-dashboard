# Test file for P1-001: Dual Embedding Strategy
# Version: 2.7.0
# Tests for: EmbeddingConfig, SemanticEmbedder, StructuralEmbedder, DualEmbedder, EmbeddingCache

import math
import time
import pytest


class TestDualEmbeddingConfig:
    def test_config_default_semantic_dim_is_384(self):
        from src.knowledge.embeddings import DualEmbeddingConfig
        config = DualEmbeddingConfig()
        assert config.embedding_dim == 384
    
    def test_config_default_structural_dim_is_128(self):
        from src.knowledge.embeddings import DualEmbeddingConfig
        config = DualEmbeddingConfig()
        assert config.node2vec_dimensions == 128
    
    def test_config_default_walk_length_is_80(self):
        from src.knowledge.embeddings import DualEmbeddingConfig
        config = DualEmbeddingConfig()
        assert config.node2vec_walk_length == 80
    
    def test_config_default_num_walks_is_10(self):
        from src.knowledge.embeddings import DualEmbeddingConfig
        config = DualEmbeddingConfig()
        assert config.node2vec_num_walks == 10
    
    def test_config_default_weights(self):
        from src.knowledge.embeddings import DualEmbeddingConfig
        config = DualEmbeddingConfig()
        assert config.semantic_weight == 0.7
        assert config.structural_weight == 0.3
    
    def test_config_weights_must_sum_to_one(self):
        from src.knowledge.embeddings import DualEmbeddingConfig
        with pytest.raises(ValueError, match="must sum to 1.0"):
            DualEmbeddingConfig(semantic_weight=0.8, structural_weight=0.5)
    
    def test_config_weights_non_negative(self):
        from src.knowledge.embeddings import DualEmbeddingConfig
        with pytest.raises(ValueError, match="non-negative"):
            DualEmbeddingConfig(semantic_weight=-0.3, structural_weight=1.3)
    
    def test_config_dimensions_positive(self):
        from src.knowledge.embeddings import DualEmbeddingConfig
        with pytest.raises(ValueError, match="positive"):
            DualEmbeddingConfig(embedding_dim=0)
    
    def test_config_to_dict(self):
        from src.knowledge.embeddings import DualEmbeddingConfig
        config = DualEmbeddingConfig()
        d = config.to_dict()
        assert d["embedding_dim"] == 384
        assert d["node2vec_dimensions"] == 128
    
    def test_config_from_dict(self):
        from src.knowledge.embeddings import DualEmbeddingConfig
        data = {
            "semantic_weight": 0.6, "structural_weight": 0.4,
            "embedding_dim": 384, "node2vec_dimensions": 128,
            "node2vec_walk_length": 80, "node2vec_num_walks": 10,
            "node2vec_p": 1.0, "node2vec_q": 1.0,
            "semantic_model": "all-MiniLM-L6-v2",
        }
        config = DualEmbeddingConfig.from_dict(data)
        assert config.semantic_weight == 0.6
        assert config.structural_weight == 0.4


class TestSemanticEmbedder:
    def test_embed_returns_384_dim_vector(self):
        from src.knowledge.embeddings import SemanticEmbedder
        embedder = SemanticEmbedder()
        embedding = embedder.embed("Test text for embedding")
        assert len(embedding) == 384
    
    def test_embed_is_l2_normalized(self):
        from src.knowledge.embeddings import SemanticEmbedder
        embedder = SemanticEmbedder()
        embedding = embedder.embed("Test text for embedding")
        magnitude = math.sqrt(sum(x * x for x in embedding))
        assert abs(magnitude - 1.0) < 0.01
    
    def test_embed_empty_text_returns_vector(self):
        from src.knowledge.embeddings import SemanticEmbedder
        embedder = SemanticEmbedder()
        embedding = embedder.embed("")
        assert len(embedding) == 384
    
    def test_embed_batch_returns_list_of_vectors(self):
        from src.knowledge.embeddings import SemanticEmbedder
        embedder = SemanticEmbedder()
        texts = ["First text", "Second text", "Third text"]
        embeddings = embedder.embed_batch(texts)
        assert len(embeddings) == 3
        for emb in embeddings:
            assert len(emb) == 384
    
    def test_embed_different_texts_produce_different_vectors(self):
        from src.knowledge.embeddings import SemanticEmbedder
        embedder = SemanticEmbedder()
        emb1 = embedder.embed("Python programming language")
        emb2 = embedder.embed("JavaScript programming language")
        diff = sum(abs(a - b) for a, b in zip(emb1, emb2))
        assert diff > 0.01


class TestStructuralEmbedder:
    def test_structural_dim_is_128(self):
        from src.knowledge.embeddings import StructuralEmbedder, DualEmbeddingConfig
        config = DualEmbeddingConfig()
        embedder = StructuralEmbedder(config)
        assert embedder.dimensions == 128
    
    def test_add_node(self):
        from src.knowledge.embeddings import StructuralEmbedder
        embedder = StructuralEmbedder()
        embedder.add_node("node-1")
        assert "node-1" in embedder.graph.nodes()
    
    def test_add_edge(self):
        from src.knowledge.embeddings import StructuralEmbedder
        embedder = StructuralEmbedder()
        embedder.add_node("node-1")
        embedder.add_node("node-2")
        embedder.add_edge("node-1", "node-2")
        assert embedder.graph.has_edge("node-1", "node-2")
    
    def test_embed_returns_none_before_training(self):
        from src.knowledge.embeddings import StructuralEmbedder
        embedder = StructuralEmbedder()
        embedder.add_node("node-1")
        result = embedder.get_embedding("node-1")
        assert result is None
    
    def test_embed_returns_128_dim_after_training(self):
        from src.knowledge.embeddings import StructuralEmbedder, DualEmbeddingConfig
        config = DualEmbeddingConfig()
        embedder = StructuralEmbedder(config)
        embedder.add_node("node-1")
        embedder.add_node("node-2")
        embedder.add_node("node-3")
        embedder.add_edge("node-1", "node-2")
        embedder.add_edge("node-2", "node-3")
        embedder.train()
        embedding = embedder.get_embedding("node-1")
        assert embedding is not None
        assert len(embedding) == 128
    
    def test_embed_unknown_node_returns_none(self):
        from src.knowledge.embeddings import StructuralEmbedder
        embedder = StructuralEmbedder()
        embedder.add_node("node-1")
        embedder.train()
        result = embedder.get_embedding("unknown-node")
        assert result is None


class TestDualEmbedder:
    def test_embed_text_returns_384_dim(self):
        from src.knowledge.embeddings import DualEmbedder, DualEmbeddingConfig
        config = DualEmbeddingConfig(semantic_weight=1.0, structural_weight=0.0)
        embedder = DualEmbedder(config)
        embedding = embedder.embed_text("Python programming")
        assert len(embedding) == 384
    
    def test_combined_embed_returns_512_dim(self):
        from src.knowledge.embeddings import DualEmbedder, DualEmbeddingConfig
        config = DualEmbeddingConfig()
        embedder = DualEmbedder(config)
        embedder.add_claim_to_graph("claim-1", ["entity-a", "entity-b"])
        embedder.train_structural()
        class MockClaim:
            text = "Test claim text"
            claim_id = "claim-1"
        embedding = embedder.embed_claim(MockClaim())
        assert len(embedding) == 512
    
    def test_combined_embed_pads_when_no_structural(self):
        from src.knowledge.embeddings import DualEmbedder, DualEmbeddingConfig
        config = DualEmbeddingConfig()
        embedder = DualEmbedder(config)
        class MockClaim:
            text = "Test claim text"
            claim_id = "unknown-claim"
        embedding = embedder.embed_claim(MockClaim())
        assert len(embedding) >= 384
    
    def test_compute_similarity(self):
        from src.knowledge.embeddings import DualEmbedder
        embedder = DualEmbedder()
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        similarity = embedder.compute_similarity(vec1, vec2)
        assert abs(similarity - 1.0) < 0.01
    
    def test_compute_similarity_orthogonal(self):
        from src.knowledge.embeddings import DualEmbedder
        embedder = DualEmbedder()
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        similarity = embedder.compute_similarity(vec1, vec2)
        assert abs(similarity) < 0.01


class TestEmbeddingCache:
    def test_cache_stores_and_retrieves(self):
        from src.knowledge.embeddings import EmbeddingCache
        cache = EmbeddingCache()
        embedding = [0.1, 0.2, 0.3, 0.4]
        cache.set("key1", embedding)
        result = cache.get("key1")
        assert result == embedding
    
    def test_cache_returns_none_for_missing_key(self):
        from src.knowledge.embeddings import EmbeddingCache
        cache = EmbeddingCache()
        result = cache.get("nonexistent")
        assert result is None
    
    def test_cache_expires_after_ttl(self):
        from src.knowledge.embeddings import EmbeddingCache
        cache = EmbeddingCache(default_ttl=0.1)
        embedding = [0.1, 0.2, 0.3, 0.4]
        cache.set("key1", embedding)
        assert cache.get("key1") is not None
        time.sleep(0.15)
        assert cache.get("key1") is None
    
    def test_cache_custom_ttl_per_entry(self):
        from src.knowledge.embeddings import EmbeddingCache
        cache = EmbeddingCache(default_ttl=3600)
        embedding = [0.1, 0.2, 0.3, 0.4]
        cache.set("key1", embedding, ttl=0.1)
        time.sleep(0.15)
        assert cache.get("key1") is None
    
    def test_cache_no_expiration_with_negative_ttl(self):
        from src.knowledge.embeddings import EmbeddingCache
        cache = EmbeddingCache(default_ttl=-1)
        embedding = [0.1, 0.2, 0.3, 0.4]
        cache.set("key1", embedding)
        time.sleep(0.1)
        assert cache.get("key1") is not None
    
    def test_cache_clear(self):
        from src.knowledge.embeddings import EmbeddingCache
        cache = EmbeddingCache()
        cache.set("key1", [0.1])
        cache.set("key2", [0.2])
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None
    
    def test_cache_size(self):
        from src.knowledge.embeddings import EmbeddingCache
        cache = EmbeddingCache()
        assert cache.size() == 0
        cache.set("key1", [0.1])
        assert cache.size() == 1
        cache.set("key2", [0.2])
        assert cache.size() == 2
    
    def test_cache_evicts_expired_on_access(self):
        from src.knowledge.embeddings import EmbeddingCache
        cache = EmbeddingCache(default_ttl=0.1)
        cache.set("key1", [0.1])
        assert cache.size() == 1
        time.sleep(0.15)
        cache.get("key1")
        assert cache.size() == 0


class TestDualEmbedderWithCache:
    def test_embedder_uses_cache(self):
        from src.knowledge.embeddings import DualEmbedder, DualEmbeddingConfig, EmbeddingCache
        config = DualEmbeddingConfig()
        cache = EmbeddingCache()
        embedder = DualEmbedder(config, cache=cache)
        emb1 = embedder.embed_text("Same text")
        assert cache.size() >= 1
        emb2 = embedder.embed_text("Same text")
        assert emb1 == emb2
