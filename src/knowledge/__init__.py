"""
Knowledge Graph Infrastructure Module.

Provides knowledge graph capabilities for research output storage,
semantic search, provenance tracking, and contradiction detection.

Version: 2.8.0
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
from .retriever import (
    HybridRetrieverConfig,
    HybridRetrievalResult,
    HybridRetriever,
)
from .embeddings import (
    DualEmbeddingConfig,
    SemanticEmbedder,
    StructuralEmbedder,
    DualEmbedder,
    EmbeddingCache,
)
from .bm25 import (
    BM25Config,
    BM25Index,
    reciprocal_rank_fusion,
    HybridBM25Retriever,
    # P1-002: Three-Way Hybrid
    ThreeWayHybridConfig,
    ThreeWayRetrievalResult,
    HybridRetrieverV2,
    TokenizerConfig,
    Tokenizer,
)
from .community import (
    # P2-001: Community Detection
    CommunityConfig,
    Community,
    CommunityHierarchy,
    CommunityDetectionResult,
    CommunityDetector,
    IGRAPH_AVAILABLE,
    LEIDENALG_AVAILABLE,
)
from .hnsw_index import (
    # P2-002: HNSW Index
    HNSWConfig,
    HNSWIndex,
    CapacityError,
    HNSWLIB_AVAILABLE,
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
    # Retriever (RETR-001)
    "HybridRetrieverConfig",
    "HybridRetrievalResult",
    "HybridRetriever",
    # Dual Embeddings (P1-001)
    "DualEmbeddingConfig",
    "SemanticEmbedder",
    "StructuralEmbedder",
    "DualEmbedder",
    "EmbeddingCache",
    # BM25 Hybrid (P1-002)
    "BM25Config",
    "BM25Index",
    "reciprocal_rank_fusion",
    "HybridBM25Retriever",
    # Three-Way Hybrid (P1-002)
    "ThreeWayHybridConfig",
    "ThreeWayRetrievalResult",
    "HybridRetrieverV2",
    "TokenizerConfig",
    "Tokenizer",
    # Community Detection (P2-001)
    "CommunityConfig",
    "Community",
    "CommunityHierarchy",
    "CommunityDetectionResult",
    "CommunityDetector",
    "IGRAPH_AVAILABLE",
    "LEIDENALG_AVAILABLE",
    # HNSW Index (P2-002)
    "HNSWConfig",
    "HNSWIndex",
    "CapacityError",
    "HNSWLIB_AVAILABLE",
]
