"""
Hybrid Vector-Graph Retriever.

Combines vector similarity search with graph-based traversal for
contextually relevant retrieval from the knowledge graph.

Implements RETR-001 with:
- HybridRetrieverConfig for tunable parameters
- HybridRetrievalResult for scored results with provenance
- HybridRetriever class combining vector and graph signals

Version: 2.6.0
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Callable, Set

from .graph import (
    GraphStorageBackend,
    KGClaim,
    Entity,
    EntityType,
)
from .storage import cosine_similarity


def _validate_config(
    vector_weight: float,
    graph_weight: float,
    max_hops: int,
    min_similarity: float,
    min_graph_score: float,
) -> None:
    """Validate configuration parameters."""
    if vector_weight < 0:
        raise ValueError("vector_weight must be non-negative")
    if graph_weight < 0:
        raise ValueError("graph_weight must be non-negative")
    if max_hops <= 0:
        raise ValueError("max_hops must be positive")
    if min_similarity < 0 or min_similarity > 1:
        raise ValueError("min_similarity must be between 0.0 and 1.0")
    if min_graph_score < 0 or min_graph_score > 1:
        raise ValueError("min_graph_score must be between 0.0 and 1.0")


@dataclass
class HybridRetrieverConfig:
    """Configuration for hybrid retrieval.

    Attributes:
        vector_weight: Weight for vector similarity score (default 0.6)
        graph_weight: Weight for graph-based score (default 0.4)
        max_hops: Maximum hops for graph expansion (default 2)
        min_similarity: Minimum vector similarity threshold (default 0.3)
        min_graph_score: Minimum graph score threshold (default 0.1)
        temporal_filter: Whether to filter by entity validity (default False)
        as_of: Datetime for temporal filtering (default None = current time)
    """
    vector_weight: float = 0.6
    graph_weight: float = 0.4
    max_hops: int = 2
    min_similarity: float = 0.3
    min_graph_score: float = 0.1
    temporal_filter: bool = False
    as_of: Optional[datetime] = None

    def __post_init__(self):
        """Validate configuration after initialization."""
        _validate_config(
            self.vector_weight,
            self.graph_weight,
            self.max_hops,
            self.min_similarity,
            self.min_graph_score,
        )


@dataclass
class HybridRetrievalResult:
    """Result from hybrid retrieval.

    Attributes:
        claim: The retrieved KGClaim
        combined_score: Fused score from vector and graph components
        vector_score: Score from vector similarity (0 if not found via vector)
        graph_score: Score from graph traversal (0 if not found via graph)
        retrieval_path: How claim was found ("vector", "graph", or "both")
        hop_distance: Graph hop distance (0 for direct vector match)
    """
    claim: KGClaim
    combined_score: float
    vector_score: float
    graph_score: float
    retrieval_path: str
    hop_distance: int

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "claim": self.claim.to_dict(),
            "combined_score": self.combined_score,
            "vector_score": self.vector_score,
            "graph_score": self.graph_score,
            "retrieval_path": self.retrieval_path,
            "hop_distance": self.hop_distance,
        }


# Type alias for embedding function
EmbeddingFunction = Callable[[str], List[float]]


class HybridRetriever:
    """Combines vector and graph retrieval for enhanced results.

    Provides:
    - Vector similarity search using embeddings
    - Graph expansion via shared entities
    - Score fusion with configurable weights
    - Temporal filtering for entity validity
    - Batch query support

    Example:
        from src.knowledge import HybridRetriever, MemoryGraphBackend

        retriever = HybridRetriever(
            storage=backend,
            embedding_fn=my_embedding_fn,
        )

        results = retriever.retrieve("machine learning frameworks", limit=10)
        for r in results:
            print(f"{r.claim.text}: {r.combined_score:.2f} ({r.retrieval_path})")
    """

    def __init__(
        self,
        storage: GraphStorageBackend,
        embedding_fn: EmbeddingFunction,
        config: Optional[HybridRetrieverConfig] = None,
    ):
        """Initialize the hybrid retriever.

        Args:
            storage: Knowledge graph storage backend
            embedding_fn: Function to compute text embeddings
            config: Retrieval configuration (uses defaults if None)
        """
        self.storage = storage
        self.embedding_fn = embedding_fn
        self.config = config or HybridRetrieverConfig()

    def retrieve(
        self,
        query: str,
        limit: int = 10,
        config: Optional[HybridRetrieverConfig] = None,
    ) -> List[HybridRetrievalResult]:
        """Retrieve claims using hybrid vector+graph approach.

        Args:
            query: Search query text
            limit: Maximum results to return
            config: Override config for this query (optional)

        Returns:
            List of HybridRetrievalResult sorted by combined_score descending
        """
        if not query or not query.strip():
            return []

        # Use override config or default
        cfg = config or self.config

        # Step 1: Vector search (pass config for min_similarity)
        query_embedding = self.embedding_fn(query)
        vector_results = self._vector_search(query_embedding, limit * 2, cfg)

        # Step 2: Graph expansion from vector seeds (pass config for temporal filter)
        seed_claims = [claim for claim, _ in vector_results]
        graph_results = self._graph_expand(seed_claims, cfg)

        # Step 3: Build score dictionaries
        vector_scores: Dict[str, float] = {
            claim.claim_id: score for claim, score in vector_results
        }

        graph_scores: Dict[str, Tuple[int, float]] = {}
        for claim, hop_distance, score in graph_results:
            if claim.claim_id not in graph_scores:
                graph_scores[claim.claim_id] = (hop_distance, score)

        # Step 4: Fuse scores (pass config for weights)
        fused = self._fuse_scores(vector_scores, graph_scores, cfg)

        # Step 5: Get full claim objects and sort
        results = []
        for claim_id, result_stub in fused.items():
            # Get full claim from storage
            claim = self.storage.get_claim(claim_id)
            if claim:
                result = HybridRetrievalResult(
                    claim=claim,
                    combined_score=result_stub.combined_score,
                    vector_score=result_stub.vector_score,
                    graph_score=result_stub.graph_score,
                    retrieval_path=result_stub.retrieval_path,
                    hop_distance=result_stub.hop_distance,
                )
                results.append(result)

        # Sort by combined score descending
        results.sort(key=lambda r: r.combined_score, reverse=True)

        return results[:limit]

    def retrieve_batch(
        self,
        queries: List[str],
        limit: int = 10,
    ) -> Dict[str, List[HybridRetrievalResult]]:
        """Retrieve for multiple queries.

        Args:
            queries: List of search queries
            limit: Maximum results per query

        Returns:
            Dictionary mapping each query to its results
        """
        if not queries:
            return {}

        results = {}
        for query in queries:
            results[query] = self.retrieve(query, limit)

        return results

    def _vector_search(
        self,
        query_embedding: List[float],
        limit: int,
        config: Optional[HybridRetrieverConfig] = None,
    ) -> List[Tuple[KGClaim, float]]:
        """Find claims by vector similarity.

        Args:
            query_embedding: Query embedding vector
            limit: Maximum results
            config: Configuration to use (defaults to self.config)

        Returns:
            List of (claim, similarity) tuples sorted by similarity descending
        """
        cfg = config or self.config
        return self.storage.find_claims_by_embedding(
            embedding=query_embedding,
            limit=limit,
            min_similarity=cfg.min_similarity,
        )

    def _graph_expand(
        self,
        seed_claims: List[KGClaim],
        config: Optional[HybridRetrieverConfig] = None,
    ) -> List[Tuple[KGClaim, int, float]]:
        """Expand from seed claims via entity relationships.

        Args:
            seed_claims: Starting claims for expansion
            config: Configuration to use (defaults to self.config)

        Returns:
            List of (claim, hop_distance, score) tuples
        """
        if not seed_claims:
            return []

        cfg = config or self.config

        # Get temporal filter settings from config
        temporal_filter = cfg.temporal_filter
        as_of = cfg.as_of
        if temporal_filter and as_of is None:
            as_of = datetime.now(timezone.utc)

        max_hops = cfg.max_hops
        min_graph_score = cfg.min_graph_score

        # Collect seed entities
        seed_ids = {c.claim_id for c in seed_claims}
        seed_entities: Set[Tuple[str, EntityType]] = set()

        for claim in seed_claims:
            for entity in claim.entities:
                # Apply temporal filter if enabled
                if temporal_filter:
                    if not entity.is_valid(as_of):
                        continue
                seed_entities.add((entity.name, entity.entity_type))

        # BFS expansion
        results: List[Tuple[KGClaim, int, float]] = []
        visited_claims: Set[str] = set(seed_ids)
        current_entities = seed_entities
        current_hop = 1

        while current_hop <= max_hops and current_entities:
            next_entities: Set[Tuple[str, EntityType]] = set()

            for entity_name, entity_type in current_entities:
                # Find claims mentioning this entity
                claims = self.storage.find_claims_by_entity(entity_name, entity_type)

                for claim in claims:
                    if claim.claim_id in visited_claims:
                        continue

                    visited_claims.add(claim.claim_id)

                    # Calculate entity overlap score
                    claim_entities = {
                        (e.name, e.entity_type) for e in claim.entities
                        if not temporal_filter or e.is_valid(as_of)
                    }
                    overlap = len(seed_entities & claim_entities)
                    max_entities = max(len(seed_entities), len(claim_entities), 1)
                    overlap_ratio = overlap / max_entities

                    # Graph score = 1/(1+hop_distance) * overlap_ratio
                    graph_score = (1.0 / (1.0 + current_hop)) * overlap_ratio

                    if graph_score >= min_graph_score:
                        results.append((claim, current_hop, graph_score))

                    # Add claim's entities to next hop
                    for entity in claim.entities:
                        if temporal_filter and not entity.is_valid(as_of):
                            continue
                        next_entities.add((entity.name, entity.entity_type))

            current_entities = next_entities - seed_entities
            current_hop += 1

        return results

    def _fuse_scores(
        self,
        vector_results: Dict[str, float],
        graph_results: Dict[str, Tuple[int, float]],
        config: Optional[HybridRetrieverConfig] = None,
    ) -> Dict[str, HybridRetrievalResult]:
        """Fuse vector and graph scores into combined results.

        Args:
            vector_results: claim_id -> vector similarity score
            graph_results: claim_id -> (hop_distance, graph_score)
            config: Configuration to use (defaults to self.config)

        Returns:
            Dictionary of claim_id -> HybridRetrievalResult stub
        """
        cfg = config or self.config
        all_claim_ids = set(vector_results.keys()) | set(graph_results.keys())
        fused: Dict[str, HybridRetrievalResult] = {}

        for claim_id in all_claim_ids:
            vector_score = vector_results.get(claim_id, 0.0)
            hop_distance, graph_score = graph_results.get(claim_id, (0, 0.0))

            # Determine retrieval path
            has_vector = claim_id in vector_results
            has_graph = claim_id in graph_results

            if has_vector and has_graph:
                retrieval_path = "both"
            elif has_vector:
                retrieval_path = "vector"
            else:
                retrieval_path = "graph"

            # Calculate combined score using config weights
            combined_score = (
                cfg.vector_weight * vector_score +
                cfg.graph_weight * graph_score
            )

            # Create result stub (claim will be fetched later)
            fused[claim_id] = HybridRetrievalResult(
                claim=None,  # type: ignore  # Will be populated later
                combined_score=combined_score,
                vector_score=vector_score,
                graph_score=graph_score,
                retrieval_path=retrieval_path,
                hop_distance=hop_distance if has_graph else 0,
            )

        return fused
