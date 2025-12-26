"""
Knowledge Graph Core Types and Interface.

Provides dataclasses and abstract interface for knowledge graph operations,
enabling provenance tracking, semantic search, and contradiction detection.

Version: 2.6.0
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple


def utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


class EntityType(str, Enum):
    """Types of entities that can be extracted from claims.

    Includes both general entity types and code-specific types
    for source code analysis use cases.
    """
    # General entity types
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    DATE = "date"
    CONCEPT = "concept"
    TECHNOLOGY = "technology"
    PRODUCT = "product"
    EVENT = "event"
    METRIC = "metric"
    OTHER = "other"
    # Code entity types (KG-001)
    FILE = "file"
    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"
    VARIABLE = "variable"
    DEPENDENCY = "dependency"


class RelationType(str, Enum):
    """Types of relationships between nodes."""
    SOURCED_FROM = "sourced_from"
    DERIVED_FROM = "derived_from"
    MENTIONS = "mentions"
    ABOUT = "about"
    GENERATED_IN = "generated_in"
    CONTRADICTS = "contradicts"
    SUPPORTS = "supports"
    RELATED_TO = "related_to"


@dataclass
class Entity:
    """
    Entity extracted from a claim.

    Attributes:
        name: Entity name/label
        entity_type: Type classification
        metadata: Additional entity metadata
        valid_from: Start of temporal validity (KG-002)
        valid_to: End of temporal validity (KG-002)
        source_location: Source code location, e.g. "file.py:42" (KG-002)
    """
    name: str
    entity_type: EntityType = EntityType.OTHER
    metadata: Dict[str, Any] = field(default_factory=dict)
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    source_location: Optional[str] = None

    def is_valid(self, as_of: Optional[datetime] = None) -> bool:
        """Check if entity is valid at a given point in time.

        Args:
            as_of: Datetime to check validity at. Defaults to current UTC time.
                   Timezone-naive datetimes are treated as UTC.

        Returns:
            True if entity is valid at the specified time, False otherwise.
            Entities without temporal bounds are always valid.
            Boundaries are inclusive (valid_from <= as_of <= valid_to).

        Note:
            - None for valid_from means 'valid since the beginning of time'
            - None for valid_to means 'valid indefinitely into the future'
        """
        if as_of is None:
            as_of = utc_now()
        elif as_of.tzinfo is None:
            # Treat naive datetimes as UTC to avoid comparison errors
            as_of = as_of.replace(tzinfo=timezone.utc)

        # No bounds means always valid
        if self.valid_from is None and self.valid_to is None:
            return True

        # Normalize bounds to UTC if naive
        valid_from = self.valid_from
        if valid_from is not None and valid_from.tzinfo is None:
            valid_from = valid_from.replace(tzinfo=timezone.utc)

        valid_to = self.valid_to
        if valid_to is not None and valid_to.tzinfo is None:
            valid_to = valid_to.replace(tzinfo=timezone.utc)

        # Check lower bound (inclusive)
        if valid_from is not None and as_of < valid_from:
            return False

        # Check upper bound (inclusive)
        if valid_to is not None and as_of > valid_to:
            return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": self.entity_type.value,
            "metadata": self.metadata,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "source_location": self.source_location,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Entity":
        """Create from dictionary."""
        valid_from = None
        if data.get("valid_from"):
            valid_from = datetime.fromisoformat(data["valid_from"])

        valid_to = None
        if data.get("valid_to"):
            valid_to = datetime.fromisoformat(data["valid_to"])

        return cls(
            name=data["name"],
            entity_type=EntityType(data.get("type", "other")),
            metadata=data.get("metadata", {}),
            valid_from=valid_from,
            valid_to=valid_to,
            source_location=data.get("source_location"),
        )


@dataclass
class Source:
    """
    Source document for a claim.

    Attributes:
        url: Source URL (unique identifier)
        title: Source title
        publication_date: When source was published
        author: Author name(s)
        domain: Source domain
        last_accessed: When source was last accessed
        metadata: Additional source metadata
    """
    url: str
    title: str = ""
    publication_date: Optional[datetime] = None
    author: str = ""
    domain: str = ""
    last_accessed: datetime = field(default_factory=utc_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "title": self.title,
            "publication_date": self.publication_date.isoformat() if self.publication_date else None,
            "author": self.author,
            "domain": self.domain,
            "last_accessed": self.last_accessed.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Source":
        """Create from dictionary."""
        pub_date = None
        if data.get("publication_date"):
            pub_date = datetime.fromisoformat(data["publication_date"])

        last_accessed = utc_now()
        if data.get("last_accessed"):
            last_accessed = datetime.fromisoformat(data["last_accessed"])

        return cls(
            url=data["url"],
            title=data.get("title", ""),
            publication_date=pub_date,
            author=data.get("author", ""),
            domain=data.get("domain", ""),
            last_accessed=last_accessed,
            metadata=data.get("metadata", {}),
        )


@dataclass
class KGClaim:
    """
    Claim to be stored in knowledge graph.

    Attributes:
        text: The claim text
        confidence: Confidence score (0.0-1.0)
        source_url: URL of the source
        source_title: Title of the source
        publication_date: When source was published
        entities: Entities mentioned in claim
        topics: Topics the claim relates to
        agent_id: Agent that extracted the claim
        session_id: Session where claim was extracted
        claim_id: Unique identifier (auto-generated)
        embedding: Vector embedding for semantic search
        created_at: When claim was created
        metadata: Additional claim metadata
    """
    text: str
    confidence: float
    source_url: str
    source_title: str = ""
    publication_date: Optional[datetime] = None
    entities: List[Entity] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    agent_id: str = ""
    session_id: str = ""
    claim_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    embedding: Optional[List[float]] = None
    created_at: datetime = field(default_factory=utc_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "claim_id": self.claim_id,
            "text": self.text,
            "confidence": self.confidence,
            "source_url": self.source_url,
            "source_title": self.source_title,
            "publication_date": self.publication_date.isoformat() if self.publication_date else None,
            "entities": [e.to_dict() for e in self.entities],
            "topics": self.topics,
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "embedding": self.embedding,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KGClaim":
        """Create from dictionary."""
        pub_date = None
        if data.get("publication_date"):
            pub_date = datetime.fromisoformat(data["publication_date"])

        created_at = utc_now()
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])

        entities = [
            Entity.from_dict(e) if isinstance(e, dict) else e
            for e in data.get("entities", [])
        ]

        return cls(
            claim_id=data.get("claim_id", str(uuid.uuid4())),
            text=data["text"],
            confidence=data.get("confidence", 0.0),
            source_url=data["source_url"],
            source_title=data.get("source_title", ""),
            publication_date=pub_date,
            entities=entities,
            topics=data.get("topics", []),
            agent_id=data.get("agent_id", ""),
            session_id=data.get("session_id", ""),
            embedding=data.get("embedding"),
            created_at=created_at,
            metadata=data.get("metadata", {}),
        )


@dataclass
class KGQueryResult:
    """
    Result from knowledge graph query.

    Attributes:
        claims: Matching claims with scores
        sources: Sources for matched claims
        related_entities: Entities mentioned across claims
        provenance_chain: Provenance trace for claims
        query_time_ms: Query execution time
    """
    claims: List[Dict[str, Any]] = field(default_factory=list)
    sources: List[Dict[str, Any]] = field(default_factory=list)
    related_entities: List[Dict[str, Any]] = field(default_factory=list)
    provenance_chain: List[Dict[str, Any]] = field(default_factory=list)
    query_time_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "claims": self.claims,
            "sources": self.sources,
            "related_entities": self.related_entities,
            "provenance_chain": self.provenance_chain,
            "query_time_ms": self.query_time_ms,
        }


@dataclass
class ContradictionResult:
    """
    Result from contradiction detection.

    Attributes:
        claim_id: ID of the original claim
        contradicting_claims: Claims that potentially contradict
        similarity_scores: Semantic similarity scores
        shared_topics: Topics shared between claims
    """
    claim_id: str
    contradicting_claims: List[Dict[str, Any]] = field(default_factory=list)
    similarity_scores: Dict[str, float] = field(default_factory=dict)
    shared_topics: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "claim_id": self.claim_id,
            "contradicting_claims": self.contradicting_claims,
            "similarity_scores": self.similarity_scores,
            "shared_topics": self.shared_topics,
        }


class GraphStorageBackend(ABC):
    """
    Abstract base class for knowledge graph storage backends.

    Implementations must provide methods for storing, querying,
    and traversing the knowledge graph.
    """

    @abstractmethod
    def store_claim(self, claim: KGClaim) -> str:
        """
        Store a claim with its relationships.

        Args:
            claim: The claim to store

        Returns:
            The claim ID
        """
        pass

    @abstractmethod
    def get_claim(self, claim_id: str) -> Optional[KGClaim]:
        """Get a claim by ID."""
        pass

    @abstractmethod
    def store_source(self, source: Source) -> str:
        """Store or update a source."""
        pass

    @abstractmethod
    def get_source(self, url: str) -> Optional[Source]:
        """Get a source by URL."""
        pass

    @abstractmethod
    def add_relationship(
        self,
        from_id: str,
        to_id: str,
        relation_type: RelationType,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Add a relationship between nodes."""
        pass

    @abstractmethod
    def find_claims_by_embedding(
        self,
        embedding: List[float],
        limit: int = 10,
        min_similarity: float = 0.5,
    ) -> List[Tuple[KGClaim, float]]:
        """Find claims by embedding similarity."""
        pass

    @abstractmethod
    def find_claims_by_entity(
        self,
        entity_name: str,
        entity_type: Optional[EntityType] = None,
    ) -> List[KGClaim]:
        """Find claims mentioning an entity."""
        pass

    @abstractmethod
    def find_claims_by_topic(self, topic: str) -> List[KGClaim]:
        """Find claims about a topic."""
        pass

    @abstractmethod
    def find_claims_by_session(self, session_id: str) -> List[KGClaim]:
        """Find claims from a session."""
        pass

    @abstractmethod
    def get_provenance_chain(self, claim_id: str, max_depth: int = 5) -> List[Dict[str, Any]]:
        """Trace claim back to its sources."""
        pass

    @abstractmethod
    def get_related_claims(
        self,
        claim_id: str,
        max_hops: int = 2,
    ) -> List[Tuple[KGClaim, int]]:
        """Get claims related through shared entities."""
        pass

    @abstractmethod
    def count_claims(self) -> int:
        """Count total claims."""
        pass

    @abstractmethod
    def count_sources(self) -> int:
        """Count total sources."""
        pass

    @abstractmethod
    def count_entities(self) -> int:
        """Count unique entities."""
        pass

    def close(self) -> None:
        """Close any open connections."""
        pass
