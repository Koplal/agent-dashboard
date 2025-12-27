"""
HNSW Index Support for Knowledge Graph.

Provides approximate nearest neighbor search using Hierarchical
Navigable Small World graphs for fast vector similarity search.

Version: 2.7.0
"""

import json
import math
import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple, Any

try:
    import hnswlib
    HNSWLIB_AVAILABLE = True
except ImportError:
    hnswlib = None
    HNSWLIB_AVAILABLE = False


class CapacityError(Exception):
    """Raised when index is at capacity."""
    pass


@dataclass
class HNSWConfig:
    """Configuration for HNSW index."""
    dim: int
    max_elements: int = 1_000_000
    M: int = 16
    ef_construction: int = 200
    ef_search: int = 50
    space: str = "cosine"

    def __post_init__(self):
        if self.dim <= 0:
            raise ValueError("dim must be positive")
        if self.M < 2:
            raise ValueError("M must be at least 2")
        if self.ef_construction <= 0:
            raise ValueError("ef_construction must be positive")
        if self.ef_search <= 0:
            raise ValueError("ef_search must be positive")


class HNSWIndex:
    """HNSW index for approximate nearest neighbor search."""

    def __init__(self, config: HNSWConfig):
        self.config = config
        self._id_to_label: Dict[str, int] = {}
        self._label_to_id: Dict[int, str] = {}
        self._next_label: int = 0

        if HNSWLIB_AVAILABLE:
            self._index = hnswlib.Index(space=config.space, dim=config.dim)
            self._index.init_index(
                max_elements=config.max_elements,
                M=config.M,
                ef_construction=config.ef_construction,
            )
            self._index.set_ef(config.ef_search)
        else:
            # Fallback: simple in-memory storage
            self._vectors: Dict[str, List[float]] = {}
            self._index = None

    @property
    def count(self) -> int:
        if HNSWLIB_AVAILABLE and self._index:
            return self._index.get_current_count()
        return len(self._vectors) if hasattr(self, "_vectors") else 0

    def _normalize(self, vec: List[float]) -> List[float]:
        """Normalize vector to unit length."""
        norm = math.sqrt(sum(x * x for x in vec))
        if norm == 0:
            raise ValueError("Cannot normalize zero vector")
        return [x / norm for x in vec]

    def add(self, id: str, vector: List[float]) -> None:
        """Add a vector to the index."""
        if len(vector) != self.config.dim:
            raise ValueError(f"Vector dimension {len(vector)} does not match index dimension {self.config.dim}")

        vector = self._normalize(vector)

        if HNSWLIB_AVAILABLE and self._index:
            if id in self._id_to_label:
                # Update existing
                label = self._id_to_label[id]
            else:
                if self.count >= self.config.max_elements:
                    raise CapacityError(f"Index at capacity ({self.config.max_elements})")
                label = self._next_label
                self._next_label += 1
                self._id_to_label[id] = label
                self._label_to_id[label] = id
            self._index.add_items([vector], [label])
        else:
            self._vectors[id] = vector

    def add_batch(self, ids: List[str], vectors: List[List[float]]) -> None:
        """Add multiple vectors to the index."""
        for id, vec in zip(ids, vectors):
            self.add(id, vec)


    def search(self, query: List[float], k: int = 10, filter_ids: Optional[Set[str]] = None) -> List[Tuple[str, float]]:
        """Search for k nearest neighbors."""
        if self.count == 0:
            return []

        query = self._normalize(query)

        if HNSWLIB_AVAILABLE and self._index:
            labels, distances = self._index.knn_query([query], k=min(k, self.count))
            results = []
            for label, dist in zip(labels[0], distances[0]):
                id = self._label_to_id.get(int(label))
                if id:
                    # Convert distance to similarity for cosine
                    similarity = 1.0 - dist
                    results.append((id, similarity))
        else:
            # Fallback: brute force search
            results = []
            for id, vec in self._vectors.items():
                similarity = sum(a * b for a, b in zip(query, vec))
                results.append((id, similarity))
            results.sort(key=lambda x: x[1], reverse=True)
            results = results[:k]

        # Apply filter if provided
        if filter_ids is not None:
            results = [(id, sim) for id, sim in results if id in filter_ids]

        return results

    def save(self, path: str) -> None:
        """Save index to disk."""
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)

        if HNSWLIB_AVAILABLE and self._index:
            self._index.save_index(path)
            # Save mappings
            meta_path = path + ".meta"
            with open(meta_path, "w") as f:
                json.dump({
                    "config": {
                        "dim": self.config.dim,
                        "max_elements": self.config.max_elements,
                        "M": self.config.M,
                        "ef_construction": self.config.ef_construction,
                        "ef_search": self.config.ef_search,
                        "space": self.config.space,
                    },
                    "id_to_label": self._id_to_label,
                    "next_label": self._next_label,
                }, f)
        else:
            with open(path, "w") as f:
                json.dump({
                    "config": {
                        "dim": self.config.dim,
                        "max_elements": self.config.max_elements,
                        "M": self.config.M,
                        "ef_construction": self.config.ef_construction,
                        "ef_search": self.config.ef_search,
                        "space": self.config.space,
                    },
                    "vectors": self._vectors,
                }, f)

    @classmethod
    def load(cls, path: str) -> "HNSWIndex":
        """Load index from disk."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Index file not found: {path}")

        if HNSWLIB_AVAILABLE:
            meta_path = path + ".meta"
            if not os.path.exists(meta_path):
                raise FileNotFoundError(f"Index metadata not found: {meta_path}")

            with open(meta_path, "r") as f:
                meta = json.load(f)

            config = HNSWConfig(**meta["config"])
            index = cls(config)
            index._index.load_index(path, max_elements=config.max_elements)
            index._id_to_label = meta["id_to_label"]
            index._label_to_id = {int(v): k for k, v in meta["id_to_label"].items()}
            index._next_label = meta["next_label"]
            return index
        else:
            with open(path, "r") as f:
                data = json.load(f)

            config = HNSWConfig(**data["config"])
            index = cls(config)
            index._vectors = data["vectors"]
            return index
