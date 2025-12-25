"""
Research Knowledge Graph Manager.

Provides high-level interface for knowledge graph operations,
including entity extraction, semantic search, and contradiction detection.

Version: 2.6.0
"""

import logging
import re
import time
from typing import Dict, Any, List, Optional, Callable, Tuple

from .graph import (
    GraphStorageBackend,
    KGClaim,
    KGQueryResult,
    ContradictionResult,
    Source,
    Entity,
    EntityType,
    RelationType,
    utc_now,
)
from .storage import MemoryGraphBackend, cosine_similarity

logger = logging.getLogger(__name__)


# Type alias for embedding function
EmbeddingFunction = Callable[[str], List[float]]


def default_embedding_function(text: str) -> List[float]:
    """
    Simple hash-based pseudo-embedding for testing.

    In production, replace with a real embedding model like
    sentence-transformers or OpenAI embeddings.
    """
    import hashlib

    # Create a deterministic pseudo-embedding from text hash
    text_hash = hashlib.sha256(text.encode()).hexdigest()

    # Convert hash to 384-dimensional vector (matching all-MiniLM-L6-v2)
    embedding = []
    for i in range(0, 64, 1):
        # Convert each hex char to float between -1 and 1
        val = int(text_hash[i % 64], 16) / 8.0 - 1.0
        embedding.append(val)

    # Pad to 384 dimensions
    while len(embedding) < 384:
        embedding.append(embedding[len(embedding) % 64])

    # Normalize
    import math
    norm = math.sqrt(sum(x * x for x in embedding))
    if norm > 0:
        embedding = [x / norm for x in embedding]

    return embedding


class EntityExtractor:
    """
    Extracts entities from text using pattern matching.

    For production use, consider spaCy NER or an LLM-based extractor.
    """

    # Common patterns for entity extraction
    PATTERNS = {
        EntityType.DATE: [
            r"\b\d{4}-\d{2}-\d{2}\b",
            r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
            r"\b\d{1,2}/\d{1,2}/\d{4}\b",
        ],
        EntityType.METRIC: [
            r"\b\d+(?:\.\d+)?%\b",
            r"\$\d+(?:,\d{3})*(?:\.\d{2})?\b",
            r"\b\d+(?:\.\d+)?\s*(?:million|billion|trillion)\b",
        ],
        EntityType.ORGANIZATION: [
            r"\b(?:Google|Microsoft|Amazon|Apple|Meta|OpenAI|Anthropic|IBM|Oracle|SAP)\b",
            r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Inc|Corp|LLC|Ltd|Company|Co)\b",
        ],
        EntityType.TECHNOLOGY: [
            r"\b(?:Python|JavaScript|TypeScript|Rust|Go|Java|C\+\+|Ruby|Swift|Kotlin)\b",
            r"\b(?:React|Vue|Angular|Django|Flask|FastAPI|Node\.js|Express)\b",
            r"\b(?:PostgreSQL|MySQL|MongoDB|Redis|Elasticsearch|Neo4j)\b",
            r"\b(?:AWS|Azure|GCP|Kubernetes|Docker|Terraform)\b",
            r"\b(?:GPT-\d|Claude|LLM|AI|ML|NLP|RAG)\b",
        ],
    }

    def extract(self, text: str) -> List[Entity]:
        """Extract entities from text."""
        entities = []
        seen = set()

        for entity_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    name = match.group().strip()
                    key = (name.lower(), entity_type)
                    if key not in seen:
                        seen.add(key)
                        entities.append(Entity(name=name, entity_type=entity_type))

        # Extract capitalized phrases as potential entities
        cap_pattern = r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b"
        for match in re.finditer(cap_pattern, text):
            name = match.group().strip()
            if len(name) > 5:  # Skip short phrases
                key = (name.lower(), EntityType.OTHER)
                if key not in seen:
                    seen.add(key)
                    entities.append(Entity(name=name, entity_type=EntityType.OTHER))

        return entities


class TopicExtractor:
    """
    Extracts topics from text using keyword matching.

    For production use, consider topic modeling or LLM-based extraction.
    """

    # Common research topics
    TOPIC_KEYWORDS = {
        "artificial intelligence": ["AI", "artificial intelligence", "machine learning", "ML", "deep learning"],
        "natural language processing": ["NLP", "language model", "LLM", "GPT", "transformer"],
        "software engineering": ["software", "engineering", "development", "programming", "code"],
        "data science": ["data science", "analytics", "statistics", "data analysis"],
        "cloud computing": ["cloud", "AWS", "Azure", "GCP", "serverless"],
        "security": ["security", "cybersecurity", "encryption", "vulnerability"],
        "databases": ["database", "SQL", "NoSQL", "PostgreSQL", "MongoDB"],
        "web development": ["web", "frontend", "backend", "API", "REST"],
        "devops": ["DevOps", "CI/CD", "deployment", "infrastructure"],
        "research methodology": ["research", "methodology", "study", "analysis"],
    }

    def extract(self, text: str) -> List[str]:
        """Extract topics from text."""
        text_lower = text.lower()
        topics = []

        for topic, keywords in self.TOPIC_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    if topic not in topics:
                        topics.append(topic)
                    break

        return topics


class ResearchKnowledgeGraph:
    """
    Knowledge graph for research output storage and retrieval.

    Provides:
    - Claim storage with entity/topic extraction
    - Semantic search using embeddings
    - Provenance chain traversal
    - Contradiction detection
    - Session-based knowledge retrieval

    Example:
        from src.knowledge import ResearchKnowledgeGraph

        kg = ResearchKnowledgeGraph()

        # Add a claim
        claim_id = kg.add_claim(
            text="GPT-4 achieves 86.4% accuracy on the MMLU benchmark",
            confidence=0.95,
            source_url="https://openai.com/research/gpt-4",
            source_title="GPT-4 Technical Report",
            session_id="session-123"
        )

        # Find related claims
        results = kg.find_related_claims("language model performance benchmarks")

        # Check for contradictions
        contradictions = kg.find_contradictions(claim_id)
    """

    def __init__(
        self,
        storage: Optional[GraphStorageBackend] = None,
        embedding_fn: Optional[EmbeddingFunction] = None,
        entity_extractor: Optional[EntityExtractor] = None,
        topic_extractor: Optional[TopicExtractor] = None,
    ):
        """
        Initialize the knowledge graph.

        Args:
            storage: Storage backend (defaults to in-memory)
            embedding_fn: Function to compute text embeddings
            entity_extractor: Entity extraction component
            topic_extractor: Topic extraction component
        """
        self.storage = storage or MemoryGraphBackend()
        self.embedding_fn = embedding_fn or default_embedding_function
        self.entity_extractor = entity_extractor or EntityExtractor()
        self.topic_extractor = topic_extractor or TopicExtractor()

        # Statistics
        self.claims_added = 0
        self.queries_executed = 0

    def add_claim(
        self,
        text: str,
        confidence: float,
        source_url: str,
        source_title: str = "",
        publication_date: Optional[str] = None,
        agent_id: str = "",
        session_id: str = "",
        entities: Optional[List[Entity]] = None,
        topics: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Store a claim with full provenance and relationships.

        Args:
            text: The claim text
            confidence: Confidence score (0.0-1.0)
            source_url: URL of the source
            source_title: Title of the source
            publication_date: Publication date (ISO format)
            agent_id: Agent that extracted the claim
            session_id: Session identifier
            entities: Pre-extracted entities (auto-extracted if None)
            topics: Pre-extracted topics (auto-extracted if None)
            metadata: Additional metadata

        Returns:
            The claim ID
        """
        # Parse publication date
        pub_date = None
        if publication_date:
            from datetime import datetime
            try:
                pub_date = datetime.fromisoformat(publication_date.replace("Z", "+00:00"))
            except ValueError:
                pass

        # Auto-extract entities if not provided
        if entities is None:
            entities = self.entity_extractor.extract(text)

        # Auto-extract topics if not provided
        if topics is None:
            topics = self.topic_extractor.extract(text)

        # Compute embedding
        embedding = self.embedding_fn(text)

        # Create claim
        claim = KGClaim(
            text=text,
            confidence=confidence,
            source_url=source_url,
            source_title=source_title,
            publication_date=pub_date,
            entities=entities,
            topics=topics,
            agent_id=agent_id,
            session_id=session_id,
            embedding=embedding,
            metadata=metadata or {},
        )

        # Store claim
        claim_id = self.storage.store_claim(claim)
        self.claims_added += 1

        logger.debug(f"Added claim {claim_id}: {text[:50]}...")

        return claim_id

    def add_claim_object(self, claim: KGClaim) -> str:
        """
        Store a pre-constructed claim object.

        Args:
            claim: The claim to store

        Returns:
            The claim ID
        """
        # Ensure embedding exists
        if claim.embedding is None:
            claim.embedding = self.embedding_fn(claim.text)

        claim_id = self.storage.store_claim(claim)
        self.claims_added += 1
        return claim_id

    def get_claim(self, claim_id: str) -> Optional[KGClaim]:
        """Get a claim by ID."""
        return self.storage.get_claim(claim_id)

    def find_related_claims(
        self,
        query: str,
        max_hops: int = 2,
        min_confidence: float = 0.0,
        min_similarity: float = 0.3,
        limit: int = 10,
    ) -> KGQueryResult:
        """
        Find claims related by semantic similarity and entity co-occurrence.

        Args:
            query: Search query
            max_hops: Maximum entity hops for relationship expansion
            min_confidence: Minimum claim confidence
            min_similarity: Minimum semantic similarity
            limit: Maximum number of results

        Returns:
            KGQueryResult with matching claims, sources, and entities
        """
        start_time = time.time()
        self.queries_executed += 1

        # Compute query embedding
        query_embedding = self.embedding_fn(query)

        # Find semantically similar claims
        similar_claims = self.storage.find_claims_by_embedding(
            embedding=query_embedding,
            limit=limit * 2,  # Get more for filtering
            min_similarity=min_similarity,
        )

        # Filter by confidence
        filtered_claims = [
            (claim, score)
            for claim, score in similar_claims
            if claim.confidence >= min_confidence
        ]

        # Collect results
        claims = []
        sources = []
        entities_seen = set()
        all_entities = []
        source_urls_seen = set()

        for claim, similarity in filtered_claims[:limit]:
            claims.append({
                "id": claim.claim_id,
                "text": claim.text,
                "confidence": claim.confidence,
                "similarity": similarity,
                "agent_id": claim.agent_id,
                "session_id": claim.session_id,
            })

            # Collect source
            if claim.source_url not in source_urls_seen:
                source_urls_seen.add(claim.source_url)
                sources.append({
                    "url": claim.source_url,
                    "title": claim.source_title,
                    "publication_date": claim.publication_date.isoformat() if claim.publication_date else None,
                })

            # Collect entities
            for entity in claim.entities:
                key = (entity.name, entity.entity_type)
                if key not in entities_seen:
                    entities_seen.add(key)
                    all_entities.append(entity.to_dict())

        elapsed_ms = int((time.time() - start_time) * 1000)

        return KGQueryResult(
            claims=claims,
            sources=sources,
            related_entities=all_entities,
            provenance_chain=[],
            query_time_ms=elapsed_ms,
        )

    def get_provenance_chain(self, claim_id: str, max_depth: int = 5) -> List[Dict[str, Any]]:
        """
        Trace claim back to its sources.

        Args:
            claim_id: ID of the claim to trace
            max_depth: Maximum depth to traverse

        Returns:
            List of nodes in the provenance chain
        """
        return self.storage.get_provenance_chain(claim_id, max_depth)

    def find_contradictions(
        self,
        claim_id: str,
        max_similarity: float = 0.4,
    ) -> ContradictionResult:
        """
        Find claims that potentially contradict a given claim.

        Looks for claims on the same topic with low semantic similarity,
        which may indicate contradictory information.

        Args:
            claim_id: ID of the claim to check
            max_similarity: Maximum similarity for potential contradictions

        Returns:
            ContradictionResult with potentially contradicting claims
        """
        claim = self.storage.get_claim(claim_id)
        if not claim or not claim.embedding:
            return ContradictionResult(claim_id=claim_id)

        contradicting = []
        similarity_scores = {}
        shared_topics = set()

        # Find claims on same topics
        for topic in claim.topics:
            shared_topics.add(topic)
            topic_claims = self.storage.find_claims_by_topic(topic)

            for other in topic_claims:
                if other.claim_id == claim_id:
                    continue

                # Check if from different source
                if other.source_url == claim.source_url:
                    continue

                # Calculate similarity
                if other.embedding:
                    similarity = cosine_similarity(claim.embedding, other.embedding)

                    # Low similarity on same topic = potential contradiction
                    if similarity < max_similarity:
                        if other.claim_id not in similarity_scores:
                            contradicting.append({
                                "claim_id": other.claim_id,
                                "text": other.text,
                                "source_url": other.source_url,
                                "confidence": other.confidence,
                                "similarity": similarity,
                            })
                            similarity_scores[other.claim_id] = similarity

        # Sort by similarity (lowest = most likely contradiction)
        contradicting.sort(key=lambda x: x["similarity"])

        return ContradictionResult(
            claim_id=claim_id,
            contradicting_claims=contradicting[:10],
            similarity_scores=similarity_scores,
            shared_topics=list(shared_topics),
        )

    def find_claims_by_entity(
        self,
        entity_name: str,
        entity_type: Optional[EntityType] = None,
    ) -> List[KGClaim]:
        """Find claims mentioning a specific entity."""
        return self.storage.find_claims_by_entity(entity_name, entity_type)

    def find_claims_by_topic(self, topic: str) -> List[KGClaim]:
        """Find claims about a specific topic."""
        return self.storage.find_claims_by_topic(topic)

    def find_claims_by_session(self, session_id: str) -> List[KGClaim]:
        """Find all claims from a session."""
        return self.storage.find_claims_by_session(session_id)

    def get_related_claims(
        self,
        claim_id: str,
        max_hops: int = 2,
    ) -> List[Tuple[KGClaim, int]]:
        """Get claims related through shared entities/topics."""
        return self.storage.get_related_claims(claim_id, max_hops)

    def get_session_context(
        self,
        session_id: str,
        query: Optional[str] = None,
        limit: int = 10,
    ) -> str:
        """
        Get formatted context from session knowledge.

        Args:
            session_id: Session to get context from
            query: Optional query to filter/rank results
            limit: Maximum claims to include

        Returns:
            Formatted string of relevant knowledge
        """
        claims = self.find_claims_by_session(session_id)

        if query and claims:
            # Rank by relevance to query
            query_embedding = self.embedding_fn(query)
            ranked = []
            for claim in claims:
                if claim.embedding:
                    similarity = cosine_similarity(query_embedding, claim.embedding)
                    ranked.append((claim, similarity))
            ranked.sort(key=lambda x: x[1], reverse=True)
            claims = [c for c, _ in ranked[:limit]]
        else:
            claims = claims[:limit]

        if not claims:
            return "No relevant prior knowledge found."

        lines = ["Prior knowledge from this session:"]
        for claim in claims:
            lines.append(f"- {claim.text} (confidence: {claim.confidence:.2f}, source: {claim.source_title or claim.source_url})")

        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge graph statistics."""
        return {
            "claims_added": self.claims_added,
            "total_claims": self.storage.count_claims(),
            "total_sources": self.storage.count_sources(),
            "total_entities": self.storage.count_entities(),
            "queries_executed": self.queries_executed,
        }

    def close(self) -> None:
        """Close the knowledge graph."""
        self.storage.close()


# Default instance management
_default_kg: Optional[ResearchKnowledgeGraph] = None


def get_default_knowledge_graph() -> ResearchKnowledgeGraph:
    """Get or create the default knowledge graph."""
    global _default_kg
    if _default_kg is None:
        _default_kg = ResearchKnowledgeGraph()
    return _default_kg


def set_default_knowledge_graph(kg: ResearchKnowledgeGraph) -> None:
    """Set the default knowledge graph."""
    global _default_kg
    _default_kg = kg
