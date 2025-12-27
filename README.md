# Agent Dashboard v2.7.0

> **Quick Install:** `git clone https://github.com/Koplal/agent-dashboard.git && cd agent-dashboard && ./scripts/install.sh`
>
> **Cross-Platform Install:** `python scripts/install.py`
>
> **Platform-specific instructions:** See [INSTALL.md](INSTALL.md)
> **Troubleshooting:** See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

**Real-time monitoring and orchestration for Claude Code multi-agent workflows with advanced knowledge graph retrieval.**

A comprehensive multi-agent workflow framework implementing **Test-Driven Development (TDD)** with tiered model architecture (Opus/Sonnet/Haiku), **neurosymbolic knowledge management**, cost governance, and six-layer validation. Built for production-grade AI workflows where tests define correctness.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-green.svg)
![Claude](https://img.shields.io/badge/Claude-Code-purple.svg)
![Tests](https://img.shields.io/badge/tests-1%2C240%20passing-brightgreen.svg)

---

## Table of Contents

- [What's New in v2.7.0](#-whats-new-in-v270---knowledge-enhanced-retrieval)
- [Features](#-features)
- [Quick Start](#-quick-start)
- [Knowledge Graph & Retrieval](#-knowledge-graph--retrieval)
- [Multi-Agent Demo Workflow](#-multi-agent-demo-workflow)
- [Architecture](#-architecture)
- [Agent Registry](#-agent-registry-22-agents)
- [Manual Testing](#-manual-testing)
- [API Reference](#-api-reference)
- [Configuration](#-configuration)
- [Testing](#-testing)
- [Documentation](#-documentation)
- [License](#-license)

---

## What's New in v2.7.0 - Knowledge-Enhanced Retrieval

The **experiment/neuro-symbolic** branch introduces major enhancements for knowledge management, hybrid retrieval, and production-ready testing infrastructure.

### Key Highlights

| Feature | Description | Tests |
|---------|-------------|-------|
| **Hybrid Retrieval System** | BM25 + Vector + Graph fusion with RRF ranking | 110+ |
| **Knowledge Graph Layer** | Entity tracking, temporal validity, provenance | 82+ |
| **Community Detection** | Leiden algorithm for graph clustering | 21 |
| **HNSW Vector Index** | Sub-linear approximate nearest neighbor search | 33 |
| **Embedding Visualization** | Interactive 2D/3D plots with UMAP/PCA | 21 |
| **Cross-Encoder Re-Ranking** | Semantic re-ranking for improved precision | 22 |
| **Comprehensive Manual Testing** | 25 test cases, fixtures, execution scripts | 30 files |

**Total New Tests:** 445+ (bringing total to 1,240+)

### P1: Core Retrieval Enhancements

#### Dual Embedding Strategy (`src/knowledge/embeddings.py`)
```python
from src.knowledge.embeddings import DualEmbedder, EmbeddingCache

# Combines semantic + structural embeddings
embedder = DualEmbedder(cache=EmbeddingCache(default_ttl=3600))
embedding = embedder.embed_text("Python machine learning frameworks")
```

- **Semantic embeddings** via sentence-transformers (or hash fallback)
- **Structural embeddings** via Node2Vec graph walks
- **Configurable weights** (default: 70% semantic, 30% structural)
- **TTL-based caching** to prevent memory bloat

#### BM25 Three-Way Hybrid Search (`src/knowledge/bm25.py`)
```python
from src.knowledge.bm25 import BM25Index, HybridRetrieverV2

# Create and populate BM25 index
index = BM25Index()
index.add_document("doc1", "REST API best practices")
index.add_document("doc2", "Database connection pooling")

# Search with BM25
results = index.search("API design", limit=10)
```

- **Porter Stemmer** with intelligent caching
- **Reciprocal Rank Fusion (RRF)** for multi-signal combination
- **Configurable k parameter** for RRF (default: 60)
- **54 unit tests** covering all edge cases

#### Hierarchical Session Summarizer (`src/ledger/summarizer.py`)
```python
from src.ledger.summarizer import HierarchicalSummarizer, SummaryLevel

summarizer = HierarchicalSummarizer(gap_threshold_minutes=90)
phases = summarizer.detect_phases(task_list)
session_summary = summarizer.summarize_session(phase_summaries)
```

- **4-level hierarchy:** SESSION → PHASE → TASK → ATOMIC
- **Phase detection** based on time gaps (configurable threshold)
- **Token-budgeted context loading** for LLM queries
- **37 unit tests** with comprehensive coverage

#### Entity-Aware Provenance (`src/audit/provenance.py`)
```python
from src.audit.provenance import EntityProvenanceTracker, EntityRole
from src.knowledge.graph import Entity, EntityType

tracker = EntityProvenanceTracker()
entity = Entity(name="UserService", entity_type=EntityType.CLASS)
tracker.record(entity, EntityRole.SUBJECT, "audit-entry-001")

# Query provenance
history = tracker.get_entities_by_name("UserService")
timeline = tracker.get_entity_timeline("UserService")
```

- **Full entity lifecycle tracking** across sessions
- **Role-based classification** (SUBJECT, OBJECT, INSTRUMENT)
- **Integrity verification** with hash chains
- **48 unit tests** for provenance tracking

### P2: Advanced Knowledge Features

#### Leiden Community Detection (`src/knowledge/community.py`)
```python
from src.knowledge.community import CommunityDetector, CommunityConfig

detector = CommunityDetector(CommunityConfig(resolution=1.0))
result = detector.detect(graph)

print(f"Found {len(result.communities)} communities")
print(f"Modularity: {result.modularity:.3f}")
```

- **Leiden algorithm** (faster than Louvain)
- **Hierarchical community structure**
- **Modularity scoring** for partition quality
- **Graceful fallback** when igraph unavailable

#### HNSW Vector Index (`src/knowledge/hnsw_index.py`)
```python
from src.knowledge.hnsw_index import HNSWIndex, HNSWConfig

index = HNSWIndex(HNSWConfig(dim=384, max_elements=100000))
index.add("doc1", embedding_vector)
results = index.search(query_vector, k=10)
index.save("index.bin")
```

- **Approximate nearest neighbor** with <10ms p50 latency
- **Incremental updates** without full rebuild
- **Filtered search** with ID whitelist/blacklist
- **Persistence** with atomic save/load

#### Tiered Token Counting (`src/utils/tiered_token_counter.py`)
```python
from src.utils.tiered_token_counter import TieredTokenCounter

counter = TieredTokenCounter()
result = counter.count("Hello, world!")
print(f"Tokens: {result.count}, Method: {result.method}, Confidence: {result.confidence}")
```

- **Fallback chain:** xenova → tiktoken → character estimation
- **Never fails** - always returns estimation
- **Result caching** with configurable TTL
- **Batch counting** support

### P3: Visualization & Benchmarks

#### Graph Embedding Visualization (`src/visualization/embedding_viz.py`)
```python
from src.visualization.embedding_viz import EmbeddingVisualizer

visualizer = EmbeddingVisualizer()
fig = visualizer.visualize(embeddings, labels=labels, dimensions=2)
visualizer.save_html(fig, "embeddings.html")
```

- **Interactive Plotly charts** (2D and 3D)
- **UMAP dimensionality reduction** with PCA fallback
- **Cluster color mapping** for community visualization
- **HTML and JSON export**

#### Cross-Encoder Re-Ranking (`src/knowledge/reranker.py`)
```python
from src.knowledge.reranker import ReRanker

reranker = ReRanker()
ranked = reranker.rerank(query="Python API", candidates=documents, top_k=5)
```

- **Cross-encoder scoring** via sentence-transformers
- **Jaccard similarity fallback** when unavailable
- **Batch re-ranking** for efficiency
- **22 unit tests**

#### Benchmark Suite (`tests/benchmarks/`)
```bash
python -m pytest tests/benchmarks/ -v --benchmark-only
```

- **Vector search latency** (p50/p95/p99)
- **BM25 indexing throughput**
- **Hybrid retrieval end-to-end**
- **Memory usage tracking**

### P4: Developer Experience

#### Enhanced Docstrings
All public methods now include runnable examples:
```python
def retrieve(self, query: str, limit: int = 10) -> List[RetrievalResult]:
    """
    Retrieve relevant claims using hybrid search.

    Example:
        >>> retriever = HybridRetriever(storage)
        >>> results = retriever.retrieve("machine learning frameworks")
        >>> for r in results:
        ...     print(f"{r.claim_id}: {r.score:.3f}")
    """
```

#### Configuration Reference (`docs/CONFIG_REFERENCE.md`)
Complete documentation of all configurable parameters:
- Default values extracted from code
- Valid ranges and choices
- Environment variable overrides

#### Async Variants (`src/knowledge/storage.py`)
```python
async with SQLiteGraphBackend(":memory:") as storage:
    await storage.store_claim_async(claim)
    result = await storage.get_claim_async(claim_id)
```

- **aiosqlite-based** async database operations
- **Graceful fallback** when aiosqlite unavailable
- **Backward compatible** - sync methods unchanged

---

## Features

### Core Capabilities

| Feature | Description |
|---------|-------------|
| **TDD Workflow** | Test-Driven Development with immutable tests |
| **Multi-Agent Orchestration** | 22 specialized agents across 3 tiers |
| **Hybrid Retrieval** | BM25 + Vector + Graph fusion |
| **Knowledge Graph** | Entity tracking with provenance |
| **Real-time Monitoring** | Web Dashboard with WebSocket updates |
| **Community Detection** | Leiden algorithm clustering |
| **7-Phase Workflow** | SPEC → TEST → IMPLEMENT → VALIDATE → REVIEW |
| **Cost Governance** | Circuit breaker with budget enforcement |

### Test Coverage

| Category | Tests | Status |
|----------|-------|--------|
| Core Modules | 249 | Passing |
| NESY Modules | 536 | Passing |
| P1-P4 Enhancements | 445 | Passing |
| **Total** | **1,240** | **98.9%** |

---

## Quick Start

### Prerequisites

| Requirement | Version | Check Command |
|-------------|---------|---------------|
| Python | 3.10+ | `python --version` |
| pip | Latest | `pip --version` |

### Installation

```bash
# Clone the repository
git clone https://github.com/Koplal/agent-dashboard.git
cd agent-dashboard

# Switch to neuro-symbolic branch
git checkout experiment/neuro-symbolic

# Install dependencies
pip install -r requirements.txt

# Run the dashboard
python src/web_server.py
```

### Verify Installation

```bash
# Run tests
python -m pytest tests/ -v --tb=short

# Expected: 1,240 passed, 14 skipped
```

### Quick Demo

```bash
# Start dashboard in Terminal 1
python src/web_server.py

# Run demo workflow in Terminal 2
python scripts/demo_workflow.py
```

---

## Knowledge Graph & Retrieval

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    KNOWLEDGE LAYER                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ BM25 Index   │  │ HNSW Vector  │  │ Graph Store  │           │
│  │ (Keyword)    │  │ (Semantic)   │  │ (Structure)  │           │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘           │
│         │                 │                 │                    │
│         └────────────┬────┴────────────────┘                    │
│                      │                                           │
│              ┌───────▼───────┐                                   │
│              │  RRF Fusion   │  (Reciprocal Rank Fusion)        │
│              └───────┬───────┘                                   │
│                      │                                           │
│              ┌───────▼───────┐                                   │
│              │  Re-Ranker    │  (Cross-Encoder, optional)       │
│              └───────┬───────┘                                   │
│                      │                                           │
│              ┌───────▼───────┐                                   │
│              │ Final Results │                                   │
│              └───────────────┘                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Usage Example

```python
from src.knowledge.bm25 import BM25Index
from src.knowledge.embeddings import DualEmbedder
from src.audit.provenance import EntityProvenanceTracker

# 1. Create knowledge base
bm25 = BM25Index()
embedder = DualEmbedder()
provenance = EntityProvenanceTracker()

# 2. Add claims
bm25.add_document("claim-001", "REST APIs should use proper HTTP methods")
bm25.add_document("claim-002", "Use JWT for authentication")

# 3. Search
results = bm25.search("API authentication", limit=5)
for doc_id, score in results:
    print(f"  [{score:.3f}] {doc_id}")

# 4. Track provenance
from src.knowledge.graph import Entity, EntityType
entity = Entity(name="JWT", entity_type=EntityType.OTHER)
provenance.record(entity, EntityRole.SUBJECT, "claim-002")
```

---

## Multi-Agent Demo Workflow

The demo workflow (`scripts/demo_workflow.py`) demonstrates real multi-agent orchestration:

### Workflow Phases

```
Phase 1: Strategic Planning (Opus)
  └── PlannerAgent creates 3-phase implementation plan

Phase 2: Parallel Research (Sonnet)
  ├── researcher-api ─────┐
  ├── researcher-database ┼── 3 agents in PARALLEL
  └── researcher-security ┘

Phase 3: Parallel Implementation (Sonnet)
  ├── implementer-api ──────┐
  ├── implementer-database ─┼── 3 agents in PARALLEL
  └── implementer-auth ─────┘

Phase 4: Parallel Validation (Haiku + Opus)
  ├── validator ─┬── 2 agents in PARALLEL
  └── critic ────┘

Phase 5: Knowledge Synthesis (Opus)
  └── SynthesisAgent compiles session knowledge
```

### Run the Demo

```bash
# Start dashboard
python src/web_server.py

# Run workflow (in another terminal)
python scripts/demo_workflow.py
```

### Expected Output

```
Session ID: DEMO-20251227-XXXXXX
Phases completed: 5
Agents executed: 10 (parallel workflow)
Knowledge claims: 17
Entities tracked: 30
Artifacts produced: 8

SUCCESS CRITERIA: 7/7 passed
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AGENT DASHBOARD v2.7.0                        │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │  Web Dashboard  │  │  Terminal TUI   │  │  REST API       │     │
│  │  (port 4200)    │  │  (Rich)         │  │  + WebSocket    │     │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘     │
│           └────────────────────┼────────────────────┘               │
│                                │                                     │
│  ┌─────────────────────────────┴─────────────────────────────┐     │
│  │                 KNOWLEDGE LAYER (v2.7.0)                   │     │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │     │
│  │  │  BM25    │  │  HNSW    │  │  Graph   │  │ Embedder │   │     │
│  │  │  Index   │  │  Vector  │  │  Store   │  │  Dual    │   │     │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │     │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │     │
│  │  │Community │  │Provenance│  │Summarizer│  │ ReRanker │   │     │
│  │  │ Leiden   │  │ Tracker  │  │Hierarchic│  │CrossEnc. │   │     │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │     │
│  └────────────────────────────────────────────────────────────┘     │
│                                │                                     │
│  ┌─────────────────────────────┴─────────────────────────────┐     │
│  │                    WORKFLOW ENGINE                         │     │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │     │
│  │  │ Planner  │→ │ Tester   │→ │Implementer│→ │ Validator│   │     │
│  │  │ (Opus)   │  │ (Haiku)  │  │ (Sonnet)  │  │ (Haiku)  │   │     │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │     │
│  │                                                            │     │
│  │  ┌──────────────────────────────────────────────────────┐ │     │
│  │  │  Cost Circuit Breaker │ Six-Layer Validation Stack   │ │     │
│  │  └──────────────────────────────────────────────────────┘ │     │
│  └────────────────────────────────────────────────────────────┘     │
│                                │                                     │
│  ┌─────────────────────────────┴─────────────────────────────┐     │
│  │  SQLite Database │ Event Hooks │ Token Tracking           │     │
│  └────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Agent Registry (22 Agents)

### Tier 1 - Opus (Strategic/Quality) `$$$`

| Agent | Role | Description |
|-------|------|-------------|
| `orchestrator` | Coordinator | Multi-agent workflow coordination |
| `synthesis` | Combiner | Research output synthesizer |
| `critic` | Challenger | Quality assurance, devil's advocate |
| `planner` | Strategist | Read-only planning (PLAN MODE) |

### Tier 2 - Sonnet (Analysis/Research) `$$`

| Agent | Role | Description |
|-------|------|-------------|
| `researcher` | Analyst | Documentation-based research |
| `perplexity-researcher` | Search | Real-time web search |
| `implementer` | Builder | Execute approved plans |
| `panel-coordinator` | Coordinator | Orchestrates judge panels |
| `judge-*` | Evaluators | Technical, completeness, practicality |

### Tier 3 - Haiku (Execution/Routine) `$`

| Agent | Role | Description |
|-------|------|-------------|
| `web-search-researcher` | Searcher | Broad web searches |
| `summarizer` | Compressor | Output compression |
| `test-writer` | Tester | Automated test generation |
| `validator` | Validator | Six-layer validation |

---

## Manual Testing

### Test Infrastructure

The project includes comprehensive manual testing infrastructure:

```
tests/
├── fixtures/                    # Test data
│   ├── minimal_kg.json         # 10 claims (smoke tests)
│   ├── standard_kg.json        # 1,000 claims (integration)
│   ├── large_kg.json           # 10,000 claims (performance)
│   └── test_queries.json       # 100 queries with expected results

scripts/manual_tests/
├── run_smoke_tests.py          # Automated smoke runner
├── run_performance_tests.py    # Performance benchmarks
├── websocket_load_test.py      # WebSocket scalability
└── check_test_environment.py   # Environment validation

docs/testing/
├── SMOKE_TEST_GUIDE.md         # Step-by-step procedures
├── PERFORMANCE_TEST_GUIDE.md   # Performance testing
├── TROUBLESHOOTING_GUIDE.md    # Common issues
└── checklists/                 # Deployment checklists
```

### Running Manual Tests

```bash
# 1. Verify environment
python scripts/manual_tests/check_test_environment.py --verbose

# 2. Run smoke tests (5 tests, ~15 min)
python scripts/manual_tests/run_smoke_tests.py --verbose

# 3. Run performance tests (4 tests)
python scripts/manual_tests/run_performance_tests.py --verbose

# 4. WebSocket load test (100 clients)
python scripts/manual_tests/websocket_load_test.py --clients 100 --duration 30
```

### Test Results

| Suite | Tests | Status |
|-------|-------|--------|
| Smoke Tests | 5/5 | PASS |
| Performance Tests | 4/4 | PASS |
| WebSocket Load | 100 clients | 51 events/sec |
| Integration Tests | 5/5 | PASS |

---

## API Reference

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web dashboard |
| `/events` | POST | Receive events from hooks |
| `/api/events` | GET | Get recent events |
| `/api/sessions` | GET | Get active sessions |
| `/api/stats` | GET | Get statistics |
| `/health` | GET | Health check |
| `/ws` | WebSocket | Live updates |

### Knowledge Endpoints (v2.7.0)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/knowledge/search` | POST | Hybrid search |
| `/api/knowledge/claims` | GET/POST | Manage claims |
| `/api/knowledge/entities` | GET | Get tracked entities |

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_DASHBOARD_URL` | `http://127.0.0.1:4200` | Dashboard URL |
| `AGENT_NAME` | `claude` | Agent identifier |
| `AGENT_MODEL` | `sonnet` | Model tier |

### Configuration Reference

See `docs/CONFIG_REFERENCE.md` for complete parameter documentation.

---

## Testing

### Running Tests

```bash
# All tests
python -m pytest tests/ -v

# Specific module
python -m pytest tests/test_bm25.py -v

# With coverage
python -m pytest tests/ --cov=src --cov-report=html
```

### Test Categories

| Category | Files | Tests |
|----------|-------|-------|
| Core | 9 | 249 |
| NESY | 10 | 536 |
| P1-P4 | 14 | 445 |
| Benchmarks | 1 | 6 |
| **Total** | **34** | **1,240** |

---

## Documentation

| Document | Description |
|----------|-------------|
| [README.md](README.md) | This file |
| [docs/CONFIG_REFERENCE.md](docs/CONFIG_REFERENCE.md) | Configuration parameters |
| [docs/MANUAL_TESTING_STRATEGY.md](docs/MANUAL_TESTING_STRATEGY.md) | Manual test procedures |
| [docs/testing/](docs/testing/) | Test guides and checklists |
| [docs/NESY-ARCHITECTURE.md](docs/NESY-ARCHITECTURE.md) | Neurosymbolic module docs |

---

## Repository Structure (v2.7.0)

```
agent-dashboard/
├── src/
│   ├── knowledge/              # Knowledge graph layer
│   │   ├── graph.py            # Entity, Claim, Graph types
│   │   ├── storage.py          # SQLite backend + async
│   │   ├── bm25.py             # BM25 index + hybrid retriever
│   │   ├── embeddings.py       # Dual embedding strategy
│   │   ├── retriever.py        # Hybrid vector-graph retriever
│   │   ├── community.py        # Leiden community detection
│   │   ├── hnsw_index.py       # HNSW vector index
│   │   └── reranker.py         # Cross-encoder re-ranking
│   ├── ledger/
│   │   └── summarizer.py       # Hierarchical session summarizer
│   ├── audit/
│   │   └── provenance.py       # Entity-aware provenance
│   ├── utils/
│   │   └── tiered_token_counter.py  # Fallback token counting
│   ├── visualization/
│   │   └── embedding_viz.py    # Graph embedding visualization
│   └── web_server.py           # Dashboard server
├── tests/
│   ├── test_bm25.py            # 54 tests
│   ├── test_dual_embeddings.py # 36 tests
│   ├── test_hybrid_retriever.py # 56 tests
│   ├── test_summarizer.py      # 37 tests
│   ├── test_entity_provenance.py # 48 tests
│   ├── test_community.py       # 21 tests
│   ├── test_hnsw_index.py      # 33 tests
│   ├── test_tiered_token_counter.py # 29 tests
│   ├── test_embedding_viz.py   # 21 tests
│   ├── test_reranker.py        # 22 tests
│   ├── benchmarks/             # Performance benchmarks
│   └── fixtures/               # Test data
├── scripts/
│   ├── demo_workflow.py        # Multi-agent demo
│   ├── install.py              # Cross-platform installer
│   └── manual_tests/           # Manual test scripts
├── docs/
│   ├── testing/                # Test guides
│   ├── CONFIG_REFERENCE.md     # Configuration docs
│   └── MANUAL_TESTING_STRATEGY.md
├── agents/                     # 22 agent definitions
├── TEST_REPORT.html            # HTML test report
├── TEST_REPORT.md              # Markdown test report
└── README.md                   # This file
```

---

## Version History

| Version | Date | Highlights |
|---------|------|------------|
| **2.7.0** | Dec 2024 | Hybrid retrieval, HNSW, Leiden, manual testing |
| 2.6.0 | Dec 2024 | Robust installation, NESY modules |
| 2.5.0 | Dec 2024 | 5-judge panel minimum, agent optimization |
| 2.4.x | Dec 2024 | Collapsible projects, dynamic viewport |
| 2.3.0 | Dec 2024 | Project grouping, responsive dashboard |

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- [Anthropic](https://anthropic.com) - Claude models
- [Rich](https://github.com/Textualize/rich) - Terminal formatting
- [sentence-transformers](https://www.sbert.net/) - Embeddings
- [python-igraph](https://igraph.org/python/) - Graph algorithms

---

**Built for quality-focused AI workflows with knowledge-enhanced retrieval.**
