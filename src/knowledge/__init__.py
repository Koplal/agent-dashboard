"""
Knowledge Graph Infrastructure Module.

Provides knowledge graph capabilities for research output storage,
semantic search, provenance tracking, and contradiction detection.

Version: 2.6.0
"""

from .graph import (
    # Enums
    EntityType,
    RelationType,
    # Dataclasses
    Entity,
    Source,
    KGClaim,
    KGQueryResult,
    ContradictionResult,
    # Abstract base
    GraphStorageBackend,
)
from .storage import (
    MemoryGraphBackend,
    SQLiteGraphBackend,
    cosine_similarity,
)
from .manager import (
    ResearchKnowledgeGraph,
    EntityExtractor,
    TopicExtractor,
    EmbeddingFunction,
    default_embedding_function,
    get_default_knowledge_graph,
    set_default_knowledge_graph,
)
from .agent import (
    KGEnhancedResearchAgent,
    ResearchClaim,
    ResearchOutput,
    ResearchAgentProtocol,
    MockResearchAgent,
)

__all__ = [
    # Enums
    "EntityType",
    "RelationType",
    # Dataclasses
    "Entity",
    "Source",
    "KGClaim",
    "KGQueryResult",
    "ContradictionResult",
    # Storage
    "GraphStorageBackend",
    "MemoryGraphBackend",
    "SQLiteGraphBackend",
    "cosine_similarity",
    # Manager
    "ResearchKnowledgeGraph",
    "EntityExtractor",
    "TopicExtractor",
    "EmbeddingFunction",
    "default_embedding_function",
    "get_default_knowledge_graph",
    "set_default_knowledge_graph",
    # Agent
    "KGEnhancedResearchAgent",
    "ResearchClaim",
    "ResearchOutput",
    "ResearchAgentProtocol",
    "MockResearchAgent",
]
