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
    h = hashlib.sha256(text.encode()).hexdigest()
    emb = [int(h[i % 64], 16) / 8.0 - 1.0 for i in range(dim)]
    norm = math.sqrt(sum(x*x for x in emb))
    return [x/norm for x in emb] if norm > 0 else emb


class EmbeddingCache:
    """TTL-based cache for embeddings."""
    
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
    def __init__(self, model_name="all-MiniLM-L6-v2", embedding_dim=384, fallback_mode=False):
        self.model_name = model_name
        self.embedding_dim = embedding_dim
        self.fallback_mode = fallback_mode
        self._model = None

    def embed(self, text: str) -> List[float]:
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
