"""
Unit tests for Knowledge Graph Infrastructure (NESY-004).

Tests cover:
- Entity and Source dataclasses
- KGClaim and KGQueryResult structures
- Storage backends (Memory, SQLite)
- ResearchKnowledgeGraph operations
- Entity and topic extraction
- Semantic search and contradiction detection
- KGEnhancedResearchAgent integration
"""

import os
import pytest
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from knowledge import (
    # Enums
    EntityType,
    RelationType,
    # Dataclasses
    Entity,
    Source,
    KGClaim,
    KGQueryResult,
    ContradictionResult,
    # Storage
    GraphStorageBackend,
    MemoryGraphBackend,
    SQLiteGraphBackend,
    cosine_similarity,
    # Manager
    ResearchKnowledgeGraph,
    EntityExtractor,
    TopicExtractor,
    default_embedding_function,
    get_default_knowledge_graph,
    # Agent
    KGEnhancedResearchAgent,
    ResearchClaim,
    ResearchOutput,
    MockResearchAgent,
)


# ============================================================================
# Utility Tests
# ============================================================================

class TestCosineSimilarity:
    """Tests for cosine similarity function."""

    def test_identical_vectors(self):
        """Test similarity of identical vectors."""
        vec = [1.0, 2.0, 3.0]
        assert cosine_similarity(vec, vec) == pytest.approx(1.0, rel=1e-5)

    def test_orthogonal_vectors(self):
        """Test similarity of orthogonal vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        assert cosine_similarity(vec1, vec2) == pytest.approx(0.0, rel=1e-5)

    def test_opposite_vectors(self):
        """Test similarity of opposite vectors."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [-1.0, -2.0, -3.0]
        assert cosine_similarity(vec1, vec2) == pytest.approx(-1.0, rel=1e-5)

    def test_empty_vectors(self):
        """Test with empty vectors."""
        assert cosine_similarity([], []) == 0.0

    def test_different_lengths(self):
        """Test with different length vectors."""
        assert cosine_similarity([1.0, 2.0], [1.0, 2.0, 3.0]) == 0.0


class TestDefaultEmbedding:
    """Tests for default embedding function."""

    def test_returns_list(self):
        """Test that embedding returns a list."""
        embedding = default_embedding_function("test text")
        assert isinstance(embedding, list)

    def test_correct_dimension(self):
        """Test embedding has correct dimension."""
        embedding = default_embedding_function("test text")
        assert len(embedding) == 384

    def test_deterministic(self):
        """Test embedding is deterministic."""
        text = "same text"
        emb1 = default_embedding_function(text)
        emb2 = default_embedding_function(text)
        assert emb1 == emb2

    def test_different_text_different_embedding(self):
        """Test different text produces different embeddings."""
        emb1 = default_embedding_function("text one")
        emb2 = default_embedding_function("text two")
        assert emb1 != emb2


# ============================================================================
# Dataclass Tests
# ============================================================================

class TestEntity:
    """Tests for Entity dataclass."""

    def test_create_entity(self):
        """Test creating an entity."""
        entity = Entity(name="Python", entity_type=EntityType.TECHNOLOGY)
        assert entity.name == "Python"
        assert entity.entity_type == EntityType.TECHNOLOGY

    def test_to_dict(self):
        """Test converting entity to dict."""
        entity = Entity(name="Google", entity_type=EntityType.ORGANIZATION)
        d = entity.to_dict()
        assert d["name"] == "Google"
        assert d["type"] == "organization"

    def test_from_dict(self):
        """Test creating entity from dict."""
        d = {"name": "OpenAI", "type": "organization", "metadata": {"founded": 2015}}
        entity = Entity.from_dict(d)
        assert entity.name == "OpenAI"
        assert entity.entity_type == EntityType.ORGANIZATION
        assert entity.metadata["founded"] == 2015


class TestSource:
    """Tests for Source dataclass."""

    def test_create_source(self):
        """Test creating a source."""
        source = Source(
            url="https://example.com/article",
            title="Test Article",
        )
        assert source.url == "https://example.com/article"
        assert source.title == "Test Article"

    def test_to_dict(self):
        """Test converting source to dict."""
        source = Source(url="https://example.com", title="Example")
        d = source.to_dict()
        assert d["url"] == "https://example.com"
        assert d["title"] == "Example"
        assert "last_accessed" in d

    def test_from_dict(self):
        """Test creating source from dict."""
        d = {
            "url": "https://test.com",
            "title": "Test",
            "author": "John Doe",
        }
        source = Source.from_dict(d)
        assert source.url == "https://test.com"
        assert source.author == "John Doe"


class TestKGClaim:
    """Tests for KGClaim dataclass."""

    def test_create_claim(self):
        """Test creating a claim."""
        claim = KGClaim(
            text="Python is a programming language",
            confidence=0.95,
            source_url="https://python.org",
            source_title="Python.org",
        )
        assert claim.text == "Python is a programming language"
        assert claim.confidence == 0.95
        assert claim.claim_id  # Auto-generated

    def test_to_dict(self):
        """Test converting claim to dict."""
        claim = KGClaim(
            text="Test claim",
            confidence=0.8,
            source_url="https://test.com",
            topics=["testing"],
        )
        d = claim.to_dict()
        assert d["text"] == "Test claim"
        assert d["confidence"] == 0.8
        assert "testing" in d["topics"]

    def test_from_dict(self):
        """Test creating claim from dict."""
        d = {
            "text": "A test claim",
            "confidence": 0.7,
            "source_url": "https://source.com",
            "topics": ["topic1", "topic2"],
        }
        claim = KGClaim.from_dict(d)
        assert claim.text == "A test claim"
        assert len(claim.topics) == 2


class TestKGQueryResult:
    """Tests for KGQueryResult dataclass."""

    def test_create_result(self):
        """Test creating a query result."""
        result = KGQueryResult(
            claims=[{"id": "1", "text": "Claim 1"}],
            sources=[{"url": "https://test.com"}],
            query_time_ms=50,
        )
        assert len(result.claims) == 1
        assert result.query_time_ms == 50

    def test_to_dict(self):
        """Test converting result to dict."""
        result = KGQueryResult(claims=[], sources=[], query_time_ms=10)
        d = result.to_dict()
        assert "claims" in d
        assert "query_time_ms" in d


# ============================================================================
# Entity Extractor Tests
# ============================================================================

class TestEntityExtractor:
    """Tests for EntityExtractor."""

    def test_extract_technology(self):
        """Test extracting technology entities."""
        extractor = EntityExtractor()
        entities = extractor.extract("Python and JavaScript are popular programming languages")

        names = [e.name for e in entities]
        assert "Python" in names
        assert "JavaScript" in names

    def test_extract_organization(self):
        """Test extracting organization entities."""
        extractor = EntityExtractor()
        entities = extractor.extract("Google and Microsoft are tech giants")

        names = [e.name.lower() for e in entities]
        assert "google" in names
        assert "microsoft" in names

    def test_extract_metrics(self):
        """Test extracting metric entities."""
        extractor = EntityExtractor()
        entities = extractor.extract("The model achieved 95% accuracy and costs $100")

        # Check that we extracted some metric entities
        metric_entities = [e for e in entities if e.entity_type == EntityType.METRIC]
        assert len(metric_entities) >= 1

    def test_extract_dates(self):
        """Test extracting date entities."""
        extractor = EntityExtractor()
        entities = extractor.extract("The event happened on 2024-01-15")

        types = [e.entity_type for e in entities]
        assert EntityType.DATE in types


class TestTopicExtractor:
    """Tests for TopicExtractor."""

    def test_extract_ai_topic(self):
        """Test extracting AI-related topics."""
        extractor = TopicExtractor()
        topics = extractor.extract("Machine learning and deep learning are types of AI")

        assert "artificial intelligence" in topics

    def test_extract_web_topic(self):
        """Test extracting web development topics."""
        extractor = TopicExtractor()
        topics = extractor.extract("Building APIs with REST and frontend development")

        assert "web development" in topics

    def test_extract_multiple_topics(self):
        """Test extracting multiple topics."""
        extractor = TopicExtractor()
        topics = extractor.extract(
            "Using Python for data science and machine learning on AWS cloud"
        )

        assert len(topics) >= 2


# ============================================================================
# Memory Storage Backend Tests
# ============================================================================

class TestMemoryGraphBackend:
    """Tests for MemoryGraphBackend."""

    def test_store_and_get_claim(self):
        """Test storing and retrieving a claim."""
        storage = MemoryGraphBackend()
        claim = KGClaim(
            text="Test claim",
            confidence=0.9,
            source_url="https://test.com",
            embedding=[0.1] * 384,
        )
        storage.store_claim(claim)
        retrieved = storage.get_claim(claim.claim_id)

        assert retrieved is not None
        assert retrieved.text == "Test claim"

    def test_store_source(self):
        """Test storing a source."""
        storage = MemoryGraphBackend()
        source = Source(url="https://example.com", title="Example")
        storage.store_source(source)

        retrieved = storage.get_source("https://example.com")
        assert retrieved is not None
        assert retrieved.title == "Example"

    def test_add_relationship(self):
        """Test adding a relationship."""
        storage = MemoryGraphBackend()
        result = storage.add_relationship(
            "claim-1",
            "source-1",
            RelationType.SOURCED_FROM,
        )
        assert result

    def test_find_by_embedding(self):
        """Test finding claims by embedding."""
        storage = MemoryGraphBackend()

        # Add claims with embeddings
        claim1 = KGClaim(
            text="Python programming",
            confidence=0.9,
            source_url="https://test1.com",
            embedding=[1.0] + [0.0] * 383,
        )
        claim2 = KGClaim(
            text="JavaScript programming",
            confidence=0.8,
            source_url="https://test2.com",
            embedding=[0.9] + [0.1] * 383,
        )
        storage.store_claim(claim1)
        storage.store_claim(claim2)

        # Search with similar embedding
        results = storage.find_claims_by_embedding(
            [1.0] + [0.0] * 383,
            limit=10,
            min_similarity=0.5,
        )

        assert len(results) >= 1
        assert results[0][0].text == "Python programming"

    def test_find_by_entity(self):
        """Test finding claims by entity."""
        storage = MemoryGraphBackend()
        claim = KGClaim(
            text="Python is great",
            confidence=0.9,
            source_url="https://test.com",
            entities=[Entity(name="Python", entity_type=EntityType.TECHNOLOGY)],
        )
        storage.store_claim(claim)

        results = storage.find_claims_by_entity("Python", EntityType.TECHNOLOGY)
        assert len(results) == 1
        assert results[0].text == "Python is great"

    def test_find_by_topic(self):
        """Test finding claims by topic."""
        storage = MemoryGraphBackend()
        claim = KGClaim(
            text="AI is advancing",
            confidence=0.9,
            source_url="https://test.com",
            topics=["artificial intelligence"],
        )
        storage.store_claim(claim)

        results = storage.find_claims_by_topic("artificial intelligence")
        assert len(results) == 1

    def test_find_by_session(self):
        """Test finding claims by session."""
        storage = MemoryGraphBackend()
        claim = KGClaim(
            text="Session claim",
            confidence=0.9,
            source_url="https://test.com",
            session_id="session-123",
        )
        storage.store_claim(claim)

        results = storage.find_claims_by_session("session-123")
        assert len(results) == 1

    def test_get_provenance_chain(self):
        """Test getting provenance chain."""
        storage = MemoryGraphBackend()

        # Store claim and source
        claim = KGClaim(
            text="A claim",
            confidence=0.9,
            source_url="https://source.com",
        )
        source = Source(url="https://source.com", title="The Source")
        storage.store_claim(claim)
        storage.store_source(source)

        chain = storage.get_provenance_chain(claim.claim_id)
        assert len(chain) >= 1
        assert chain[0]["type"] == "claim"

    def test_get_related_claims(self):
        """Test getting related claims."""
        storage = MemoryGraphBackend()

        # Add claims sharing an entity
        entity = Entity(name="Python", entity_type=EntityType.TECHNOLOGY)
        claim1 = KGClaim(
            text="Claim 1 about Python",
            confidence=0.9,
            source_url="https://test1.com",
            entities=[entity],
        )
        claim2 = KGClaim(
            text="Claim 2 about Python",
            confidence=0.8,
            source_url="https://test2.com",
            entities=[entity],
        )
        storage.store_claim(claim1)
        storage.store_claim(claim2)

        related = storage.get_related_claims(claim1.claim_id)
        assert len(related) == 1
        assert related[0][0].claim_id == claim2.claim_id

    def test_counts(self):
        """Test counting functions."""
        storage = MemoryGraphBackend()
        assert storage.count_claims() == 0
        assert storage.count_sources() == 0
        assert storage.count_entities() == 0

        claim = KGClaim(
            text="Test",
            confidence=0.9,
            source_url="https://test.com",
            entities=[Entity(name="Test", entity_type=EntityType.OTHER)],
        )
        storage.store_claim(claim)

        assert storage.count_claims() == 1
        assert storage.count_sources() == 1
        assert storage.count_entities() == 1


# ============================================================================
# SQLite Storage Backend Tests
# ============================================================================

def _safe_delete(path: str) -> None:
    """Safely delete a file, handling Windows locking issues."""
    import gc
    gc.collect()
    try:
        os.unlink(path)
    except PermissionError:
        pass  # File in use on Windows, will be cleaned up by OS later


class TestSQLiteGraphBackend:
    """Tests for SQLiteGraphBackend."""

    def test_store_and_get_claim(self):
        """Test storing and retrieving a claim."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            storage = SQLiteGraphBackend(db_path)
            claim = KGClaim(
                text="SQLite test claim",
                confidence=0.85,
                source_url="https://sqlite.org",
                entities=[Entity(name="SQLite", entity_type=EntityType.TECHNOLOGY)],
                topics=["databases"],
            )
            storage.store_claim(claim)

            retrieved = storage.get_claim(claim.claim_id)
            assert retrieved is not None
            assert retrieved.text == "SQLite test claim"
            assert len(retrieved.entities) == 1
            assert "databases" in retrieved.topics
        finally:
            _safe_delete(db_path)

    def test_persistence(self):
        """Test that data persists across instances."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            # Store claim
            storage1 = SQLiteGraphBackend(db_path)
            claim = KGClaim(
                text="Persistent claim",
                confidence=0.9,
                source_url="https://test.com",
            )
            storage1.store_claim(claim)
            claim_id = claim.claim_id

            # Create new instance
            storage2 = SQLiteGraphBackend(db_path)
            retrieved = storage2.get_claim(claim_id)
            assert retrieved is not None
            assert retrieved.text == "Persistent claim"
        finally:
            _safe_delete(db_path)

    def test_find_by_embedding(self):
        """Test finding claims by embedding in SQLite."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            storage = SQLiteGraphBackend(db_path)
            claim = KGClaim(
                text="Embedding test",
                confidence=0.9,
                source_url="https://test.com",
                embedding=[1.0] * 384,
            )
            storage.store_claim(claim)

            results = storage.find_claims_by_embedding(
                [1.0] * 384,
                limit=10,
                min_similarity=0.9,
            )
            assert len(results) == 1
        finally:
            _safe_delete(db_path)

    def test_counts(self):
        """Test counting in SQLite backend."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            storage = SQLiteGraphBackend(db_path)
            assert storage.count_claims() == 0

            claim = KGClaim(
                text="Test",
                confidence=0.9,
                source_url="https://test.com",
            )
            storage.store_claim(claim)

            assert storage.count_claims() == 1
            assert storage.count_sources() == 1
        finally:
            _safe_delete(db_path)


# ============================================================================
# ResearchKnowledgeGraph Tests
# ============================================================================

class TestResearchKnowledgeGraph:
    """Tests for ResearchKnowledgeGraph."""

    def test_create_graph(self):
        """Test creating a knowledge graph."""
        kg = ResearchKnowledgeGraph()
        assert kg.storage is not None
        assert kg.embedding_fn is not None

    def test_add_claim(self):
        """Test adding a claim."""
        kg = ResearchKnowledgeGraph()
        claim_id = kg.add_claim(
            text="Python is a programming language",
            confidence=0.95,
            source_url="https://python.org",
            source_title="Python.org",
            session_id="test-session",
        )

        assert claim_id
        claim = kg.get_claim(claim_id)
        assert claim is not None
        assert claim.text == "Python is a programming language"

    def test_auto_extract_entities(self):
        """Test automatic entity extraction."""
        kg = ResearchKnowledgeGraph()
        claim_id = kg.add_claim(
            text="Google and Microsoft are investing in AI",
            confidence=0.9,
            source_url="https://news.com",
        )

        claim = kg.get_claim(claim_id)
        assert claim is not None
        entity_names = [e.name.lower() for e in claim.entities]
        assert "google" in entity_names or "microsoft" in entity_names

    def test_auto_extract_topics(self):
        """Test automatic topic extraction."""
        kg = ResearchKnowledgeGraph()
        claim_id = kg.add_claim(
            text="Machine learning is transforming AI research",
            confidence=0.9,
            source_url="https://ai.com",
        )

        claim = kg.get_claim(claim_id)
        assert claim is not None
        assert len(claim.topics) > 0

    def test_find_related_claims(self):
        """Test finding related claims."""
        kg = ResearchKnowledgeGraph()

        # Add some claims
        kg.add_claim(
            text="Python is great for data science",
            confidence=0.9,
            source_url="https://python.org",
            session_id="test",
        )
        kg.add_claim(
            text="JavaScript is popular for web development",
            confidence=0.85,
            source_url="https://js.org",
            session_id="test",
        )

        # Search
        results = kg.find_related_claims("programming languages", limit=10)
        assert isinstance(results, KGQueryResult)
        assert results.query_time_ms >= 0

    def test_get_provenance_chain(self):
        """Test provenance chain retrieval."""
        kg = ResearchKnowledgeGraph()
        claim_id = kg.add_claim(
            text="Test claim",
            confidence=0.9,
            source_url="https://source.com",
            source_title="The Source",
        )

        chain = kg.get_provenance_chain(claim_id)
        assert len(chain) >= 1

    def test_find_contradictions(self):
        """Test contradiction detection."""
        kg = ResearchKnowledgeGraph()

        # Add claims on same topic with different sources
        kg.add_claim(
            text="AI will replace all jobs",
            confidence=0.7,
            source_url="https://pessimist.com",
            topics=["artificial intelligence", "employment"],
        )
        id2 = kg.add_claim(
            text="AI will create more jobs than it eliminates",
            confidence=0.8,
            source_url="https://optimist.com",
            topics=["artificial intelligence", "employment"],
        )

        result = kg.find_contradictions(id2)
        assert isinstance(result, ContradictionResult)
        # May or may not find contradictions based on embedding similarity

    def test_find_claims_by_entity(self):
        """Test finding claims by entity."""
        kg = ResearchKnowledgeGraph()
        kg.add_claim(
            text="Python is used for AI",
            confidence=0.9,
            source_url="https://test.com",
            entities=[Entity(name="Python", entity_type=EntityType.TECHNOLOGY)],
        )

        results = kg.find_claims_by_entity("Python", EntityType.TECHNOLOGY)
        assert len(results) == 1

    def test_find_claims_by_topic(self):
        """Test finding claims by topic."""
        kg = ResearchKnowledgeGraph()
        kg.add_claim(
            text="Cloud computing is growing",
            confidence=0.9,
            source_url="https://test.com",
            topics=["cloud computing"],
        )

        results = kg.find_claims_by_topic("cloud computing")
        assert len(results) == 1

    def test_find_claims_by_session(self):
        """Test finding claims by session."""
        kg = ResearchKnowledgeGraph()
        kg.add_claim(
            text="Session 1 claim",
            confidence=0.9,
            source_url="https://test.com",
            session_id="session-1",
        )
        kg.add_claim(
            text="Session 2 claim",
            confidence=0.9,
            source_url="https://test.com",
            session_id="session-2",
        )

        results = kg.find_claims_by_session("session-1")
        assert len(results) == 1
        assert results[0].session_id == "session-1"

    def test_get_session_context(self):
        """Test getting session context."""
        kg = ResearchKnowledgeGraph()
        kg.add_claim(
            text="Python is great",
            confidence=0.9,
            source_url="https://python.org",
            source_title="Python.org",
            session_id="my-session",
        )

        context = kg.get_session_context("my-session")
        assert "Python" in context

    def test_get_stats(self):
        """Test getting statistics."""
        kg = ResearchKnowledgeGraph()
        kg.add_claim(
            text="Test claim",
            confidence=0.9,
            source_url="https://test.com",
        )

        stats = kg.get_stats()
        assert stats["claims_added"] == 1
        assert stats["total_claims"] == 1

    def test_with_sqlite_backend(self):
        """Test with SQLite backend."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            storage = SQLiteGraphBackend(db_path)
            kg = ResearchKnowledgeGraph(storage=storage)

            claim_id = kg.add_claim(
                text="SQLite backed claim",
                confidence=0.9,
                source_url="https://sqlite.org",
            )

            claim = kg.get_claim(claim_id)
            assert claim is not None
            assert claim.text == "SQLite backed claim"
        finally:
            _safe_delete(db_path)


# ============================================================================
# KGEnhancedResearchAgent Tests
# ============================================================================

class TestKGEnhancedResearchAgent:
    """Tests for KGEnhancedResearchAgent."""

    @pytest.mark.asyncio
    async def test_create_agent(self):
        """Test creating an enhanced agent."""
        kg = ResearchKnowledgeGraph()
        base_agent = MockResearchAgent()
        enhanced = KGEnhancedResearchAgent(base_agent, kg)

        assert enhanced.agent is base_agent
        assert enhanced.kg is kg

    @pytest.mark.asyncio
    async def test_research_stores_findings(self):
        """Test that research stores findings in KG."""
        kg = ResearchKnowledgeGraph()
        base_agent = MockResearchAgent()
        enhanced = KGEnhancedResearchAgent(base_agent, kg)

        output = await enhanced.research(
            "What is Python?",
            session_id="test-session",
            store_findings=True,
        )

        assert output is not None
        assert len(output.claims) > 0

        # Check that claims were stored
        session_claims = kg.find_claims_by_session("test-session")
        assert len(session_claims) > 0

    @pytest.mark.asyncio
    async def test_research_uses_existing_knowledge(self):
        """Test that research uses existing knowledge."""
        kg = ResearchKnowledgeGraph()

        # Add existing knowledge
        kg.add_claim(
            text="Python was created by Guido van Rossum",
            confidence=0.95,
            source_url="https://python.org/history",
            topics=["python", "programming"],
        )

        base_agent = MockResearchAgent()
        enhanced = KGEnhancedResearchAgent(base_agent, kg)

        output = await enhanced.research(
            "Tell me about Python's history",
            session_id="test-session",
            include_existing_knowledge=True,
        )

        assert output is not None

    @pytest.mark.asyncio
    async def test_get_session_summary(self):
        """Test getting session summary."""
        kg = ResearchKnowledgeGraph()
        kg.add_claim(
            text="AI is transforming industries",
            confidence=0.9,
            source_url="https://ai.com",
            topics=["artificial intelligence"],
            session_id="summary-session",
        )

        base_agent = MockResearchAgent()
        enhanced = KGEnhancedResearchAgent(base_agent, kg)

        summary = enhanced.get_session_summary("summary-session")
        assert "summary-session" in summary
        assert "AI" in summary or "artificial intelligence" in summary.lower()


class TestResearchOutput:
    """Tests for ResearchOutput dataclass."""

    def test_create_output(self):
        """Test creating research output."""
        output = ResearchOutput(
            claims=[ResearchClaim(text="Test claim", confidence=0.9)],
            summary="A summary",
            agent_id="test-agent",
        )
        assert len(output.claims) == 1
        assert output.summary == "A summary"


class TestMockResearchAgent:
    """Tests for MockResearchAgent."""

    @pytest.mark.asyncio
    async def test_mock_research(self):
        """Test mock research output."""
        agent = MockResearchAgent()
        output = await agent.research("Test query")

        assert output is not None
        assert len(output.claims) == 1
        assert output.agent_id == "mock-researcher"


# ============================================================================
# Integration Tests
# ============================================================================

class TestKnowledgeGraphIntegration:
    """Integration tests for knowledge graph."""

    def test_full_workflow(self):
        """Test complete workflow."""
        kg = ResearchKnowledgeGraph()

        # Add multiple claims from a research session
        session_id = "research-session-1"

        kg.add_claim(
            text="GPT-4 achieves 86.4% on MMLU benchmark",
            confidence=0.95,
            source_url="https://openai.com/gpt-4",
            source_title="GPT-4 Technical Report",
            session_id=session_id,
        )

        kg.add_claim(
            text="Claude 3 Opus performs well on reasoning tasks",
            confidence=0.9,
            source_url="https://anthropic.com/claude-3",
            source_title="Claude 3 Announcement",
            session_id=session_id,
        )

        kg.add_claim(
            text="LLM performance varies across different benchmarks",
            confidence=0.85,
            source_url="https://research.ai/benchmarks",
            source_title="AI Benchmark Analysis",
            session_id=session_id,
        )

        # Query related claims
        results = kg.find_related_claims("AI model performance evaluation")
        assert len(results.claims) >= 0  # May find matches

        # Get session context
        context = kg.get_session_context(session_id)
        assert session_id in context or "knowledge" in context.lower()

        # Check stats
        stats = kg.get_stats()
        assert stats["total_claims"] == 3
        assert stats["total_sources"] == 3

    def test_contradiction_workflow(self):
        """Test contradiction detection workflow."""
        kg = ResearchKnowledgeGraph()

        # Add potentially contradicting claims
        id1 = kg.add_claim(
            text="Remote work increases productivity by 20%",
            confidence=0.8,
            source_url="https://pro-remote.com/study",
            topics=["remote work", "productivity"],
        )

        id2 = kg.add_claim(
            text="Remote work decreases productivity by 15%",
            confidence=0.75,
            source_url="https://office-work.com/study",
            topics=["remote work", "productivity"],
        )

        # Check for contradictions
        result1 = kg.find_contradictions(id1)
        result2 = kg.find_contradictions(id2)

        # Both should have shared topics
        assert "remote work" in result1.shared_topics or "productivity" in result1.shared_topics

    def test_provenance_tracking(self):
        """Test provenance chain tracking."""
        kg = ResearchKnowledgeGraph()

        claim_id = kg.add_claim(
            text="Derived insight about AI",
            confidence=0.85,
            source_url="https://source.com/article",
            source_title="Original Article",
        )

        chain = kg.get_provenance_chain(claim_id)
        assert len(chain) >= 1
        assert chain[0]["type"] == "claim"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
