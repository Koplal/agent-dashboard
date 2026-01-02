# Agent Dashboard Multi-Project Implementation Guide

## Overview

This guide explains how to implement and use the Agent Dashboard for multiple distinct projects while maintaining complete isolation of knowledge graphs, embeddings, and learned rules. Each project maintains its own knowledge base that remains unique and relevant to its specific domain.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Project Isolation Strategies](#project-isolation-strategies)
3. [Quick Start: Single Project](#quick-start-single-project)
4. [Multi-Project Setup](#multi-project-setup)
5. [Configuration Management](#configuration-management)
6. [Knowledge Graph Isolation](#knowledge-graph-isolation)
7. [Embedding Strategy per Project](#embedding-strategy-per-project)
8. [Audit Trail Separation](#audit-trail-separation)
9. [Best Practices](#best-practices)
10. [Example: Three-Project Setup](#example-three-project-setup)
11. [Migration and Backup](#migration-and-backup)
12. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

The Agent Dashboard uses a layered architecture that supports project isolation at multiple levels:

```
┌─────────────────────────────────────────────────────────────┐
│                    Project Configuration                     │
│  (project_id, data_dir, embedding_config, retrieval_config) │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  Project A  │  │  Project B  │  │  Project C  │        │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤        │
│  │ knowledge.db│  │ knowledge.db│  │ knowledge.db│        │
│  │ embeddings/ │  │ embeddings/ │  │ embeddings/ │        │
│  │ audit/      │  │ audit/      │  │ audit/      │        │
│  │ rules/      │  │ rules/      │  │ rules/      │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                    Shared Components                         │
│        (models, validators, judge panels, agents)           │
└─────────────────────────────────────────────────────────────┘
```

### Key Isolation Points

| Component | Isolation Method | Storage Location |
|-----------|------------------|------------------|
| Knowledge Graph | Separate SQLite database | `{project_dir}/knowledge.db` |
| Embeddings | Separate HNSW index | `{project_dir}/embeddings/` |
| Audit Trail | Separate log directory | `{project_dir}/audit/` |
| Learned Rules | Separate rule store | `{project_dir}/rules/` |
| BM25 Index | Per-project in memory | Rebuilt on load |

---

## Project Isolation Strategies

### Strategy 1: Directory-Based Isolation (Recommended)

Each project gets its own directory with all data stored within:

```
~/agent-dashboard-projects/
├── project-alpha/
│   ├── knowledge.db
│   ├── embeddings/
│   │   ├── hnsw_index.bin
│   │   └── structural_embeddings.pkl
│   ├── audit/
│   │   └── audit_trail.jsonl
│   ├── rules/
│   │   └── learned_rules.json
│   └── config.yaml
├── project-beta/
│   └── ... (same structure)
└── project-gamma/
    └── ... (same structure)
```

### Strategy 2: Database-Based Isolation

Use separate SQLite databases with project prefix:

```python
# Project-specific database paths
PROJECT_DATABASES = {
    "alpha": "~/data/alpha_knowledge.db",
    "beta": "~/data/beta_knowledge.db",
    "gamma": "~/data/gamma_knowledge.db",
}
```

### Strategy 3: Schema-Based Isolation (Advanced)

Use table prefixes within a single database (useful for shared infrastructure):

```sql
-- Project Alpha tables
CREATE TABLE alpha_claims (...);
CREATE TABLE alpha_entities (...);

-- Project Beta tables
CREATE TABLE beta_claims (...);
CREATE TABLE beta_entities (...);
```

---

## Quick Start: Single Project

### Step 1: Create Project Directory

```bash
mkdir -p ~/projects/my-research-project
cd ~/projects/my-research-project
```

### Step 2: Initialize Project Configuration

Create `config.yaml`:

```yaml
# Project Configuration
project:
  id: "my-research-project"
  name: "My Research Project"
  description: "Knowledge base for AI research papers"
  
# Storage Configuration
storage:
  type: "sqlite"
  database_path: "./knowledge.db"
  
# Embedding Configuration
embeddings:
  semantic_model: "all-MiniLM-L6-v2"
  semantic_dim: 384
  structural_dim: 128
  semantic_weight: 0.7
  structural_weight: 0.3

# Retrieval Configuration
retrieval:
  vector_weight: 0.4
  graph_weight: 0.3
  bm25_weight: 0.3
  max_results: 20
  min_similarity: 0.3

# Audit Configuration
audit:
  enabled: true
  storage_path: "./audit/"
  retention_days: 90
```

### Step 3: Initialize Knowledge Graph

```python
#!/usr/bin/env python3
"""Initialize a new project knowledge graph."""

from pathlib import Path
import yaml

# Add agent-dashboard to path
import sys
sys.path.insert(0, "/path/to/agent-dashboard")

from src.knowledge.storage import SQLiteGraphBackend
from src.knowledge.manager import KnowledgeGraphManager, default_embedding_function
from src.knowledge.retriever import HybridRetriever, HybridRetrieverConfig
from src.knowledge.embeddings import DualEmbedder, DualEmbeddingConfig, EmbeddingCache


def init_project(config_path: str = "config.yaml"):
    """Initialize project from configuration."""
    
    # Load configuration
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    project_id = config["project"]["id"]
    db_path = Path(config["storage"]["database_path"])
    
    # Create directories
    db_path.parent.mkdir(parents=True, exist_ok=True)
    Path(config["audit"]["storage_path"]).mkdir(parents=True, exist_ok=True)
    
    # Initialize storage backend
    storage = SQLiteGraphBackend(str(db_path))
    
    # Initialize embedding configuration
    embed_config = DualEmbeddingConfig(
        semantic_weight=config["embeddings"]["semantic_weight"],
        structural_weight=config["embeddings"]["structural_weight"],
        embedding_dim=config["embeddings"]["semantic_dim"],
        node2vec_dimensions=config["embeddings"]["structural_dim"],
    )
    
    # Initialize embedder with cache
    cache = EmbeddingCache(default_ttl=3600.0)
    embedder = DualEmbedder(config=embed_config, cache=cache)
    
    # Initialize retriever configuration
    retriever_config = HybridRetrieverConfig(
        vector_weight=config["retrieval"]["vector_weight"],
        graph_weight=config["retrieval"]["graph_weight"],
        min_similarity=config["retrieval"]["min_similarity"],
    )
    
    # Initialize knowledge graph manager
    manager = KnowledgeGraphManager(
        storage=storage,
        embedding_fn=default_embedding_function,  # Replace with real embeddings in production
    )
    
    # Initialize retriever
    retriever = HybridRetriever(
        storage=storage,
        embedding_fn=default_embedding_function,
        config=retriever_config,
    )
    
    print(f"✅ Project '{project_id}' initialized successfully")
    print(f"   Database: {db_path}")
    print(f"   Audit: {config['audit']['storage_path']}")
    
    return {
        "manager": manager,
        "retriever": retriever,
        "embedder": embedder,
        "storage": storage,
        "config": config,
    }


if __name__ == "__main__":
    project = init_project()
```

### Step 4: Add Knowledge to the Graph

```python
from src.knowledge.graph import KGClaim, Entity, EntityType

# Create a claim with entities
claim = KGClaim(
    claim_id="claim-001",
    text="Transformer models have revolutionized natural language processing since 2017",
    confidence=0.95,
    source_url="https://arxiv.org/abs/1706.03762",
    source_title="Attention Is All You Need",
    entities=[
        Entity(name="Transformer", entity_type=EntityType.TECHNOLOGY),
        Entity(name="NLP", entity_type=EntityType.CONCEPT),
    ],
    topics=["natural language processing", "deep learning"],
)

# Store the claim
project["manager"].add_claim(claim)

# Query the knowledge graph
results = project["retriever"].retrieve("transformer architecture", limit=5)
for r in results:
    print(f"[{r.combined_score:.2f}] {r.claim.text}")
```

---

## Multi-Project Setup

### Project Factory Pattern

Create a factory class to manage multiple projects:

```python
#!/usr/bin/env python3
"""Multi-project management for Agent Dashboard."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional
import yaml

from src.knowledge.storage import SQLiteGraphBackend, MemoryGraphBackend
from src.knowledge.manager import KnowledgeGraphManager, default_embedding_function
from src.knowledge.retriever import HybridRetriever, HybridRetrieverConfig
from src.knowledge.embeddings import DualEmbedder, DualEmbeddingConfig, EmbeddingCache
from src.knowledge.bm25 import BM25Index, HybridRetrieverV2, ThreeWayHybridConfig
from src.knowledge.hnsw_index import HNSWIndex, HNSWConfig
from src.audit.manager import AuditManager


@dataclass
class ProjectConfig:
    """Configuration for a single project."""
    project_id: str
    name: str
    description: str
    data_dir: Path
    
    # Optional overrides
    embedding_config: Optional[DualEmbeddingConfig] = None
    retrieval_config: Optional[HybridRetrieverConfig] = None
    
    @classmethod
    def from_yaml(cls, path: str) -> "ProjectConfig":
        """Load configuration from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        
        return cls(
            project_id=data["project"]["id"],
            name=data["project"]["name"],
            description=data["project"].get("description", ""),
            data_dir=Path(data.get("data_dir", ".")).expanduser(),
        )


class Project:
    """A single project instance with isolated knowledge graph."""
    
    def __init__(self, config: ProjectConfig):
        self.config = config
        self.data_dir = config.data_dir
        self._initialized = False
        
        # Components (lazy initialized)
        self._storage = None
        self._manager = None
        self._retriever = None
        self._retriever_v2 = None
        self._embedder = None
        self._bm25_index = None
        self._hnsw_index = None
        self._audit_manager = None
        self._cache = None
    
    def initialize(self) -> None:
        """Initialize all project components."""
        if self._initialized:
            return
        
        # Create directory structure
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "embeddings").mkdir(exist_ok=True)
        (self.data_dir / "audit").mkdir(exist_ok=True)
        (self.data_dir / "rules").mkdir(exist_ok=True)
        
        # Initialize storage
        db_path = self.data_dir / "knowledge.db"
        self._storage = SQLiteGraphBackend(str(db_path))
        
        # Initialize cache
        self._cache = EmbeddingCache(default_ttl=3600.0)
        
        # Initialize embedding config
        embed_config = self.config.embedding_config or DualEmbeddingConfig()
        self._embedder = DualEmbedder(config=embed_config, cache=self._cache)
        
        # Initialize HNSW index
        hnsw_path = self.data_dir / "embeddings" / "hnsw_index.bin"
        hnsw_config = HNSWConfig(dim=384, max_elements=100000)
        self._hnsw_index = HNSWIndex(hnsw_config)
        if hnsw_path.exists():
            self._hnsw_index.load(str(hnsw_path))
        
        # Initialize BM25 index
        self._bm25_index = BM25Index()
        
        # Initialize manager
        self._manager = KnowledgeGraphManager(
            storage=self._storage,
            embedding_fn=default_embedding_function,
        )
        
        # Initialize retriever
        retrieval_config = self.config.retrieval_config or HybridRetrieverConfig()
        self._retriever = HybridRetriever(
            storage=self._storage,
            embedding_fn=default_embedding_function,
            config=retrieval_config,
        )
        
        # Initialize three-way hybrid retriever
        three_way_config = ThreeWayHybridConfig()
        self._retriever_v2 = HybridRetrieverV2(
            storage=self._storage,
            embedding_fn=default_embedding_function,
            bm25_index=self._bm25_index,
            config=three_way_config,
        )
        
        # Initialize audit manager
        audit_path = self.data_dir / "audit"
        self._audit_manager = AuditManager(storage_path=str(audit_path))
        
        self._initialized = True
        print(f"✅ Project '{self.config.project_id}' initialized at {self.data_dir}")
    
    @property
    def storage(self) -> SQLiteGraphBackend:
        """Get storage backend."""
        self.initialize()
        return self._storage
    
    @property
    def manager(self) -> KnowledgeGraphManager:
        """Get knowledge graph manager."""
        self.initialize()
        return self._manager
    
    @property
    def retriever(self) -> HybridRetriever:
        """Get hybrid retriever."""
        self.initialize()
        return self._retriever
    
    @property
    def retriever_v2(self) -> HybridRetrieverV2:
        """Get three-way hybrid retriever."""
        self.initialize()
        return self._retriever_v2
    
    def add_claim(self, claim) -> str:
        """Add a claim to this project's knowledge graph."""
        self.initialize()
        
        # Store in knowledge graph
        claim_id = self._manager.add_claim(claim)
        
        # Index in BM25
        self._bm25_index.add_document(claim.claim_id, claim.text)
        
        # Index in HNSW if embedding available
        if claim.embedding:
            self._hnsw_index.add(claim.claim_id, claim.embedding)
        
        return claim_id
    
    def search(self, query: str, limit: int = 10, use_bm25: bool = True):
        """Search the project's knowledge graph."""
        self.initialize()
        
        if use_bm25 and self._bm25_index.document_count > 0:
            return self._retriever_v2.retrieve(query, limit=limit)
        else:
            return self._retriever.retrieve(query, limit=limit)
    
    def save_indexes(self) -> None:
        """Persist indexes to disk."""
        hnsw_path = self.data_dir / "embeddings" / "hnsw_index.bin"
        self._hnsw_index.save(str(hnsw_path))
        
        structural_path = self.data_dir / "embeddings" / "structural_embeddings.pkl"
        self._embedder.structural_embedder.save(str(structural_path))
    
    def get_stats(self) -> Dict:
        """Get project statistics."""
        self.initialize()
        return {
            "project_id": self.config.project_id,
            "claims": self._storage.get_claim_count() if hasattr(self._storage, 'get_claim_count') else "N/A",
            "bm25_documents": self._bm25_index.document_count,
            "hnsw_vectors": self._hnsw_index.count,
            "cache_size": self._cache.size(),
        }
    
    def close(self) -> None:
        """Close all connections and save state."""
        if self._initialized:
            self.save_indexes()
            self._storage.close()


class ProjectManager:
    """Manages multiple project instances."""
    
    def __init__(self, base_dir: str = "~/agent-dashboard-projects"):
        self.base_dir = Path(base_dir).expanduser()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._projects: Dict[str, Project] = {}
    
    def create_project(
        self,
        project_id: str,
        name: str,
        description: str = "",
        embedding_config: Optional[DualEmbeddingConfig] = None,
        retrieval_config: Optional[HybridRetrieverConfig] = None,
    ) -> Project:
        """Create a new project."""
        
        if project_id in self._projects:
            raise ValueError(f"Project '{project_id}' already exists")
        
        config = ProjectConfig(
            project_id=project_id,
            name=name,
            description=description,
            data_dir=self.base_dir / project_id,
            embedding_config=embedding_config,
            retrieval_config=retrieval_config,
        )
        
        # Save config
        config_path = config.data_dir / "config.yaml"
        config.data_dir.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            yaml.dump({
                "project": {
                    "id": project_id,
                    "name": name,
                    "description": description,
                },
                "data_dir": str(config.data_dir),
            }, f)
        
        project = Project(config)
        project.initialize()
        self._projects[project_id] = project
        
        return project
    
    def load_project(self, project_id: str) -> Project:
        """Load an existing project."""
        
        if project_id in self._projects:
            return self._projects[project_id]
        
        config_path = self.base_dir / project_id / "config.yaml"
        if not config_path.exists():
            raise ValueError(f"Project '{project_id}' not found at {config_path}")
        
        config = ProjectConfig.from_yaml(str(config_path))
        project = Project(config)
        project.initialize()
        self._projects[project_id] = project
        
        return project
    
    def get_project(self, project_id: str) -> Optional[Project]:
        """Get a loaded project."""
        return self._projects.get(project_id)
    
    def list_projects(self) -> list:
        """List all available projects."""
        projects = []
        for item in self.base_dir.iterdir():
            if item.is_dir() and (item / "config.yaml").exists():
                projects.append(item.name)
        return projects
    
    def close_all(self) -> None:
        """Close all loaded projects."""
        for project in self._projects.values():
            project.close()
        self._projects.clear()


# Convenience function for single project use
def load_or_create_project(
    project_id: str,
    base_dir: str = "~/agent-dashboard-projects",
    **kwargs
) -> Project:
    """Load existing project or create new one."""
    manager = ProjectManager(base_dir)
    
    if project_id in manager.list_projects():
        return manager.load_project(project_id)
    else:
        return manager.create_project(project_id, **kwargs)
```

---

## Configuration Management

### Environment-Based Configuration

```python
# config/environments.py
import os
from pathlib import Path

class EnvironmentConfig:
    """Environment-specific configuration."""
    
    @staticmethod
    def get_config(env: str = None):
        env = env or os.getenv("AGENT_DASHBOARD_ENV", "development")
        
        configs = {
            "development": {
                "base_dir": "~/agent-dashboard-dev",
                "log_level": "DEBUG",
                "cache_ttl": 300,  # 5 minutes
                "use_gpu": False,
            },
            "staging": {
                "base_dir": "~/agent-dashboard-staging",
                "log_level": "INFO",
                "cache_ttl": 1800,  # 30 minutes
                "use_gpu": False,
            },
            "production": {
                "base_dir": "/var/lib/agent-dashboard",
                "log_level": "WARNING",
                "cache_ttl": 3600,  # 1 hour
                "use_gpu": True,
            },
        }
        
        return configs.get(env, configs["development"])
```

### Project-Specific Embedding Configurations

```python
# Different embedding strategies for different project types
EMBEDDING_PRESETS = {
    "research": DualEmbeddingConfig(
        semantic_weight=0.8,
        structural_weight=0.2,
        semantic_model="all-mpnet-base-v2",  # Higher quality
        embedding_dim=768,
    ),
    "code": DualEmbeddingConfig(
        semantic_weight=0.6,
        structural_weight=0.4,
        semantic_model="all-MiniLM-L6-v2",
        embedding_dim=384,
    ),
    "documentation": DualEmbeddingConfig(
        semantic_weight=0.7,
        structural_weight=0.3,
        semantic_model="all-MiniLM-L6-v2",
        embedding_dim=384,
        node2vec_walk_length=100,  # Longer walks for doc structure
    ),
}

# Usage
from project_manager import ProjectManager

pm = ProjectManager()
research_project = pm.create_project(
    project_id="ml-papers",
    name="ML Research Papers",
    embedding_config=EMBEDDING_PRESETS["research"],
)
```

---

## Knowledge Graph Isolation

### Database Isolation Verification

```python
def verify_isolation(project_a: Project, project_b: Project) -> bool:
    """Verify two projects are completely isolated."""
    
    # Verify different database paths
    assert project_a.data_dir != project_b.data_dir
    
    # Add test claim to project A
    from src.knowledge.graph import KGClaim, Entity, EntityType
    
    test_claim = KGClaim(
        claim_id="isolation-test-001",
        text="This claim only exists in Project A",
        confidence=1.0,
        source_url="https://test.example.com",
    )
    project_a.add_claim(test_claim)
    
    # Verify claim exists in A
    results_a = project_a.search("isolation test", limit=5)
    found_in_a = any(r.claim.claim_id == "isolation-test-001" for r in results_a)
    
    # Verify claim does NOT exist in B
    results_b = project_b.search("isolation test", limit=5)
    found_in_b = any(r.claim.claim_id == "isolation-test-001" for r in results_b)
    
    assert found_in_a, "Claim should exist in Project A"
    assert not found_in_b, "Claim should NOT exist in Project B"
    
    print("✅ Project isolation verified")
    return True
```

### Session-Based Isolation Within Projects

For projects with multiple users or sessions:

```python
class SessionAwareProject(Project):
    """Project with session-based claim filtering."""
    
    def __init__(self, config: ProjectConfig, session_id: str):
        super().__init__(config)
        self.session_id = session_id
    
    def add_claim(self, claim) -> str:
        """Add claim with session tracking."""
        claim.session_id = self.session_id
        return super().add_claim(claim)
    
    def search(self, query: str, limit: int = 10, session_only: bool = False):
        """Search with optional session filtering."""
        results = super().search(query, limit=limit * 2)  # Get more for filtering
        
        if session_only:
            results = [r for r in results if r.claim.session_id == self.session_id]
        
        return results[:limit]
```

---

## Embedding Strategy per Project

### Domain-Specific Embedding Models

```python
# embedding_strategies.py

from typing import Callable, List
from src.knowledge.embeddings import SemanticEmbedder, DualEmbedder

class EmbeddingStrategyFactory:
    """Factory for domain-specific embedding strategies."""
    
    MODELS = {
        "general": "all-MiniLM-L6-v2",
        "scientific": "allenai/scibert_scivocab_uncased",
        "legal": "nlpaueb/legal-bert-base-uncased",
        "code": "microsoft/codebert-base",
        "medical": "emilyalsentzer/Bio_ClinicalBERT",
    }
    
    @classmethod
    def get_embedder(cls, domain: str = "general") -> Callable[[str], List[float]]:
        """Get embedding function for domain."""
        model_name = cls.MODELS.get(domain, cls.MODELS["general"])
        
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(model_name)
            
            def embed(text: str) -> List[float]:
                return model.encode(text, normalize_embeddings=True).tolist()
            
            return embed
        except ImportError:
            # Fallback to hash-based
            from src.knowledge.manager import default_embedding_function
            return default_embedding_function


# Usage
pm = ProjectManager()

# Scientific research project
science_project = pm.create_project("science-research", name="Science Research")
science_embed = EmbeddingStrategyFactory.get_embedder("scientific")

# Legal document project  
legal_project = pm.create_project("legal-docs", name="Legal Documents")
legal_embed = EmbeddingStrategyFactory.get_embedder("legal")
```

---

## Audit Trail Separation

### Per-Project Audit Configuration

```python
# audit_config.py

from pathlib import Path
from src.audit.manager import AuditManager
from src.audit.trail import AuditTrail, AuditConfig

def setup_project_audit(project: Project) -> AuditManager:
    """Setup isolated audit trail for project."""
    
    audit_dir = project.data_dir / "audit"
    audit_dir.mkdir(exist_ok=True)
    
    config = AuditConfig(
        storage_path=str(audit_dir),
        retention_days=90,
        enable_hashing=True,  # Tamper-evident
        compress_old=True,
    )
    
    audit_manager = AuditManager(config=config)
    
    # Log project initialization
    audit_manager.log_event(
        event_type="PROJECT_INIT",
        details={
            "project_id": project.config.project_id,
            "timestamp": datetime.now().isoformat(),
        }
    )
    
    return audit_manager
```

---

## Best Practices

### 1. Project Naming Convention

```
{team}-{domain}-{environment}

Examples:
- research-nlp-dev
- legal-contracts-prod
- eng-codebase-staging
```

### 2. Regular Backups

```python
import shutil
from datetime import datetime

def backup_project(project: Project, backup_dir: str = "~/backups"):
    """Create timestamped backup of project."""
    backup_dir = Path(backup_dir).expanduser()
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{project.config.project_id}_{timestamp}"
    backup_path = backup_dir / backup_name
    
    # Save indexes before backup
    project.save_indexes()
    
    # Copy entire project directory
    shutil.copytree(project.data_dir, backup_path)
    
    print(f"✅ Backup created: {backup_path}")
    return backup_path
```

### 3. Project Health Checks

```python
def check_project_health(project: Project) -> dict:
    """Run health checks on project."""
    checks = {
        "database_accessible": False,
        "indexes_valid": False,
        "audit_writable": False,
        "claim_count": 0,
    }
    
    try:
        # Check database
        project.storage._get_connection()
        checks["database_accessible"] = True
        
        # Check claim count
        checks["claim_count"] = project._storage.get_claim_count() if hasattr(project._storage, 'get_claim_count') else -1
        
        # Check indexes
        checks["indexes_valid"] = project._hnsw_index.count >= 0
        
        # Check audit
        audit_path = project.data_dir / "audit"
        checks["audit_writable"] = audit_path.exists() and os.access(audit_path, os.W_OK)
        
    except Exception as e:
        checks["error"] = str(e)
    
    return checks
```

### 4. Resource Cleanup

```python
import atexit

# Register cleanup on exit
pm = ProjectManager()

@atexit.register
def cleanup():
    pm.close_all()
    print("All projects closed successfully")
```

---

## Example: Three-Project Setup

Complete example setting up three isolated projects:

```python
#!/usr/bin/env python3
"""Example: Three isolated projects for different domains."""

from pathlib import Path
import sys

# Add agent-dashboard to path
sys.path.insert(0, "/path/to/agent-dashboard")

from project_manager import ProjectManager, EMBEDDING_PRESETS
from src.knowledge.graph import KGClaim, Entity, EntityType
from src.knowledge.retriever import HybridRetrieverConfig


def main():
    # Initialize project manager
    pm = ProjectManager(base_dir="~/multi-project-demo")
    
    # =========================================================================
    # Project 1: AI Research Papers
    # =========================================================================
    ai_research = pm.create_project(
        project_id="ai-research",
        name="AI Research Knowledge Base",
        description="Papers and findings from AI/ML research",
        embedding_config=EMBEDDING_PRESETS["research"],
        retrieval_config=HybridRetrieverConfig(
            vector_weight=0.6,
            graph_weight=0.4,
        ),
    )
    
    # Add AI research claims
    ai_research.add_claim(KGClaim(
        claim_id="ai-001",
        text="Transformers achieve state-of-the-art performance on NLP tasks",
        confidence=0.95,
        source_url="https://arxiv.org/abs/1706.03762",
        entities=[
            Entity(name="Transformer", entity_type=EntityType.TECHNOLOGY),
            Entity(name="NLP", entity_type=EntityType.CONCEPT),
        ],
        topics=["deep learning", "natural language processing"],
    ))
    
    ai_research.add_claim(KGClaim(
        claim_id="ai-002",
        text="GPT-4 demonstrates emergent reasoning capabilities",
        confidence=0.9,
        source_url="https://openai.com/research/gpt-4",
        entities=[
            Entity(name="GPT-4", entity_type=EntityType.TECHNOLOGY),
            Entity(name="OpenAI", entity_type=EntityType.ORGANIZATION),
        ],
        topics=["large language models", "reasoning"],
    ))
    
    # =========================================================================
    # Project 2: Software Engineering Best Practices
    # =========================================================================
    software_eng = pm.create_project(
        project_id="software-eng",
        name="Software Engineering Knowledge Base",
        description="Best practices, patterns, and guidelines",
        embedding_config=EMBEDDING_PRESETS["code"],
        retrieval_config=HybridRetrieverConfig(
            vector_weight=0.5,
            graph_weight=0.5,
        ),
    )
    
    # Add software engineering claims
    software_eng.add_claim(KGClaim(
        claim_id="se-001",
        text="Test-driven development reduces bug density by 40-80%",
        confidence=0.85,
        source_url="https://example.com/tdd-study",
        entities=[
            Entity(name="TDD", entity_type=EntityType.CONCEPT),
        ],
        topics=["testing", "software quality"],
    ))
    
    software_eng.add_claim(KGClaim(
        claim_id="se-002",
        text="Microservices enable independent deployment and scaling",
        confidence=0.9,
        source_url="https://martinfowler.com/microservices",
        entities=[
            Entity(name="Microservices", entity_type=EntityType.TECHNOLOGY),
        ],
        topics=["architecture", "distributed systems"],
    ))
    
    # =========================================================================
    # Project 3: Product Documentation
    # =========================================================================
    product_docs = pm.create_project(
        project_id="product-docs",
        name="Product Documentation",
        description="Internal product knowledge and FAQs",
        embedding_config=EMBEDDING_PRESETS["documentation"],
    )
    
    # Add product documentation claims
    product_docs.add_claim(KGClaim(
        claim_id="doc-001",
        text="The API rate limit is 1000 requests per minute per API key",
        confidence=1.0,
        source_url="https://docs.example.com/api/limits",
        entities=[
            Entity(name="API", entity_type=EntityType.TECHNOLOGY),
        ],
        topics=["api", "limits"],
    ))
    
    # =========================================================================
    # Demonstrate Isolation
    # =========================================================================
    print("\n" + "=" * 60)
    print("DEMONSTRATING PROJECT ISOLATION")
    print("=" * 60)
    
    # Search for "transformer" in each project
    query = "transformer deep learning"
    
    print(f"\nSearching for: '{query}'")
    print("-" * 40)
    
    for project_id in ["ai-research", "software-eng", "product-docs"]:
        project = pm.get_project(project_id)
        results = project.search(query, limit=3)
        
        print(f"\n📁 {project.config.name}:")
        if results:
            for r in results:
                print(f"   [{r.combined_score:.2f}] {r.claim.text[:60]}...")
        else:
            print("   (no results)")
    
    # =========================================================================
    # Show Project Stats
    # =========================================================================
    print("\n" + "=" * 60)
    print("PROJECT STATISTICS")
    print("=" * 60)
    
    for project_id in pm.list_projects():
        project = pm.load_project(project_id)
        stats = project.get_stats()
        print(f"\n📊 {project_id}:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
    
    # Cleanup
    pm.close_all()
    print("\n✅ All projects closed successfully")


if __name__ == "__main__":
    main()
```

---

## Migration and Backup

### Export Project to JSON

```python
import json
from datetime import datetime

def export_project(project: Project, output_path: str) -> None:
    """Export project knowledge graph to JSON."""
    
    claims = project.storage.get_all_claims()  # Implement this method
    
    export_data = {
        "project_id": project.config.project_id,
        "exported_at": datetime.now().isoformat(),
        "claims": [claim.to_dict() for claim in claims],
    }
    
    with open(output_path, "w") as f:
        json.dump(export_data, f, indent=2)
    
    print(f"✅ Exported {len(claims)} claims to {output_path}")


def import_project(project: Project, input_path: str) -> int:
    """Import claims from JSON export."""
    
    with open(input_path) as f:
        data = json.load(f)
    
    count = 0
    for claim_data in data["claims"]:
        claim = KGClaim.from_dict(claim_data)
        project.add_claim(claim)
        count += 1
    
    print(f"✅ Imported {count} claims from {input_path}")
    return count
```

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "Database is locked" | Multiple processes accessing same DB | Use separate databases per project |
| "Embedding dimension mismatch" | Different models produce different sizes | Ensure consistent embedding_dim across project |
| "Claims appearing in wrong project" | Shared storage backend | Verify each project has unique data_dir |
| "HNSW index corrupted" | Interrupted save | Delete index file and rebuild |

### Debug Mode

```python
import logging

# Enable debug logging for a project
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("agent_dashboard")
logger.setLevel(logging.DEBUG)

# Project operations will now show detailed logs
project = pm.load_project("my-project")
results = project.search("test query")  # Will show debug info
```

---

## Summary

| Aspect | Recommendation |
|--------|----------------|
| **Storage** | Use separate SQLite databases per project |
| **Directory** | Each project in its own directory |
| **Embeddings** | Configure model based on domain |
| **Indexes** | HNSW and BM25 per project |
| **Audit** | Separate audit trails per project |
| **Backup** | Regular timestamped backups |
| **Naming** | Consistent `{team}-{domain}-{env}` pattern |

The Agent Dashboard architecture fully supports multi-project deployments with complete isolation. By following this guide, you can maintain separate, domain-specific knowledge bases that remain relevant and uncontaminated across different projects.