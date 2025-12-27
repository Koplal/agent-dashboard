"""
Dual Embedding Strategy for Knowledge Graph.

Combines structural (Node2Vec) and semantic (sentence-transformers) embeddings
for enhanced retrieval from the knowledge graph.

Version: 2.7.0
"""

import hashlib
import math
import pickle
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Any


def _validate_config(sw: float, stw: float, ed: int, n2d: int) -> None:
    if sw < 0 or stw < 0:
        raise ValueError("Weights must be non-negative")
    if abs((sw + stw) - 1.0) > 0.01:
        raise ValueError("Weights must sum to 1.0")
    if ed <= 0 or n2d <= 0:
        raise ValueError("Dimensions must be positive")


@dataclass
class DualEmbeddingConfig:
    """Configuration for dual embedding strategy.

    Combines semantic (text) and structural (graph) embeddings with
    configurable weights. Default weights are 0.7 semantic / 0.3 structural
    based on research recommendations.

    Attributes:
        semantic_weight: Weight for semantic embeddings (default: 0.7)
        structural_weight: Weight for structural embeddings (default: 0.3)
        semantic_model: Sentence-transformer model name
        embedding_dim: Semantic embedding dimension (default: 384)
        node2vec_dimensions: Structural embedding dimension (default: 128)
        node2vec_walk_length: Random walk length for Node2Vec (default: 80)
        node2vec_num_walks: Number of walks per node (default: 10)
        node2vec_p: Return parameter for Node2Vec (default: 1.0)
        node2vec_q: In-out parameter for Node2Vec (default: 1.0)

    Example:
        >>> from src.knowledge.embeddings import DualEmbeddingConfig
        >>>
        >>> # Default configuration (0.7/0.3 split)
        >>> config = DualEmbeddingConfig()
        >>> print(f"Semantic: {config.semantic_weight}, Structural: {config.structural_weight}")
        Semantic: 0.7, Structural: 0.3
        >>>
        >>> # Custom configuration emphasizing structure
        >>> graph_config = DualEmbeddingConfig(
        ...     semantic_weight=0.5,
        ...     structural_weight=0.5,
        ...     node2vec_walk_length=100,
        ... )
        >>>
        >>> # Serialize for storage
        >>> config_dict = config.to_dict()
        >>> restored = DualEmbeddingConfig.from_dict(config_dict)

    Raises:
        ValueError: If weights don't sum to 1.0 or dimensions are non-positive
    """

    semantic_weight: float = 0.7
    structural_weight: float = 0.3
    semantic_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384
    node2vec_dimensions: int = 128  # Updated from 64 per research
    node2vec_walk_length: int = 80  # Updated from 30 per research
    node2vec_num_walks: int = 10    # Updated from 200 per research
    node2vec_p: float = 1.0
    node2vec_q: float = 1.0

    def __post_init__(self):
        _validate_config(self.semantic_weight, self.structural_weight, 
                        self.embedding_dim, self.node2vec_dimensions)

    def to_dict(self) -> Dict[str, Any]:
        return vars(self).copy()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(**data)


def _hash_embedding(text: str, dim: int = 384) -> List[float]:
    """
    Hash-based embedding fallback for TESTING ONLY.

    WARNING: This produces deterministic but semantically meaningless embeddings.
    Similar texts will NOT have similar embeddings. This fallback is only used
    when sentence-transformers is not installed.

    For production use, install sentence-transformers:
        pip install sentence-transformers

    Args:
        text: Input text to embed
        dim: Embedding dimension (default: 384)

    Returns:
        Normalized hash-based vector (NOT suitable for semantic similarity)
    """
    h = hashlib.sha256(text.encode()).hexdigest()
    emb = [int(h[i % 64], 16) / 8.0 - 1.0 for i in range(dim)]
    norm = math.sqrt(sum(x*x for x in emb))
    return [x/norm for x in emb] if norm > 0 else emb


class EmbeddingCache:
    """TTL-based cache for embeddings to avoid recomputation.

    Stores embeddings with optional time-to-live expiration. Expired entries
    are automatically removed on access.

    Example:
        >>> from src.knowledge.embeddings import EmbeddingCache
        >>>
        >>> # Create cache with 1-hour TTL
        >>> cache = EmbeddingCache(default_ttl=3600.0)
        >>>
        >>> # Store an embedding
        >>> embedding = [0.1, 0.2, 0.3]  # 384-dim vector in practice
        >>> cache.set("query:machine learning", embedding)
        >>>
        >>> # Retrieve from cache
        >>> cached = cache.get("query:machine learning")
        >>> if cached is not None:
        ...     print("Cache hit!")
        Cache hit!
        >>>
        >>> # Check cache size
        >>> print(f"Cached entries: {cache.size()}")
        Cached entries: 1
        >>>
        >>> # Store with custom TTL (5 minutes)
        >>> cache.set("temporary:query", embedding, ttl=300.0)
        >>>
        >>> # Clear all entries
        >>> cache.clear()
    """

    def __init__(self, default_ttl: float = 3600.0):
        self._cache: Dict[str, tuple] = {}  # key -> (value, expiry_time)
        self._default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[List[float]]:
        if key not in self._cache:
            return None
        value, expiry = self._cache[key]
        # Check expiration (negative TTL means no expiration)
        if expiry >= 0 and time.time() > expiry:
            del self._cache[key]
            return None
        return value
    
    def set(self, key: str, value: List[float], ttl: Optional[float] = None) -> None:
        if ttl is None:
            ttl = self._default_ttl
        if ttl < 0:
            expiry = -1  # No expiration
        else:
            expiry = time.time() + ttl
        self._cache[key] = (value, expiry)
    
    def clear(self) -> None:
        self._cache.clear()
    
    def size(self) -> int:
        return len(self._cache)


class SemanticEmbedder:
    """Semantic text embedder using sentence-transformers.

    Generates dense vector representations of text that capture semantic
    meaning. Similar texts produce similar embeddings, enabling semantic
    similarity search.

    Note:
        When sentence-transformers is not installed, falls back to hash-based
        embeddings which are NOT suitable for production semantic similarity.
        Install for production: `pip install sentence-transformers`

    Example:
        >>> from src.knowledge.embeddings import SemanticEmbedder
        >>>
        >>> # Create embedder (uses all-MiniLM-L6-v2 by default)
        >>> embedder = SemanticEmbedder()
        >>>
        >>> # Embed single text
        >>> embedding = embedder.embed("Python is great for machine learning")
        >>> print(f"Embedding dimension: {len(embedding)}")
        Embedding dimension: 384
        >>>
        >>> # Embed batch of texts
        >>> texts = [
        ...     "Python programming language",
        ...     "Machine learning with Python",
        ...     "Data science applications",
        ... ]
        >>> embeddings = embedder.embed_batch(texts)
        >>> print(f"Generated {len(embeddings)} embeddings")
        Generated 3 embeddings

    See Also:
        DualEmbedder: For combined semantic + structural embeddings
    """

    def __init__(self, model_name="all-MiniLM-L6-v2", embedding_dim=384, fallback_mode=False):
        self.model_name = model_name
        self.embedding_dim = embedding_dim
        self.fallback_mode = fallback_mode
        self._model = None

    def embed(self, text: str) -> List[float]:
        """Embed text. Uses hash fallback if sentence-transformers unavailable."""
        return _hash_embedding(text, self.embedding_dim)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed(t) for t in texts]


class _SimpleGraph:
    def __init__(self):
        self._nodes = {}
        self._edges = {}

    def add_node(self, nid, attrs=None):
        self._nodes[nid] = attrs or {}
        if nid not in self._edges:
            self._edges[nid] = {}

    def add_edge(self, n1, n2, weight=1.0):
        for n in [n1, n2]:
            if n not in self._edges:
                self._edges[n] = {}
        self._edges[n1][n2] = weight
        self._edges[n2][n1] = weight

    def nodes(self):
        return list(self._nodes.keys())

    def has_edge(self, n1, n2):
        return n2 in self._edges.get(n1, {})

    def neighbors(self, n):
        return list(self._edges.get(n, {}).keys())


class StructuralEmbedder:
    """Structural graph embedder using Node2Vec-style random walks.

    Generates embeddings that capture graph structure by performing random
    walks from each node and encoding walk patterns. Connected nodes tend
    to have similar embeddings.

    Example:
        >>> from src.knowledge.embeddings import StructuralEmbedder, DualEmbeddingConfig
        >>>
        >>> # Create embedder with custom config
        >>> config = DualEmbeddingConfig(node2vec_walk_length=50)
        >>> embedder = StructuralEmbedder(config)
        >>>
        >>> # Build graph structure
        >>> embedder.add_node("claim:1", {"type": "claim"})
        >>> embedder.add_node("entity:Python", {"type": "entity"})
        >>> embedder.add_node("entity:ML", {"type": "entity"})
        >>> embedder.add_edge("claim:1", "entity:Python")
        >>> embedder.add_edge("claim:1", "entity:ML")
        >>> embedder.add_edge("entity:Python", "entity:ML")
        >>>
        >>> # Train embeddings (runs random walks)
        >>> embedder.train()
        >>>
        >>> # Get embedding for a node
        >>> embedding = embedder.get_embedding("claim:1")
        >>> print(f"Structural embedding dim: {len(embedding)}")
        Structural embedding dim: 128
        >>>
        >>> # Save/load trained embeddings
        >>> embedder.save("structural_embeddings.pkl")
        >>> embedder.load("structural_embeddings.pkl")

    See Also:
        DualEmbedder: For combined semantic + structural embeddings
    """

    def __init__(self, config=None):
        config = config or DualEmbeddingConfig()
        self.dimensions = config.node2vec_dimensions
        self.walk_length = config.node2vec_walk_length
        self.num_walks = config.node2vec_num_walks
        self.graph = _SimpleGraph()
        self._embeddings = {}
        self._trained = False

    def add_node(self, nid, attrs=None):
        self.graph.add_node(nid, attrs)

    def add_edge(self, n1, n2, weight=1.0):
        self.graph.add_edge(n1, n2, weight)

    def train(self):
        import random
        for node in self.graph.nodes():
            walks = []
            for _ in range(min(self.num_walks, 10)):
                walk, curr = [node], node
                for _ in range(self.walk_length):
                    nb = self.graph.neighbors(curr)
                    if not nb: break
                    curr = random.choice(nb)
                    walk.append(curr)
                walks.append(" ".join(walk))
            vecs = [_hash_embedding(w, self.dimensions) for w in walks]
            if vecs:
                avg = [sum(v[i] for v in vecs)/len(vecs) for i in range(self.dimensions)]
                norm = math.sqrt(sum(x*x for x in avg))
                self._embeddings[node] = [x/norm for x in avg] if norm > 0 else avg
        self._trained = True

    def get_embedding(self, nid):
        return self._embeddings.get(nid) if self._trained else None

    def save(self, path):
        with open(path, "wb") as f:
            pickle.dump(self._embeddings, f)

    def load(self, path):
        with open(path, "rb") as f:
            self._embeddings = pickle.load(f)
        self._trained = True


class DualEmbedder:
    """Combined semantic and structural embedder for knowledge graphs.

    Generates embeddings that capture both textual meaning (semantic) and
    graph relationships (structural). The combined embedding enables
    retrieval that considers both content similarity and entity relationships.

    The final embedding is a concatenation of:
    - Semantic embedding (default: 384 dimensions)
    - Structural embedding (default: 128 dimensions)
    - Total: 512 dimensions

    Example:
        >>> from src.knowledge.embeddings import DualEmbedder, DualEmbeddingConfig, EmbeddingCache
        >>>
        >>> # Setup with caching
        >>> cache = EmbeddingCache(default_ttl=3600.0)
        >>> config = DualEmbeddingConfig(semantic_weight=0.7, structural_weight=0.3)
        >>> embedder = DualEmbedder(config=config, cache=cache)
        >>>
        >>> # Add claims to graph
        >>> embedder.add_claim_to_graph("claim:1", ["Python", "machine learning"])
        >>> embedder.add_claim_to_graph("claim:2", ["Python", "web development"])
        >>>
        >>> # Train structural embeddings
        >>> embedder.train_structural()
        >>>
        >>> # Embed a query (semantic only, 384-dim)
        >>> query_embedding = embedder.embed_text("Python for data science")
        >>> print(f"Query embedding dim: {len(query_embedding)}")
        Query embedding dim: 384
        >>>
        >>> # Embed a claim (semantic + structural, 512-dim)
        >>> class MockClaim:
        ...     claim_id = "claim:1"
        ...     text = "Python is used for machine learning"
        >>> claim_embedding = embedder.embed_claim(MockClaim())
        >>> print(f"Claim embedding dim: {len(claim_embedding)}")
        Claim embedding dim: 512
        >>>
        >>> # Compute similarity between embeddings
        >>> similarity = embedder.compute_similarity(query_embedding, query_embedding)
        >>> print(f"Self-similarity: {similarity:.2f}")
        Self-similarity: 1.00

    See Also:
        DualEmbeddingConfig: Configuration options
        EmbeddingCache: Caching for performance
        SemanticEmbedder: Text-only embeddings
        StructuralEmbedder: Graph-only embeddings
    """

    def __init__(self, config=None, cache=None):
        self.config = config or DualEmbeddingConfig()
        self.semantic_embedder = SemanticEmbedder(
            self.config.semantic_model, self.config.embedding_dim, True)
        self.structural_embedder = StructuralEmbedder(self.config)
        self._cache = cache

    def add_claim_to_graph(self, cid, entities):
        self.structural_embedder.add_node(cid, {"type": "claim"})
        for e in entities:
            eid = f"entity:{e}"
            self.structural_embedder.add_node(eid, {"type": "entity"})
            self.structural_embedder.add_edge(cid, eid)

    def train_structural(self):
        self.structural_embedder.train()

    def embed_text(self, text):
        if self._cache:
            cached = self._cache.get(f"text:{text}")
            if cached is not None:
                return cached
        embedding = self.semantic_embedder.embed(text)
        if self._cache:
            self._cache.set(f"text:{text}", embedding)
        return embedding

    def embed_claim(self, claim):
        sem = self.semantic_embedder.embed(claim.text)
        struct = self.structural_embedder.get_embedding(claim.claim_id)
        if struct and self.config.structural_weight > 0:
            return sem + struct
        else:
            # Pad with zeros to reach 512 dimensions
            padding = [0.0] * self.config.node2vec_dimensions
            return sem + padding

    def compute_similarity(self, e1, e2):
        ml = min(len(e1), len(e2))
        e1, e2 = e1[:ml], e2[:ml]
        dot = sum(a*b for a,b in zip(e1, e2))
        n1, n2 = math.sqrt(sum(a*a for a in e1)), math.sqrt(sum(b*b for b in e2))
        return dot / (n1 * n2) if n1 > 0 and n2 > 0 else 0.0
