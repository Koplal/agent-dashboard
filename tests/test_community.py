#!/usr/bin/env python3
"""Tests for P2-001: Leiden Community Detection. Version: 2.7.0"""
import pytest

# Check if igraph and leidenalg are available
try:
    import igraph
    IGRAPH_AVAILABLE = True
except ImportError:
    IGRAPH_AVAILABLE = False

try:
    import leidenalg
    LEIDENALG_AVAILABLE = True
except ImportError:
    LEIDENALG_AVAILABLE = False

class TestCommunityConfig:
    def test_config_default_resolution(self):
        from src.knowledge.community import CommunityConfig
        assert CommunityConfig().resolution == 1.0

    def test_config_default_min_community_size(self):
        from src.knowledge.community import CommunityConfig
        assert CommunityConfig().min_community_size == 2

    def test_config_custom_values(self):
        from src.knowledge.community import CommunityConfig
        c = CommunityConfig(resolution=2.0, min_community_size=5, seed=42)
        assert c.resolution == 2.0 and c.min_community_size == 5 and c.seed == 42

class TestCommunity:
    def test_community_has_id(self):
        from src.knowledge.community import Community
        assert Community(community_id="c-1", members=["e1"], size=1).community_id == "c-1"

    def test_community_has_members(self):
        from src.knowledge.community import Community
        assert len(Community(community_id="c-1", members=["e1", "e2", "e3"], size=3).members) == 3

    def test_community_has_size(self):
        from src.knowledge.community import Community
        assert Community(community_id="c-1", members=["e1", "e2"], size=2).size == 2

    def test_community_optional_label(self):
        from src.knowledge.community import Community
        assert Community(community_id="c-1", members=["e1"], size=1).label is None
        assert Community(community_id="c-2", members=["e1"], size=1, label="Tech").label == "Tech"


class TestCommunityHierarchy:
    def test_hierarchy_has_root(self):
        from src.knowledge.community import Community, CommunityHierarchy
        root = Community(community_id="root", members=["e1"], size=1)
        assert CommunityHierarchy(root=root, levels=[[root]], total_communities=1).root == root

    def test_hierarchy_has_levels(self):
        from src.knowledge.community import Community, CommunityHierarchy
        root = Community(community_id="root", members=["e1", "e2"], size=2)
        level1 = [Community(community_id="c-1", members=["e1"], size=1)]
        h = CommunityHierarchy(root=root, levels=[[root], level1], total_communities=2)
        assert len(h.levels) == 2

    def test_hierarchy_get_level(self):
        from src.knowledge.community import Community, CommunityHierarchy
        root = Community(community_id="root", members=["e1"], size=1)
        h = CommunityHierarchy(root=root, levels=[[root]], total_communities=1)
        assert len(h.get_level(0)) == 1 and h.get_level(5) == []

class TestGraphConversion:
    def test_convert_empty_backend(self):
        from src.knowledge.community import CommunityDetector
        from src.knowledge.storage import MemoryGraphBackend
        detector = CommunityDetector()
        graph = detector._build_igraph(MemoryGraphBackend())
        assert graph.vcount() == 0 and graph.ecount() == 0

    @pytest.mark.skipif(not IGRAPH_AVAILABLE, reason="igraph required")
    def test_convert_single_claim(self):
        from src.knowledge.community import CommunityDetector
        from src.knowledge.storage import MemoryGraphBackend
        from src.knowledge.graph import KGClaim, Entity, EntityType
        backend = MemoryGraphBackend()
        backend.store_claim(KGClaim(
            claim_id="c-1", text="Test", confidence=0.9, source_url="https://ex.com",
            entities=[Entity(name="Python", entity_type=EntityType.TECHNOLOGY), Entity(name="Java", entity_type=EntityType.TECHNOLOGY)],
        ))
        assert CommunityDetector()._build_igraph(backend).vcount() >= 2


class TestCommunityDetection:
    @pytest.mark.skipif(not IGRAPH_AVAILABLE, reason="igraph required")
    def test_detect_returns_communities(self):
        from src.knowledge.community import CommunityDetector, Community
        from src.knowledge.storage import MemoryGraphBackend
        from src.knowledge.graph import KGClaim, Entity, EntityType
        backend = MemoryGraphBackend()
        for i in range(5):
            backend.store_claim(KGClaim(
                claim_id=f"c-{i}", text=f"Claim {i}", confidence=0.9, source_url="https://ex.com",
                entities=[Entity(name=f"e-{i}", entity_type=EntityType.CONCEPT), Entity(name=f"s-{i % 2}", entity_type=EntityType.CONCEPT)],
            ))
        result = CommunityDetector().detect(backend)
        assert len(result.communities) > 0
        assert all(isinstance(c, Community) for c in result.communities)

    def test_detect_returns_result_object(self):
        from src.knowledge.community import CommunityDetector, CommunityDetectionResult
        from src.knowledge.storage import MemoryGraphBackend
        from src.knowledge.graph import KGClaim, Entity, EntityType
        backend = MemoryGraphBackend()
        backend.store_claim(KGClaim(
            claim_id="c-1", text="Test", confidence=0.9, source_url="https://ex.com",
            entities=[Entity(name="e1", entity_type=EntityType.CONCEPT), Entity(name="e2", entity_type=EntityType.CONCEPT)],
        ))
        result = CommunityDetector().detect(backend)
        assert isinstance(result, CommunityDetectionResult)
        assert hasattr(result, "communities") and hasattr(result, "modularity")
        assert result.algorithm == "leiden"

class TestModularity:
    def test_modularity_returns_float(self):
        from src.knowledge.community import CommunityDetector
        from src.knowledge.storage import MemoryGraphBackend
        from src.knowledge.graph import KGClaim, Entity, EntityType
        backend = MemoryGraphBackend()
        for i in range(5):
            backend.store_claim(KGClaim(
                claim_id=f"c-{i}", text=f"Claim {i}", confidence=0.9, source_url="https://ex.com",
                entities=[Entity(name=f"e-{i}", entity_type=EntityType.CONCEPT), Entity(name=f"s-{i % 2}", entity_type=EntityType.CONCEPT)],
            ))
        assert isinstance(CommunityDetector().detect(backend).modularity, float)

    def test_modularity_in_valid_range(self):
        from src.knowledge.community import CommunityDetector
        from src.knowledge.storage import MemoryGraphBackend
        from src.knowledge.graph import KGClaim, Entity, EntityType
        backend = MemoryGraphBackend()
        for i in range(10):
            backend.store_claim(KGClaim(
                claim_id=f"c-{i}", text=f"Claim {i}", confidence=0.9, source_url="https://ex.com",
                entities=[Entity(name=f"e-{i}", entity_type=EntityType.CONCEPT), Entity(name=f"s-{i % 3}", entity_type=EntityType.CONCEPT)],
            ))
        m = CommunityDetector().detect(backend).modularity
        assert -0.5 <= m <= 1.0


class TestEdgeCases:
    def test_empty_graph(self):
        from src.knowledge.community import CommunityDetector
        from src.knowledge.storage import MemoryGraphBackend
        result = CommunityDetector().detect(MemoryGraphBackend())
        assert result.communities == [] and result.modularity == 0.0

    @pytest.mark.skipif(not IGRAPH_AVAILABLE, reason="igraph required")
    def test_single_node(self):
        from src.knowledge.community import CommunityDetector
        from src.knowledge.storage import MemoryGraphBackend
        from src.knowledge.graph import KGClaim, Entity, EntityType
        backend = MemoryGraphBackend()
        backend.store_claim(KGClaim(
            claim_id="c-1", text="Single", confidence=0.9, source_url="https://ex.com",
            entities=[Entity(name="solo", entity_type=EntityType.CONCEPT)],
        ))
        result = CommunityDetector().detect(backend)
        assert len(result.communities) == 1

class TestErrors:
    def test_negative_resolution_error(self):
        from src.knowledge.community import CommunityConfig
        with pytest.raises(ValueError, match="resolution"):
            CommunityConfig(resolution=-1.0)

    def test_zero_min_size_error(self):
        from src.knowledge.community import CommunityConfig
        with pytest.raises(ValueError, match="min_community_size"):
            CommunityConfig(min_community_size=0)

class TestIntegration:
    @pytest.mark.skipif(not IGRAPH_AVAILABLE, reason="igraph required")
    def test_ac001_performance(self):
        import time
        from src.knowledge.community import CommunityDetector
        from src.knowledge.storage import MemoryGraphBackend
        from src.knowledge.graph import KGClaim, Entity, EntityType
        backend = MemoryGraphBackend()
        for i in range(100):
            backend.store_claim(KGClaim(
                claim_id=f"c-{i}", text=f"Claim {i}", confidence=0.9, source_url="https://ex.com",
                entities=[Entity(name=f"e-{i}", entity_type=EntityType.CONCEPT), Entity(name=f"s-{i % 20}", entity_type=EntityType.CONCEPT)],
            ))
        start = time.time()
        result = CommunityDetector().detect(backend)
        assert time.time() - start < 5.0 and len(result.communities) > 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
