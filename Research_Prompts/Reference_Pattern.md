# Documentation Enhancement Task for Dual Embedding Module
Follow the docstring style from `src/knowledge/retriever.py`:

```python
class HybridRetriever:
    """Combines vector and graph retrieval for enhanced results.

    Provides:
    - Vector similarity search using embeddings
    - Graph expansion via shared entities
    - Score fusion with configurable weights

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
```

## Classes Requiring Examples

### 1. DualEmbeddingConfig (line 27)

Add example showing:
- Default configuration usage
- Custom weight configuration
- Serialization with to_dict/from_dict

```python
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
```

### 2. EmbeddingCache (line 75)

Add example showing:
- Basic get/set operations
- TTL configuration
- Cache statistics

```python
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
        >>> embedding = [0.1, 0.2, 0.3, ...]  # 384-dim vector
        >>> cache.set("query:machine learning", embedding)
        >>> 
        >>> # Retrieve from cache
        >>> cached = cache.get("query:machine learning")
        >>> if cached is not None:
        ...     print("Cache hit!")
        >>> 
        >>> # Check cache size
        >>> print(f"Cached entries: {cache.size()}")
        >>> 
        >>> # Store with custom TTL (5 minutes)
        >>> cache.set("temporary:query", embedding, ttl=300.0)
        >>> 
        >>> # Clear all entries
        >>> cache.clear()
    """
```

### 3. SemanticEmbedder (line 108)

Add example showing:
- Single text embedding
- Batch embedding
- Fallback behavior note

```python
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
```

### 4. StructuralEmbedder (line 159)

Add example showing:
- Building graph structure
- Training embeddings
- Retrieving node embeddings

```python
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
```

### 5. DualEmbedder (line 207)

Add example showing:
- Full workflow from claims to embeddings
- Similarity computation
- Integration with knowledge graph

```python
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
        >>> # Embed a query (semantic only, 384-dim + 128-dim padding)
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
```

## Implementation Steps

1. **Read the current file:**
   ```bash
   cat src/knowledge/embeddings.py
   ```

2. **For each class**, replace the existing docstring with the enhanced version containing:
   - Brief description
   - Detailed explanation of functionality
   - `Example:` block with runnable code
   - `See Also:` references where appropriate

3. **Verify examples are runnable:**
   ```bash
   python -c "from src.knowledge.embeddings import DualEmbeddingConfig; print(DualEmbeddingConfig())"
   ```

4. **Run existing tests to ensure no regressions:**
   ```bash
   python -m pytest tests/test_dual_embeddings.py -v
   ```

## Quality Checklist

- [ ] All 5 public classes have `Example:` blocks
- [ ] Examples use realistic values (not foo/bar)
- [ ] Examples show common use cases
- [ ] Examples include expected output where appropriate
- [ ] `See Also:` links connect related classes
- [ ] No existing tests broken
- [ ] Docstrings follow Google style (Args:, Returns:, Raises:)

## Notes

- The module uses hash-based fallback when sentence-transformers is unavailable
- Examples should work with the fallback mode (don't require GPU)
- Keep examples concise but comprehensive
- Use `>>>` doctest format for consistency with other modules