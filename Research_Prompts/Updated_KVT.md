# Agent Dashboard v2.7.0 Enhancement Implementation

## Implementation Prompt for Claude Code

Use this prompt with Claude Code to implement the P1, P2, P3, and P4 enhancements identified in the v2.6.0 analysis. This follows the agent-dashboard TDD workflow with tiered agent orchestration.

---

## 🎯 Mission Briefing

You are implementing 12 enhancements to the Agent Dashboard neurosymbolic architecture, organized into four priority tiers. Each enhancement follows strict TDD principles: **tests are written first and locked before implementation begins**.

### Priority Overview

| Priority | Features | Est. Effort | Parallelizable |
|----------|----------|-------------|----------------|
| **P1** | 3 features | 40-50 hours | Yes (3 worktrees) |
| **P2** | 3 features | 30-40 hours | Yes (3 worktrees) |
| **P3** | 3 features | 20-30 hours | Yes (3 worktrees) |
| **P4** | 3 features | 15-20 hours | Yes (3 worktrees) |

**Total Estimated Effort:** 105-140 hours across 12 features

---

## 📋 Pre-Implementation Research Phase

Before writing any code, spawn parallel research agents to gather industry best practices:

```
Run these researchers in parallel:

1. @web-search-researcher: "Node2Vec graph embeddings Python implementation 2025 best practices networkx"

2. @perplexity-researcher: "BM25 hybrid search vector databases Elasticsearch OpenSearch implementation patterns"

3. @web-search-researcher: "HNSW approximate nearest neighbor index Python faiss hnswlib production scale"

4. @perplexity-researcher: "Leiden community detection algorithm Python implementation igraph cdlib 2025"

5. @web-search-researcher: "Cross-encoder re-ranking sentence-transformers ColBERT production deployment"

After research completes, run @summarizer to synthesize findings into implementation recommendations.
```

---

## 🔧 P1: High Priority Features

### P1-001: Dual Embedding Strategy (Node2Vec)

**Specification File:** `specs/dual_embeddings.spec`

```
AGENT dual-embedding-generator:
  TIER: Sonnet
  
  INPUTS:
    graph: KnowledgeGraph
    text: str
    
  OUTPUTS:
    semantic_embedding: List[float]  # Text-based, 384-dim
    structural_embedding: List[float]  # Graph-based, 128-dim
    combined_embedding: List[float]  # Concatenated, 512-dim
    
  LIMITS:
    max_nodes: 100000
    embedding_timeout: 30s
    
  ALWAYS:
    - Generate semantic embedding using sentence-transformers
    - Generate structural embedding using Node2Vec random walks
    - Normalize both embeddings before concatenation
    - Cache embeddings for repeated queries
    
  NEVER:
    - Process graphs larger than max_nodes without chunking
    - Return embeddings with different dimensions than specified
```

**Test File:** `tests/test_dual_embeddings.py`

```python
"""
Tests for P1-001: Dual Embedding Strategy.

LOCKED: Tests approved - DO NOT MODIFY after approval.
Implementation must pass all tests.
"""

import pytest
import numpy as np
from datetime import datetime, timezone

# Expected imports after implementation
# from src.knowledge.embeddings import (
#     DualEmbeddingGenerator,
#     EmbeddingConfig,
#     EmbeddingResult,
# )


class TestDualEmbeddingConfig:
    """Test embedding configuration."""
    
    def test_default_dimensions(self):
        """Semantic=384, Structural=128, Combined=512."""
        config = EmbeddingConfig()
        assert config.semantic_dim == 384
        assert config.structural_dim == 128
        assert config.combined_dim == 512
    
    def test_custom_dimensions(self):
        """Allow custom dimension configuration."""
        config = EmbeddingConfig(semantic_dim=768, structural_dim=256)
        assert config.combined_dim == 1024
    
    def test_node2vec_parameters(self):
        """Node2Vec walk parameters configurable."""
        config = EmbeddingConfig(
            walk_length=80,
            num_walks=10,
            p=1.0,  # Return parameter
            q=1.0,  # In-out parameter
        )
        assert config.walk_length == 80


class TestSemanticEmbedding:
    """Test text-based semantic embeddings."""
    
    def test_generate_semantic_embedding(self, generator):
        """Generate 384-dim embedding from text."""
        result = generator.semantic_embed("Python is used for machine learning")
        assert len(result) == 384
        assert all(isinstance(x, float) for x in result)
    
    def test_semantic_embedding_normalized(self, generator):
        """Embeddings are L2-normalized."""
        result = generator.semantic_embed("Test text")
        norm = np.linalg.norm(result)
        assert abs(norm - 1.0) < 1e-6
    
    def test_semantic_similarity(self, generator):
        """Similar texts have high cosine similarity."""
        emb1 = generator.semantic_embed("Python programming language")
        emb2 = generator.semantic_embed("Python coding language")
        emb3 = generator.semantic_embed("Quantum physics research")
        
        sim_12 = np.dot(emb1, emb2)
        sim_13 = np.dot(emb1, emb3)
        
        assert sim_12 > sim_13  # Related texts more similar


class TestStructuralEmbedding:
    """Test graph-based structural embeddings."""
    
    def test_generate_structural_embedding(self, generator, sample_graph):
        """Generate 128-dim embedding from graph node."""
        result = generator.structural_embed(sample_graph, node_id="entity:Python")
        assert len(result) == 128
    
    def test_structural_requires_graph(self, generator):
        """Structural embedding requires graph context."""
        with pytest.raises(ValueError, match="graph required"):
            generator.structural_embed(None, node_id="test")
    
    def test_connected_nodes_similar(self, generator, sample_graph):
        """Directly connected nodes have similar embeddings."""
        # Assuming Python -> machine_learning edge exists
        emb_python = generator.structural_embed(sample_graph, "entity:Python")
        emb_ml = generator.structural_embed(sample_graph, "entity:machine_learning")
        emb_unrelated = generator.structural_embed(sample_graph, "entity:cooking")
        
        sim_connected = np.dot(emb_python, emb_ml)
        sim_unconnected = np.dot(emb_python, emb_unrelated)
        
        assert sim_connected > sim_unconnected


class TestCombinedEmbedding:
    """Test combined semantic + structural embeddings."""
    
    def test_combined_dimensions(self, generator, sample_graph):
        """Combined embedding is concatenation."""
        result = generator.combined_embed(
            text="Python for ML",
            graph=sample_graph,
            node_id="entity:Python",
        )
        assert len(result) == 512  # 384 + 128
    
    def test_combined_weighted(self, generator, sample_graph):
        """Weights can adjust semantic vs structural influence."""
        result = generator.combined_embed(
            text="Python for ML",
            graph=sample_graph,
            node_id="entity:Python",
            semantic_weight=0.7,
            structural_weight=0.3,
        )
        assert len(result) == 512
    
    def test_fallback_semantic_only(self, generator):
        """Falls back to semantic-only if no graph."""
        result = generator.combined_embed(
            text="Python for ML",
            graph=None,
            node_id=None,
        )
        # Should return semantic with zero-padded structural
        assert len(result) == 512


class TestEmbeddingCache:
    """Test embedding caching for performance."""
    
    def test_cache_hit(self, generator):
        """Repeated calls use cache."""
        text = "Cache test"
        result1 = generator.semantic_embed(text)
        result2 = generator.semantic_embed(text)
        
        assert result1 == result2
        assert generator.cache_hits == 1
    
    def test_cache_ttl(self, generator):
        """Cache entries expire after TTL."""
        # Implementation should support TTL configuration
        pass


# Fixtures
@pytest.fixture
def generator():
    """Create embedding generator for testing."""
    from src.knowledge.embeddings import DualEmbeddingGenerator, EmbeddingConfig
    return DualEmbeddingGenerator(EmbeddingConfig())


@pytest.fixture
def sample_graph():
    """Create sample knowledge graph for testing."""
    from src.knowledge import MemoryGraphBackend, KGClaim, Entity, EntityType
    
    backend = MemoryGraphBackend()
    
    # Add interconnected claims
    claim1 = KGClaim(
        claim_id="c1",
        text="Python is used for machine learning",
        confidence=0.9,
        source_url="https://example.com",
        entities=[
            Entity(name="Python", entity_type=EntityType.TECHNOLOGY),
            Entity(name="machine_learning", entity_type=EntityType.CONCEPT),
        ],
    )
    claim2 = KGClaim(
        claim_id="c2",
        text="Cooking requires recipes",
        confidence=0.9,
        source_url="https://example.com",
        entities=[
            Entity(name="cooking", entity_type=EntityType.CONCEPT),
        ],
    )
    
    backend.store_claim(claim1)
    backend.store_claim(claim2)
    
    return backend
```

**Acceptance Criteria:**
- [ ] All 15+ tests pass
- [ ] Node2Vec walks complete in <5s for 10k node graphs
- [ ] Embeddings are deterministic with fixed seed
- [ ] Cache reduces repeated embedding time by 90%+
- [ ] Graceful fallback when graph unavailable

---

### P1-002: BM25 Keyword Component (Three-Way Hybrid)

**Specification File:** `specs/bm25_hybrid.spec`

```
AGENT hybrid-retriever-v2:
  TIER: Sonnet
  
  INPUTS:
    query: str
    config: HybridRetrieverConfigV2
    
  OUTPUTS:
    results: List[HybridRetrievalResultV2]
    
  COMPONENTS:
    vector_search: weight 0.4  # Semantic similarity
    graph_search: weight 0.3   # Entity relationships
    bm25_search: weight 0.3    # Keyword matching
    
  LIMITS:
    max_results: 100
    timeout: 10s
    
  ALWAYS:
    - Run all three retrieval methods in parallel
    - Reciprocal Rank Fusion for score combination
    - Deduplicate by claim_id before returning
    
  NEVER:
    - Return duplicate claims
    - Exceed timeout even if searches incomplete
```

**Test File:** `tests/test_bm25_hybrid.py`

```python
"""
Tests for P1-002: BM25 Keyword Component.

LOCKED: Tests approved - DO NOT MODIFY after approval.
"""

import pytest
from typing import List

# from src.knowledge.bm25 import BM25Index, BM25Config
# from src.knowledge.retriever import HybridRetrieverV2, HybridRetrieverConfigV2


class TestBM25Index:
    """Test BM25 keyword index."""
    
    def test_index_documents(self, bm25_index, sample_claims):
        """Index claims for BM25 search."""
        bm25_index.index(sample_claims)
        assert bm25_index.document_count == len(sample_claims)
    
    def test_search_keywords(self, bm25_index):
        """Find documents matching keywords."""
        results = bm25_index.search("Python machine learning", limit=5)
        assert len(results) > 0
        assert all(hasattr(r, 'score') for r in results)
    
    def test_bm25_parameters(self):
        """k1 and b parameters configurable."""
        config = BM25Config(k1=1.5, b=0.75)
        assert config.k1 == 1.5
        assert config.b == 0.75
    
    def test_empty_query(self, bm25_index):
        """Empty query returns empty results."""
        results = bm25_index.search("", limit=5)
        assert results == []
    
    def test_incremental_indexing(self, bm25_index, sample_claims):
        """Add documents incrementally."""
        bm25_index.index(sample_claims[:2])
        initial_count = bm25_index.document_count
        
        bm25_index.add(sample_claims[2])
        assert bm25_index.document_count == initial_count + 1


class TestThreeWayHybrid:
    """Test three-way hybrid retrieval."""
    
    def test_three_components(self, hybrid_v2):
        """Uses vector + graph + BM25."""
        results = hybrid_v2.retrieve("Python machine learning")
        
        # Results should have scores from all three
        for r in results:
            assert hasattr(r, 'vector_score')
            assert hasattr(r, 'graph_score')
            assert hasattr(r, 'bm25_score')
    
    def test_reciprocal_rank_fusion(self, hybrid_v2):
        """Scores combined using RRF."""
        results = hybrid_v2.retrieve("Python")
        
        # RRF formula: sum(1 / (k + rank_i)) for each method
        # Verify combined score is computed correctly
        for r in results:
            expected_rrf = (
                1 / (60 + r.vector_rank) +
                1 / (60 + r.graph_rank) +
                1 / (60 + r.bm25_rank)
            )
            assert abs(r.combined_score - expected_rrf) < 0.01
    
    def test_configurable_weights(self, hybrid_v2):
        """Component weights adjustable."""
        config = HybridRetrieverConfigV2(
            vector_weight=0.5,
            graph_weight=0.25,
            bm25_weight=0.25,
        )
        results = hybrid_v2.retrieve("Python", config=config)
        assert len(results) > 0
    
    def test_no_duplicates(self, hybrid_v2):
        """Results deduplicated by claim_id."""
        results = hybrid_v2.retrieve("Python")
        claim_ids = [r.claim.claim_id for r in results]
        assert len(claim_ids) == len(set(claim_ids))
    
    def test_parallel_execution(self, hybrid_v2, mocker):
        """All three searches run in parallel."""
        # Mock to track execution order
        spy_vector = mocker.spy(hybrid_v2, '_vector_search')
        spy_graph = mocker.spy(hybrid_v2, '_graph_expand')
        spy_bm25 = mocker.spy(hybrid_v2, '_bm25_search')
        
        hybrid_v2.retrieve("Python")
        
        # All should be called (parallel via asyncio.gather or ThreadPoolExecutor)
        assert spy_vector.called
        assert spy_graph.called
        assert spy_bm25.called


class TestBM25Tokenization:
    """Test BM25 text preprocessing."""
    
    def test_lowercasing(self, bm25_index):
        """Queries are lowercased."""
        r1 = bm25_index.search("Python")
        r2 = bm25_index.search("python")
        assert r1 == r2
    
    def test_stopword_removal(self, bm25_index):
        """Common stopwords removed."""
        # "the", "is", "a" should not affect results
        r1 = bm25_index.search("Python programming")
        r2 = bm25_index.search("the Python is a programming")
        assert r1 == r2
    
    def test_stemming(self, bm25_index):
        """Words stemmed for matching."""
        # "programming" and "programs" should match similar docs
        r1 = bm25_index.search("programming")
        r2 = bm25_index.search("programs")
        # Not exactly equal but should have overlap
        ids1 = {r.claim_id for r in r1}
        ids2 = {r.claim_id for r in r2}
        assert len(ids1 & ids2) > 0
```

**Acceptance Criteria:**
- [ ] BM25 index builds in O(n) time
- [ ] Search latency <50ms for 100k documents
- [ ] RRF produces better results than any single method (measured by human eval)
- [ ] Parallel execution reduces latency by 60%+ vs sequential

---

### P1-003: Cross-Platform Install Script

**Specification File:** `specs/cross_platform_install.spec`

```
AGENT installer:
  TIER: Haiku
  
  PLATFORMS:
    - Linux (Ubuntu 20.04+, Debian 11+)
    - macOS (12+)
    - Windows (10+, via WSL2 or native)
    
  OUTPUTS:
    install_result: InstallResult
    
  ALWAYS:
    - Detect platform before installation
    - Use platform-appropriate package manager
    - Verify all dependencies after install
    - Provide rollback on failure
    
  NEVER:
    - Assume Unix-style paths on Windows
    - Use chmod on Windows (use icacls)
    - Fail silently on permission errors
```

**Test File:** `tests/test_cross_platform_install.py`

```python
"""
Tests for P1-003: Cross-Platform Installation.

LOCKED: Tests approved - DO NOT MODIFY after approval.
"""

import os
import sys
import platform
import pytest


class TestPlatformDetection:
    """Test platform detection logic."""
    
    def test_detect_linux(self, mocker):
        """Detect Linux correctly."""
        mocker.patch('platform.system', return_value='Linux')
        from scripts.install import detect_platform
        assert detect_platform() == 'linux'
    
    def test_detect_macos(self, mocker):
        """Detect macOS correctly."""
        mocker.patch('platform.system', return_value='Darwin')
        from scripts.install import detect_platform
        assert detect_platform() == 'macos'
    
    def test_detect_windows(self, mocker):
        """Detect Windows correctly."""
        mocker.patch('platform.system', return_value='Windows')
        from scripts.install import detect_platform
        assert detect_platform() == 'windows'
    
    def test_detect_wsl(self, mocker):
        """Detect WSL as Linux variant."""
        mocker.patch('platform.system', return_value='Linux')
        mocker.patch('os.path.exists', return_value=True)  # /proc/version contains Microsoft
        from scripts.install import detect_platform
        result = detect_platform()
        assert result in ['linux', 'wsl']


class TestPermissions:
    """Test permission handling across platforms."""
    
    @pytest.mark.skipif(sys.platform == 'win32', reason="Unix only")
    def test_unix_executable_permission(self, tmp_path):
        """Set executable permission on Unix."""
        from scripts.install import set_executable
        
        script = tmp_path / "test.sh"
        script.write_text("#!/bin/bash\necho hello")
        
        set_executable(script)
        
        assert os.access(script, os.X_OK)
    
    @pytest.mark.skipif(sys.platform != 'win32', reason="Windows only")
    def test_windows_no_chmod(self, tmp_path):
        """Windows doesn't use chmod."""
        from scripts.install import set_executable
        
        script = tmp_path / "test.bat"
        script.write_text("@echo hello")
        
        # Should not raise, should use alternative method
        set_executable(script)
    
    def test_permission_error_handling(self, tmp_path, mocker):
        """Handle permission errors gracefully."""
        from scripts.install import set_executable, InstallError
        
        mocker.patch('os.chmod', side_effect=PermissionError("Access denied"))
        
        script = tmp_path / "test.sh"
        script.write_text("#!/bin/bash")
        
        with pytest.raises(InstallError, match="permission"):
            set_executable(script)


class TestPackageManagers:
    """Test package manager detection and usage."""
    
    def test_detect_pip(self):
        """pip always available."""
        from scripts.install import find_package_manager
        assert 'pip' in find_package_manager('python')
    
    @pytest.mark.skipif(sys.platform != 'darwin', reason="macOS only")
    def test_detect_homebrew(self):
        """Detect Homebrew on macOS."""
        from scripts.install import find_package_manager
        result = find_package_manager('system')
        # brew or port
        assert result in ['brew', 'port', None]
    
    @pytest.mark.skipif(sys.platform != 'linux', reason="Linux only")
    def test_detect_apt_or_yum(self):
        """Detect apt or yum on Linux."""
        from scripts.install import find_package_manager
        result = find_package_manager('system')
        assert result in ['apt', 'yum', 'dnf', 'pacman', None]


class TestInstallVerification:
    """Test post-install verification."""
    
    def test_verify_python_packages(self):
        """Verify required Python packages installed."""
        from scripts.install import verify_dependencies
        
        result = verify_dependencies(['pydantic', 'pytest'])
        assert result.success
        assert 'pydantic' in result.installed
    
    def test_missing_package_detected(self):
        """Detect missing packages."""
        from scripts.install import verify_dependencies
        
        result = verify_dependencies(['nonexistent_package_xyz'])
        assert not result.success
        assert 'nonexistent_package_xyz' in result.missing
    
    def test_version_requirements(self):
        """Verify version requirements met."""
        from scripts.install import verify_dependencies
        
        result = verify_dependencies(['pydantic>=2.0.0'])
        assert result.success


class TestRollback:
    """Test rollback on installation failure."""
    
    def test_rollback_on_failure(self, tmp_path, mocker):
        """Rollback changes on failure."""
        from scripts.install import install_with_rollback
        
        # Simulate failure after partial install
        mocker.patch('subprocess.run', side_effect=[
            None,  # First package succeeds
            Exception("Network error"),  # Second fails
        ])
        
        with pytest.raises(Exception):
            install_with_rollback(['package1', 'package2'])
        
        # Verify rollback was attempted
        # (implementation-specific verification)
```

**Acceptance Criteria:**
- [ ] Install succeeds on Ubuntu 22.04, macOS 14, Windows 11 WSL2
- [ ] All tests pass on all platforms
- [ ] Clear error messages for permission issues
- [ ] Rollback works when installation fails mid-way

---

## 🔧 P2: Medium Priority Features

### P2-001: Leiden Community Detection

**Git Worktree:** `git worktree add ../agent-dashboard-leiden feature/leiden-communities`

**Specification File:** `specs/leiden_communities.spec`

```
AGENT community-detector:
  TIER: Sonnet
  
  INPUTS:
    graph: KnowledgeGraph
    resolution: float = 1.0
    
  OUTPUTS:
    communities: List[Community]
    hierarchy: CommunityHierarchy
    modularity: float
    
  LIMITS:
    max_nodes: 1000000
    timeout: 60s
    
  ALWAYS:
    - Use Leiden algorithm (faster than Louvain)
    - Build hierarchical community structure
    - Calculate modularity score
    - Assign every node to exactly one community
    
  NEVER:
    - Leave nodes unassigned
    - Create single-node communities (merge into nearest)
```

**Implementation Notes:**
```python
# Use python-igraph or cdlib for Leiden
# pip install python-igraph cdlib leidenalg

from igraph import Graph
import leidenalg

def detect_communities(kg_graph, resolution=1.0):
    # Convert KG to igraph
    ig = Graph.TupleList(kg_graph.get_edges(), directed=False)
    
    # Run Leiden
    partition = leidenalg.find_partition(
        ig,
        leidenalg.RBConfigurationVertexPartition,
        resolution_parameter=resolution
    )
    
    return {
        'communities': partition.membership,
        'modularity': partition.modularity,
        'n_communities': len(partition),
    }
```

---

### P2-002: HNSW Index Support

**Git Worktree:** `git worktree add ../agent-dashboard-hnsw feature/hnsw-index`

**Specification File:** `specs/hnsw_index.spec`

```
AGENT hnsw-indexer:
  TIER: Sonnet
  
  INPUTS:
    embeddings: List[Tuple[str, List[float]]]  # (id, vector) pairs
    
  OUTPUTS:
    index: HNSWIndex
    
  PARAMETERS:
    M: int = 16           # Max connections per layer
    ef_construction: int = 200  # Build-time beam width
    ef_search: int = 50   # Query-time beam width
    
  LIMITS:
    max_vectors: 10000000
    build_timeout: 3600s
    
  ALWAYS:
    - Use hnswlib or faiss for implementation
    - Support incremental additions
    - Persist index to disk
    - Support filtering during search
```

**Implementation Notes:**
```python
# Use hnswlib for pure Python, faiss for production scale
# pip install hnswlib  # or faiss-cpu / faiss-gpu

import hnswlib
import numpy as np

class HNSWVectorIndex:
    def __init__(self, dim: int, max_elements: int, M: int = 16, ef: int = 200):
        self.index = hnswlib.Index(space='cosine', dim=dim)
        self.index.init_index(max_elements=max_elements, M=M, ef_construction=ef)
        self.id_to_label = {}
        self.label_to_id = {}
    
    def add(self, id: str, vector: List[float]):
        label = len(self.id_to_label)
        self.id_to_label[id] = label
        self.label_to_id[label] = id
        self.index.add_items([vector], [label])
    
    def search(self, query: List[float], k: int = 10, ef: int = 50) -> List[Tuple[str, float]]:
        self.index.set_ef(ef)
        labels, distances = self.index.knn_query([query], k=k)
        return [(self.label_to_id[l], 1 - d) for l, d in zip(labels[0], distances[0])]
    
    def save(self, path: str):
        self.index.save_index(path)
    
    def load(self, path: str):
        self.index.load_index(path)
```

---

### P2-003: Tiered Token Counting

**Git Worktree:** `git worktree add ../agent-dashboard-tokens feature/tiered-token-counting`

**Specification File:** `specs/tiered_tokens.spec`

```
AGENT token-counter:
  TIER: Haiku
  
  FALLBACK_CHAIN:
    1. xenova/claude-tokenizer (npm package, 99.9% accurate)
    2. Anthropic API token counting (100% accurate, requires API call)
    3. tiktoken cl100k_base (95% accurate for Claude)
    4. character estimation (text.length / 4, 70% accurate)
    
  OUTPUTS:
    token_count: int
    method_used: str
    confidence: float
    
  ALWAYS:
    - Try methods in order until one succeeds
    - Cache results for repeated text
    - Log which method was used
    
  NEVER:
    - Fail completely - always fall back to estimation
    - Make API calls for <1000 character strings (use estimation)
```

**Implementation:**
```python
import subprocess
import json
from typing import Tuple

class TieredTokenCounter:
    def __init__(self):
        self._cache = {}
        self._xenova_available = self._check_xenova()
        self._tiktoken_available = self._check_tiktoken()
    
    def _check_xenova(self) -> bool:
        try:
            result = subprocess.run(
                ['node', '-e', 'require("@xenova/transformers")'],
                capture_output=True, timeout=5
            )
            return result.returncode == 0
        except:
            return False
    
    def _check_tiktoken(self) -> bool:
        try:
            import tiktoken
            return True
        except ImportError:
            return False
    
    def count(self, text: str) -> Tuple[int, str, float]:
        """Count tokens with fallback chain."""
        cache_key = hash(text)
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Short text: use estimation (save API calls)
        if len(text) < 1000:
            result = (len(text) // 4, 'estimation', 0.70)
            self._cache[cache_key] = result
            return result
        
        # Try Xenova first (highest accuracy offline)
        if self._xenova_available:
            try:
                count = self._count_xenova(text)
                result = (count, 'xenova', 0.999)
                self._cache[cache_key] = result
                return result
            except:
                pass
        
        # Try tiktoken
        if self._tiktoken_available:
            try:
                import tiktoken
                enc = tiktoken.get_encoding('cl100k_base')
                count = len(enc.encode(text))
                result = (count, 'tiktoken', 0.95)
                self._cache[cache_key] = result
                return result
            except:
                pass
        
        # Fallback to estimation
        result = (len(text) // 4, 'estimation', 0.70)
        self._cache[cache_key] = result
        return result
    
    def _count_xenova(self, text: str) -> int:
        # Call Node.js script for Xenova tokenizer
        script = '''
        const { AutoTokenizer } = require('@xenova/transformers');
        async function count(text) {
            const tokenizer = await AutoTokenizer.from_pretrained('Xenova/claude-tokenizer');
            const tokens = tokenizer.encode(text);
            console.log(tokens.length);
        }
        count(process.argv[1]);
        '''
        result = subprocess.run(
            ['node', '-e', script, text],
            capture_output=True, text=True, timeout=30
        )
        return int(result.stdout.strip())
```

---

## 🔧 P3: Low Priority Features

### P3-001: Graph Embedding Visualization

**Specification:** Interactive 2D/3D visualization of graph embeddings using UMAP/t-SNE reduction.

```python
# Use plotly for interactive visualization
# pip install plotly umap-learn

import plotly.express as px
import umap

def visualize_embeddings(embeddings: Dict[str, List[float]], labels: Dict[str, str] = None):
    """Create interactive 2D scatter plot of embeddings."""
    ids = list(embeddings.keys())
    vectors = np.array([embeddings[id] for id in ids])
    
    # Reduce to 2D
    reducer = umap.UMAP(n_neighbors=15, min_dist=0.1, metric='cosine')
    coords = reducer.fit_transform(vectors)
    
    # Create dataframe
    df = pd.DataFrame({
        'id': ids,
        'x': coords[:, 0],
        'y': coords[:, 1],
        'label': [labels.get(id, id) for id in ids] if labels else ids,
    })
    
    fig = px.scatter(df, x='x', y='y', hover_data=['id', 'label'])
    return fig
```

---

### P3-002: Cross-Encoder Re-Ranking

**Specification:** Use cross-encoder for precision improvement on top-k results.

```python
# pip install sentence-transformers

from sentence_transformers import CrossEncoder

class ReRanker:
    def __init__(self, model_name: str = 'cross-encoder/ms-marco-MiniLM-L-6-v2'):
        self.model = CrossEncoder(model_name)
    
    def rerank(self, query: str, candidates: List[str], top_k: int = 10) -> List[Tuple[int, float]]:
        """Re-rank candidates using cross-encoder."""
        pairs = [[query, c] for c in candidates]
        scores = self.model.predict(pairs)
        
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]
```

---

### P3-003: Benchmark Suite

**Specification:** Comprehensive performance benchmarks for all retrieval methods.

```python
# tests/benchmarks/test_retrieval_performance.py

import pytest
import time
from statistics import mean, stdev

@pytest.fixture(scope='module')
def benchmark_data():
    """Load or generate benchmark dataset."""
    # 10k claims, 1k queries
    pass

class TestRetrievalBenchmarks:
    """Performance benchmarks for retrieval methods."""
    
    @pytest.mark.benchmark
    def test_vector_search_latency(self, benchmark_data, retriever):
        """Vector search p50/p95/p99 latency."""
        latencies = []
        for query in benchmark_data['queries']:
            start = time.perf_counter()
            retriever.vector_search(query)
            latencies.append((time.perf_counter() - start) * 1000)
        
        latencies.sort()
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95)]
        p99 = latencies[int(len(latencies) * 0.99)]
        
        assert p50 < 10, f"p50 latency {p50}ms exceeds 10ms target"
        assert p95 < 50, f"p95 latency {p95}ms exceeds 50ms target"
        assert p99 < 100, f"p99 latency {p99}ms exceeds 100ms target"
    
    @pytest.mark.benchmark
    def test_hybrid_search_latency(self, benchmark_data, retriever):
        """Three-way hybrid search latency."""
        # Similar structure
        pass
    
    @pytest.mark.benchmark
    def test_index_build_time(self, benchmark_data, indexer):
        """HNSW index build time for 100k vectors."""
        start = time.perf_counter()
        indexer.build(benchmark_data['embeddings'])
        elapsed = time.perf_counter() - start
        
        assert elapsed < 60, f"Index build {elapsed}s exceeds 60s target"
    
    @pytest.mark.benchmark
    def test_memory_usage(self, benchmark_data, retriever):
        """Memory usage under load."""
        import tracemalloc
        
        tracemalloc.start()
        for _ in range(1000):
            retriever.retrieve("test query")
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Peak memory should be <1GB for 100k document index
        assert peak < 1e9, f"Peak memory {peak/1e9:.2f}GB exceeds 1GB target"
```

---

## 🚀 Execution Plan

### Phase 1: Research (Day 1)

```bash
# Run parallel research agents
claude --agent researcher "Node2Vec Python implementation best practices 2024"
claude --agent perplexity-researcher "BM25 hybrid search implementation patterns"
claude --agent web-search-researcher "HNSW index production deployment"

# Synthesize findings
claude --agent summarizer --input research_outputs/
```

### Phase 2: P1 Implementation (Days 2-5)

```bash
# Create parallel worktrees
git worktree add ../agent-dashboard-embeddings feature/dual-embeddings
git worktree add ../agent-dashboard-bm25 feature/bm25-hybrid
git worktree add ../agent-dashboard-install feature/cross-platform-install

# Terminal 1: Dual Embeddings
cd ../agent-dashboard-embeddings
claude "Implement P1-001 following specs/dual_embeddings.spec. Tests first, TDD workflow."

# Terminal 2: BM25 Hybrid
cd ../agent-dashboard-bm25
claude "Implement P1-002 following specs/bm25_hybrid.spec. Tests first, TDD workflow."

# Terminal 3: Install Script
cd ../agent-dashboard-install
claude "Implement P1-003 following specs/cross_platform_install.spec. Tests first, TDD workflow."
```

### Phase 3: P2 Implementation (Days 6-8)

```bash
# After P1 merges
git worktree add ../agent-dashboard-leiden feature/leiden-communities
git worktree add ../agent-dashboard-hnsw feature/hnsw-index
git worktree add ../agent-dashboard-tokens feature/tiered-token-counting

# Parallel implementation same pattern
```

### Phase 4: P3 Implementation (Days 9-10)

```bash
# After P2 merges
git worktree add ../agent-dashboard-viz feature/embedding-visualization
git worktree add ../agent-dashboard-rerank feature/cross-encoder-reranking
git worktree add ../agent-dashboard-bench feature/benchmark-suite
```

### Phase 5: Integration & Review (Days 11-12)

```bash
# Run judge panel on each feature
claude --agent judge-technical "Evaluate dual-embeddings implementation"
claude --agent judge-completeness "Evaluate BM25 hybrid coverage"
claude --agent judge-practicality "Evaluate cross-platform install usability"

# Final synthesis
claude --agent summarizer "Generate release notes for v2.7.0"
```

---

## ✅ Definition of Done

Each feature is complete when:

1. [ ] All specification tests pass
2. [ ] Documentation updated (CHANGELOG, README, module docstrings)
3. [ ] Judge panel score ≥ 4.0/5.0
4. [ ] No regressions in existing tests
5. [ ] PR approved and merged
6. [ ] Version bumped in `src/__version__.py`

---

## 📊 Success Metrics

| Feature | Metric | Target |
|---------|--------|--------|
| Dual Embeddings | Retrieval MRR improvement | +15% |
| BM25 Hybrid | Keyword query recall | +25% |
| Cross-Platform | Platform test coverage | 100% |
| Leiden Communities | Global query latency | <100ms |
| HNSW Index | Vector search latency | <10ms p50 |
| Token Counting | Accuracy vs API | >95% |
| Visualization | Load time for 10k nodes | <2s |
| Re-Ranking | Precision@10 improvement | +20% |
| Benchmarks | CI run time | <5min |

---

## 🔧 P4: Minor Enhancements (Judge Panel Recommendations)

These non-blocking improvements were identified during judge panel review. Lower priority but valuable for developer experience and future-proofing.

### P4-001: Enhanced Docstring Examples

**Git Worktree:** `git worktree add ../agent-dashboard-docs feature/docstring-examples`

**Specification File:** `specs/docstring_examples.spec`

```
AGENT docstring-enhancer:
  TIER: Haiku
  
  TARGETS:
    - All public classes in src/
    - All public functions with >3 parameters
    - All complex return types
    
  OUTPUTS:
    enhanced_file: str
    examples_added: int
    
  EXAMPLE_FORMAT:
    """
    Brief description.
    
    Detailed explanation if needed.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ExceptionType: When this happens
        
    Example:
        >>> from src.module import ClassName
        >>> obj = ClassName(param1="value")
        >>> result = obj.method(input_data)
        >>> print(result.score)
        0.85
        
    See Also:
        RelatedClass: For similar functionality
    """
    
  ALWAYS:
    - Include at least one runnable example per public method
    - Show common use cases, not edge cases
    - Use realistic parameter values
    - Include expected output in doctest format
    
  NEVER:
    - Add examples that require external resources
    - Use placeholder values like "foo", "bar", "test"
    - Break existing doctests
```

**Implementation Checklist:**

```python
# Priority modules for docstring enhancement (by usage frequency)

PRIORITY_MODULES = [
    # Tier 1: Most used public APIs
    "src/knowledge/retriever.py",      # HybridRetriever
    "src/knowledge/manager.py",        # KnowledgeGraphManager
    "src/validators/output_validator.py",  # OutputValidator
    "src/judges/panel.py",             # HeterogeneousPanel
    
    # Tier 2: Configuration classes
    "src/knowledge/graph.py",          # KGClaim, Entity, Source
    "src/audit/trail.py",              # AuditEntry
    "src/learning/models.py",          # ExtractedRule, ExecutionOutcome
    
    # Tier 3: Internal utilities
    "src/verification/symbolic_solver.py",
    "src/specifications/parser.py",
    "src/constraints/structured_generation.py",
]
```

**Example Enhancement Pattern:**

```python
# BEFORE
class HybridRetriever:
    """Combines vector and graph retrieval for enhanced results."""
    
    def retrieve(self, query: str, limit: int = 10) -> List[HybridRetrievalResult]:
        """Retrieve claims using hybrid approach."""
        pass

# AFTER
class HybridRetriever:
    """
    Combines vector similarity and graph traversal for contextually relevant retrieval.
    
    The hybrid approach uses configurable weights to balance semantic similarity
    (vector search) with structural relationships (graph expansion). Results are
    scored using a fusion algorithm that rewards claims found by multiple methods.
    
    Attributes:
        storage: Backend storage for the knowledge graph
        embedding_fn: Function to compute text embeddings
        config: Retrieval configuration with weights and thresholds
        
    Example:
        >>> from src.knowledge import HybridRetriever, MemoryGraphBackend
        >>> from src.knowledge.manager import default_embedding_function
        >>> 
        >>> # Setup retriever with default config
        >>> backend = MemoryGraphBackend()
        >>> retriever = HybridRetriever(
        ...     storage=backend,
        ...     embedding_fn=default_embedding_function,
        ... )
        >>> 
        >>> # Retrieve relevant claims
        >>> results = retriever.retrieve("machine learning frameworks", limit=5)
        >>> for r in results:
        ...     print(f"{r.claim.text[:50]}... (score: {r.combined_score:.2f})")
        Python is widely used for machine learning... (score: 0.87)
        TensorFlow provides powerful tools for deep... (score: 0.72)
        
    See Also:
        HybridRetrieverConfig: For customizing retrieval weights
        KnowledgeGraphManager: Higher-level API with automatic embedding
    """
    
    def retrieve(
        self,
        query: str,
        limit: int = 10,
        config: Optional[HybridRetrieverConfig] = None,
    ) -> List[HybridRetrievalResult]:
        """
        Retrieve claims using hybrid vector+graph approach.
        
        Performs vector similarity search followed by graph expansion from
        seed results. Scores are fused using configurable weights.
        
        Args:
            query: Search query text (will be embedded automatically)
            limit: Maximum number of results to return (default: 10)
            config: Override default config for this query. If None,
                uses the config provided at initialization.
                
        Returns:
            List of HybridRetrievalResult sorted by combined_score descending.
            Each result contains:
            - claim: The matched KGClaim object
            - combined_score: Fused score (0.0-1.0)
            - vector_score: Contribution from vector similarity
            - graph_score: Contribution from graph relationships
            - retrieval_path: "vector", "graph", or "both"
            
        Raises:
            ValueError: If query is empty or whitespace-only
            
        Example:
            >>> # Basic retrieval
            >>> results = retriever.retrieve("Python data science")
            >>> len(results)
            5
            
            >>> # Custom config for this query
            >>> from src.knowledge.retriever import HybridRetrieverConfig
            >>> config = HybridRetrieverConfig(vector_weight=0.8, graph_weight=0.2)
            >>> results = retriever.retrieve("Python", limit=3, config=config)
            >>> results[0].retrieval_path
            'both'
            
        Note:
            Empty queries return an empty list without raising an exception.
            For best results, use descriptive multi-word queries.
        """
        pass
```

**Test File:** `tests/test_docstring_examples.py`

```python
"""
Tests for P4-001: Docstring Examples.

Validates that all docstring examples are runnable and produce expected output.
"""

import doctest
import pytest
import importlib
from pathlib import Path


MODULES_WITH_EXAMPLES = [
    "src.knowledge.retriever",
    "src.knowledge.manager",
    "src.knowledge.graph",
    "src.validators.output_validator",
    "src.judges.panel",
    "src.audit.trail",
    "src.learning.models",
]


class TestDocstringExamples:
    """Verify docstring examples are valid and runnable."""
    
    @pytest.mark.parametrize("module_path", MODULES_WITH_EXAMPLES)
    def test_doctest_examples(self, module_path):
        """All docstring examples should pass doctest."""
        module = importlib.import_module(module_path)
        results = doctest.testmod(module, verbose=False)
        assert results.failed == 0, f"{module_path}: {results.failed} doctest failures"
    
    def test_public_methods_have_examples(self):
        """Public methods should have at least one example."""
        from src.knowledge.retriever import HybridRetriever
        
        # Check retrieve method has Example section
        assert "Example:" in HybridRetriever.retrieve.__doc__
        assert ">>>" in HybridRetriever.retrieve.__doc__
    
    def test_examples_use_realistic_values(self):
        """Examples should not use placeholder values."""
        from src.knowledge.retriever import HybridRetriever
        
        doc = HybridRetriever.retrieve.__doc__
        
        # No placeholder values
        assert "foo" not in doc.lower()
        assert "bar" not in doc.lower()
        assert "test123" not in doc.lower()
        
        # Uses realistic values
        assert "machine learning" in doc.lower() or "python" in doc.lower()


class TestDocstringCompleteness:
    """Verify docstrings have all required sections."""
    
    def test_has_args_section(self):
        """Methods with parameters should document Args."""
        from src.knowledge.retriever import HybridRetriever
        
        doc = HybridRetriever.retrieve.__doc__
        assert "Args:" in doc
        assert "query:" in doc
        assert "limit:" in doc
    
    def test_has_returns_section(self):
        """Methods with return values should document Returns."""
        from src.knowledge.retriever import HybridRetriever
        
        doc = HybridRetriever.retrieve.__doc__
        assert "Returns:" in doc
    
    def test_has_raises_section_if_applicable(self):
        """Methods that raise exceptions should document Raises."""
        from src.knowledge.retriever import HybridRetriever
        
        doc = HybridRetriever.retrieve.__doc__
        # Only if the method actually raises
        assert "Raises:" in doc or "ValueError" not in str(HybridRetriever.retrieve)
```

**Acceptance Criteria:**
- [ ] All priority modules have enhanced docstrings
- [ ] All doctest examples pass
- [ ] No placeholder values in examples
- [ ] Coverage: 100% of public methods with >0 parameters

---

### P4-002: Configuration Reference Tables

**Git Worktree:** `git worktree add ../agent-dashboard-config-docs feature/config-reference`

**Specification File:** `specs/config_reference.spec`

```
AGENT config-documenter:
  TIER: Haiku
  
  OUTPUTS:
    - docs/CONFIG_REFERENCE.md
    - Per-module config tables in docstrings
    
  TABLE_FORMAT:
    | Parameter | Type | Default | Range | Description |
    |-----------|------|---------|-------|-------------|
    
  ALWAYS:
    - Extract defaults from code (never hardcode in docs)
    - Include valid ranges/choices for constrained parameters
    - Group related parameters
    - Add "See Also" links between related configs
    
  NEVER:
    - Document internal/private config options
    - Let docs drift from code defaults
```

**Output: `docs/CONFIG_REFERENCE.md`**

```markdown
# Configuration Reference

Complete reference for all configurable parameters in Agent Dashboard v2.7.0.

## Table of Contents

1. [Knowledge Graph](#knowledge-graph)
2. [Hybrid Retrieval](#hybrid-retrieval)
3. [Judge Panel](#judge-panel)
4. [Learning Orchestrator](#learning-orchestrator)
5. [Audit Trail](#audit-trail)
6. [Verification](#verification)
7. [Specifications](#specifications)

---

## Knowledge Graph

### EmbeddingConfig

Configuration for dual embedding generation.

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `semantic_dim` | int | 384 | 64-1536 | Dimension of text embeddings |
| `structural_dim` | int | 128 | 32-512 | Dimension of graph embeddings |
| `walk_length` | int | 80 | 10-200 | Node2Vec random walk length |
| `num_walks` | int | 10 | 1-50 | Number of walks per node |
| `p` | float | 1.0 | 0.1-10.0 | Return parameter (BFS vs DFS) |
| `q` | float | 1.0 | 0.1-10.0 | In-out parameter |
| `cache_ttl` | int | 3600 | 0-86400 | Embedding cache TTL in seconds |

**Example:**
```python
from src.knowledge.embeddings import EmbeddingConfig

config = EmbeddingConfig(
    semantic_dim=768,      # Larger model
    structural_dim=256,    # More graph detail
    walk_length=100,       # Longer walks
    cache_ttl=7200,        # 2 hour cache
)
```

---

## Hybrid Retrieval

### HybridRetrieverConfig

Configuration for hybrid vector+graph retrieval.

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `vector_weight` | float | 0.6 | 0.0-1.0 | Weight for vector similarity |
| `graph_weight` | float | 0.4 | 0.0-1.0 | Weight for graph expansion |
| `max_hops` | int | 2 | 1-5 | Maximum graph traversal depth |
| `min_similarity` | float | 0.3 | 0.0-1.0 | Minimum vector similarity threshold |
| `min_graph_score` | float | 0.1 | 0.0-1.0 | Minimum graph score threshold |
| `temporal_filter` | bool | False | - | Filter by entity validity dates |

**Presets:**
```python
# Semantic-focused (research queries)
SEMANTIC_PRESET = HybridRetrieverConfig(vector_weight=0.8, graph_weight=0.2)

# Relationship-focused (entity queries)  
GRAPH_PRESET = HybridRetrieverConfig(vector_weight=0.4, graph_weight=0.6, max_hops=3)

# Balanced (default)
BALANCED_PRESET = HybridRetrieverConfig()  # Uses defaults
```

### HybridRetrieverConfigV2 (with BM25)

Extended configuration for three-way hybrid retrieval.

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `vector_weight` | float | 0.4 | 0.0-1.0 | Weight for vector similarity |
| `graph_weight` | float | 0.3 | 0.0-1.0 | Weight for graph expansion |
| `bm25_weight` | float | 0.3 | 0.0-1.0 | Weight for keyword matching |
| `rrf_k` | int | 60 | 1-100 | RRF smoothing constant |
| `parallel` | bool | True | - | Run searches in parallel |

**Note:** Weights should sum to 1.0 for normalized scores.

---

## Judge Panel

### JudgeConfig

Configuration for individual judges in a panel.

| Parameter | Type | Default | Choices | Description |
|-----------|------|---------|---------|-------------|
| `judge_type` | JudgeType | - | ADVERSARIAL, RUBRIC, DOMAIN_EXPERT, SKEPTIC, END_USER | Type of judge |
| `weight` | float | 1.0 | 0.1-5.0 | Voting weight |
| `rubric` | dict | None | - | Custom rubric (for RUBRIC type) |
| `domain` | str | None | - | Domain expertise (for DOMAIN_EXPERT) |
| `skepticism_level` | float | 0.5 | 0.0-1.0 | How critical (for SKEPTIC) |

### PanelConfig

Configuration for judge panel orchestration.

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `min_judges` | int | 5 | 3-11 | Minimum judges (odd number) |
| `max_judges` | int | 7 | 5-15 | Maximum judges for high-stakes |
| `consensus_threshold` | float | 0.6 | 0.5-0.9 | Agreement threshold |
| `timeout_seconds` | int | 300 | 60-900 | Per-judge timeout |
| `allow_abstain` | bool | True | - | Allow judges to abstain |

---

## Learning Orchestrator

### LearningConfig

Configuration for neurosymbolic learning.

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `max_rules_to_apply` | int | 3 | 1-10 | Max rules per execution |
| `min_rule_effectiveness` | float | 0.5 | 0.0-1.0 | Threshold for rule application |
| `learn_from_high_quality` | bool | True | - | Extract rules from successes |
| `min_quality_for_learning` | float | 0.8 | 0.5-1.0 | Quality threshold for learning |
| `auto_prune` | bool | True | - | Automatically prune bad rules |
| `prune_interval_hours` | int | 24 | 1-168 | Hours between pruning |
| `min_effectiveness_threshold` | float | 0.4 | 0.1-0.9 | Prune rules below this |

---

## Environment Variables

All configs can be overridden via environment variables:

| Variable | Config | Description |
|----------|--------|-------------|
| `NESY_VECTOR_WEIGHT` | HybridRetrieverConfig.vector_weight | Override vector weight |
| `NESY_GRAPH_WEIGHT` | HybridRetrieverConfig.graph_weight | Override graph weight |
| `NESY_Z3_TIMEOUT` | SymbolicSolverConfig.timeout_ms | Z3 solver timeout |
| `NESY_EMBEDDING_MODEL` | EmbeddingConfig.model_name | Sentence transformer model |
| `NESY_AUDIT_PATH` | AuditConfig.storage_path | Audit trail storage location |
| `NESY_LEARNING_MIN_EFF` | LearningConfig.min_rule_effectiveness | Learning threshold |

**Example:**
```bash
export NESY_VECTOR_WEIGHT=0.7
export NESY_EMBEDDING_MODEL="all-mpnet-base-v2"
python -m src.cli search "machine learning"
```

---

## Config Validation

All configs validate on instantiation:

```python
from src.knowledge.retriever import HybridRetrieverConfig

# This raises ValueError
try:
    config = HybridRetrieverConfig(vector_weight=1.5)  # > 1.0
except ValueError as e:
    print(e)  # "vector_weight must be between 0.0 and 1.0"

# This raises ValueError  
try:
    config = HybridRetrieverConfig(max_hops=0)  # < 1
except ValueError as e:
    print(e)  # "max_hops must be positive"
```

---

*Auto-generated from codebase. Last updated: v2.7.0*
```

**Test File:** `tests/test_config_reference.py`

```python
"""
Tests for P4-002: Configuration Reference Tables.

Validates that documentation matches actual code defaults.
"""

import pytest
import re
from pathlib import Path


class TestConfigDocumentation:
    """Verify config docs match code."""
    
    def test_defaults_match_code(self):
        """Documented defaults should match code defaults."""
        from src.knowledge.retriever import HybridRetrieverConfig
        
        config = HybridRetrieverConfig()
        
        # Read docs
        docs = Path("docs/CONFIG_REFERENCE.md").read_text()
        
        # Extract documented default for vector_weight
        match = re.search(r'\| `vector_weight` \| float \| ([\d.]+)', docs)
        assert match, "vector_weight not found in docs"
        doc_default = float(match.group(1))
        
        assert doc_default == config.vector_weight, \
            f"Doc says {doc_default}, code says {config.vector_weight}"
    
    def test_all_public_params_documented(self):
        """All public config parameters should be documented."""
        from src.knowledge.retriever import HybridRetrieverConfig
        import inspect
        
        # Get all init parameters
        sig = inspect.signature(HybridRetrieverConfig.__init__)
        params = [p for p in sig.parameters if p != 'self']
        
        # Read docs
        docs = Path("docs/CONFIG_REFERENCE.md").read_text()
        
        for param in params:
            assert f"`{param}`" in docs, f"Parameter {param} not documented"
    
    def test_ranges_are_valid(self):
        """Documented ranges should be enforceable."""
        from src.knowledge.retriever import HybridRetrieverConfig
        
        # Test that values outside documented range raise errors
        with pytest.raises(ValueError):
            HybridRetrieverConfig(vector_weight=1.5)  # Above range
        
        with pytest.raises(ValueError):
            HybridRetrieverConfig(vector_weight=-0.1)  # Below range
    
    def test_env_vars_work(self, monkeypatch):
        """Documented env vars should override defaults."""
        monkeypatch.setenv("NESY_VECTOR_WEIGHT", "0.75")
        
        from src.knowledge.retriever import HybridRetrieverConfig
        
        # Config should read from env
        config = HybridRetrieverConfig.from_env()
        assert config.vector_weight == 0.75
```

**Acceptance Criteria:**
- [ ] CONFIG_REFERENCE.md generated with all configs
- [ ] Defaults extracted from code (not hardcoded)
- [ ] All public parameters documented
- [ ] Env var overrides documented and tested

---

### P4-003: Async Variants for I/O Operations

**Git Worktree:** `git worktree add ../agent-dashboard-async feature/async-variants`

**Specification File:** `specs/async_variants.spec`

```
AGENT async-converter:
  TIER: Sonnet
  
  TARGETS:
    - Database operations (SQLite, knowledge graph)
    - File I/O (audit trail, rule store)
    - External API calls (embedding models)
    
  PATTERN:
    # For each sync method, add async variant:
    def method(self, ...) -> T:
        """Sync version."""
        pass
        
    async def method_async(self, ...) -> T:
        """Async version for concurrent I/O."""
        pass
        
  ALWAYS:
    - Maintain backward compatibility (sync methods unchanged)
    - Use aiosqlite for database operations
    - Use aiofiles for file I/O
    - Document when to use async vs sync
    
  NEVER:
    - Remove or modify existing sync methods
    - Block the event loop in async methods
    - Mix sync and async in same call chain
```

**Implementation Pattern:**

```python
# src/knowledge/storage.py

import sqlite3
from typing import Optional, List
from contextlib import contextmanager

# Optional async imports
try:
    import aiosqlite
    ASYNC_AVAILABLE = True
except ImportError:
    ASYNC_AVAILABLE = False


class SQLiteGraphBackend(GraphStorageBackend):
    """
    SQLite-based knowledge graph storage.
    
    Provides both synchronous and asynchronous APIs for flexibility.
    Use sync methods for simple scripts, async for high-concurrency services.
    
    Example (sync):
        >>> backend = SQLiteGraphBackend("knowledge.db")
        >>> claim_id = backend.store_claim(claim)
        >>> retrieved = backend.get_claim(claim_id)
        
    Example (async):
        >>> backend = SQLiteGraphBackend("knowledge.db")
        >>> async with backend.async_session() as session:
        ...     claim_id = await backend.store_claim_async(claim)
        ...     retrieved = await backend.get_claim_async(claim_id)
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._sync_conn: Optional[sqlite3.Connection] = None
        self._async_conn: Optional[aiosqlite.Connection] = None
    
    # ==================== SYNC METHODS (existing) ====================
    
    @contextmanager
    def _get_connection(self):
        """Get sync database connection."""
        if self._sync_conn is None:
            self._sync_conn = sqlite3.connect(self.db_path)
        yield self._sync_conn
    
    def store_claim(self, claim: KGClaim) -> str:
        """Store a claim synchronously."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO claims (id, text, confidence, ...) VALUES (?, ?, ?, ...)",
                (claim.claim_id, claim.text, claim.confidence, ...)
            )
            conn.commit()
        return claim.claim_id
    
    def get_claim(self, claim_id: str) -> Optional[KGClaim]:
        """Get a claim synchronously."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM claims WHERE id = ?", (claim_id,))
            row = cursor.fetchone()
            return KGClaim.from_row(row) if row else None
    
    # ==================== ASYNC METHODS (new) ====================
    
    async def _get_async_connection(self) -> aiosqlite.Connection:
        """Get async database connection."""
        if not ASYNC_AVAILABLE:
            raise ImportError("aiosqlite required for async operations. pip install aiosqlite")
        if self._async_conn is None:
            self._async_conn = await aiosqlite.connect(self.db_path)
        return self._async_conn
    
    async def store_claim_async(self, claim: KGClaim) -> str:
        """
        Store a claim asynchronously.
        
        Use this method when storing claims in an async context (e.g., web server,
        concurrent processing). For simple scripts, use store_claim() instead.
        
        Args:
            claim: The KGClaim to store
            
        Returns:
            The claim ID
            
        Example:
            >>> async def process_claims(claims):
            ...     tasks = [backend.store_claim_async(c) for c in claims]
            ...     ids = await asyncio.gather(*tasks)
            ...     return ids
        """
        conn = await self._get_async_connection()
        await conn.execute(
            "INSERT INTO claims (id, text, confidence, ...) VALUES (?, ?, ?, ...)",
            (claim.claim_id, claim.text, claim.confidence, ...)
        )
        await conn.commit()
        return claim.claim_id
    
    async def get_claim_async(self, claim_id: str) -> Optional[KGClaim]:
        """
        Get a claim asynchronously.
        
        Args:
            claim_id: The claim ID to retrieve
            
        Returns:
            The KGClaim if found, None otherwise
        """
        conn = await self._get_async_connection()
        async with conn.execute("SELECT * FROM claims WHERE id = ?", (claim_id,)) as cursor:
            row = await cursor.fetchone()
            return KGClaim.from_row(row) if row else None
    
    async def find_claims_by_embedding_async(
        self,
        embedding: List[float],
        limit: int = 10,
        min_similarity: float = 0.5,
    ) -> List[Tuple[KGClaim, float]]:
        """
        Find claims by embedding similarity asynchronously.
        
        Useful for concurrent search across multiple queries.
        
        Example:
            >>> queries = ["Python ML", "JavaScript web", "Rust systems"]
            >>> embeddings = [embed(q) for q in queries]
            >>> results = await asyncio.gather(*[
            ...     backend.find_claims_by_embedding_async(e)
            ...     for e in embeddings
            ... ])
        """
        conn = await self._get_async_connection()
        # Implementation...
        pass
    
    # ==================== CLEANUP ====================
    
    def close(self):
        """Close sync connection."""
        if self._sync_conn:
            self._sync_conn.close()
            self._sync_conn = None
    
    async def close_async(self):
        """Close async connection."""
        if self._async_conn:
            await self._async_conn.close()
            self._async_conn = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close_async()
```

**Test File:** `tests/test_async_variants.py`

```python
"""
Tests for P4-003: Async Variants.

Validates async methods work correctly and maintain parity with sync versions.
"""

import pytest
import asyncio
from typing import List

# Skip all tests if aiosqlite not available
aiosqlite = pytest.importorskip("aiosqlite")


class TestAsyncStorage:
    """Test async storage operations."""
    
    @pytest.mark.asyncio
    async def test_store_claim_async(self, async_backend, sample_claim):
        """Async store works like sync store."""
        claim_id = await async_backend.store_claim_async(sample_claim)
        assert claim_id == sample_claim.claim_id
    
    @pytest.mark.asyncio
    async def test_get_claim_async(self, async_backend, sample_claim):
        """Async get retrieves stored claims."""
        await async_backend.store_claim_async(sample_claim)
        retrieved = await async_backend.get_claim_async(sample_claim.claim_id)
        
        assert retrieved is not None
        assert retrieved.text == sample_claim.text
    
    @pytest.mark.asyncio
    async def test_concurrent_stores(self, async_backend, sample_claims):
        """Multiple concurrent stores work correctly."""
        tasks = [async_backend.store_claim_async(c) for c in sample_claims]
        ids = await asyncio.gather(*tasks)
        
        assert len(ids) == len(sample_claims)
        assert len(set(ids)) == len(ids)  # All unique
    
    @pytest.mark.asyncio
    async def test_concurrent_searches(self, async_backend, sample_embeddings):
        """Multiple concurrent searches work correctly."""
        tasks = [
            async_backend.find_claims_by_embedding_async(e)
            for e in sample_embeddings
        ]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == len(sample_embeddings)


class TestAsyncSyncParity:
    """Verify async and sync methods produce same results."""
    
    @pytest.mark.asyncio
    async def test_store_parity(self, backend, async_backend, sample_claim):
        """Sync and async store produce same result."""
        # Store via sync
        sync_id = backend.store_claim(sample_claim)
        
        # Retrieve via async
        async_claim = await async_backend.get_claim_async(sync_id)
        
        assert async_claim is not None
        assert async_claim.text == sample_claim.text
    
    @pytest.mark.asyncio
    async def test_search_parity(self, backend, async_backend, sample_embedding):
        """Sync and async search produce same results."""
        sync_results = backend.find_claims_by_embedding(sample_embedding, limit=5)
        async_results = await async_backend.find_claims_by_embedding_async(
            sample_embedding, limit=5
        )
        
        sync_ids = [r[0].claim_id for r in sync_results]
        async_ids = [r[0].claim_id for r in async_results]
        
        assert sync_ids == async_ids


class TestAsyncContextManager:
    """Test async context manager."""
    
    @pytest.mark.asyncio
    async def test_context_manager_cleanup(self, tmp_path):
        """Context manager closes connection on exit."""
        from src.knowledge.storage import SQLiteGraphBackend
        
        db_path = tmp_path / "test.db"
        
        async with SQLiteGraphBackend(str(db_path)) as backend:
            await backend.store_claim_async(sample_claim)
        
        # Connection should be closed
        assert backend._async_conn is None


class TestAsyncNotAvailable:
    """Test graceful handling when aiosqlite not installed."""
    
    def test_import_error_message(self, monkeypatch):
        """Clear error message when async deps missing."""
        # Simulate aiosqlite not available
        monkeypatch.setattr("src.knowledge.storage.ASYNC_AVAILABLE", False)
        
        from src.knowledge.storage import SQLiteGraphBackend
        backend = SQLiteGraphBackend("test.db")
        
        with pytest.raises(ImportError, match="aiosqlite required"):
            asyncio.run(backend.store_claim_async(sample_claim))


# Fixtures
@pytest.fixture
def async_backend(tmp_path):
    """Create async-capable backend."""
    from src.knowledge.storage import SQLiteGraphBackend
    return SQLiteGraphBackend(str(tmp_path / "test.db"))


@pytest.fixture
def sample_claims():
    """Generate sample claims for testing."""
    from src.knowledge.graph import KGClaim
    return [
        KGClaim(claim_id=f"c{i}", text=f"Claim {i}", confidence=0.9, source_url="http://example.com")
        for i in range(10)
    ]
```

**Acceptance Criteria:**
- [ ] Async variants for all I/O-bound operations
- [ ] Backward compatibility maintained (sync unchanged)
- [ ] Graceful fallback when aiosqlite not installed
- [ ] Parity tests pass (async == sync results)
- [ ] Context manager support for cleanup

---

## 📊 P4 Success Metrics

| Feature | Metric | Target |
|---------|--------|--------|
| Docstring Examples | Methods with examples | 100% public methods |
| Docstring Examples | Doctest pass rate | 100% |
| Config Reference | Parameters documented | 100% |
| Config Reference | Defaults match code | 100% |
| Async Variants | Operations covered | All I/O methods |
| Async Variants | Parity with sync | 100% same results |

---

## 🚀 Updated Execution Plan

### Phase 6: P4 Implementation (Days 13-14)

```bash
# After P3 merges
git worktree add ../agent-dashboard-docs feature/docstring-examples
git worktree add ../agent-dashboard-config-docs feature/config-reference
git worktree add ../agent-dashboard-async feature/async-variants

# Terminal 1: Docstring Examples
cd ../agent-dashboard-docs
claude "Implement P4-001 following specs/docstring_examples.spec. Add runnable examples to all priority modules."

# Terminal 2: Config Reference
cd ../agent-dashboard-config-docs
claude "Implement P4-002 following specs/config_reference.spec. Generate CONFIG_REFERENCE.md from code."

# Terminal 3: Async Variants
cd ../agent-dashboard-async
claude "Implement P4-003 following specs/async_variants.spec. Add async methods maintaining backward compat."
```

### Updated Timeline

| Phase | Days | Features |
|-------|------|----------|
| Research | 1 | Parallel research agents |
| P1 | 2-5 | Dual embeddings, BM25, Install |
| P2 | 6-8 | Leiden, HNSW, Token counting |
| P3 | 9-10 | Visualization, Re-ranking, Benchmarks |
| **P4** | **13-14** | **Docstrings, Config docs, Async** |
| Integration | 15-16 | Judge review, Release |

---

*Generated for Agent Dashboard v2.7.0 Enhancement Implementation*
*Following TDD workflow with tiered agent orchestration*
*Updated with P4 recommendations from Judge Panel review*