# Agent Dashboard Memory Architecture

> **Version:** 2.7.0
> **Last Updated:** 2025-01-01
> **Purpose:** Technical reference for database architecture, verification, and project isolation

This document provides a comprehensive overview of the Agent Dashboard persistence layer, including all database locations, schemas, and methods for project isolation.

---

## Table of Contents

- [Database Overview](#database-overview)
- [Database Locations and Purposes](#database-locations-and-purposes)
- [Schema Reference](#schema-reference)
- [Verification Commands](#verification-commands)
- [Project Isolation](#project-isolation)
- [Context Switching](#context-switching)
- [Best Practices](#best-practices)

---

## Database Overview

Agent Dashboard uses SQLite for all persistent storage, with separate databases for different concerns:

```
~/.claude/
  agent_dashboard.db    # Events, sessions, real-time monitoring
  knowledge.db          # Knowledge graph: claims, entities, embeddings
  audit.db              # Audit trail: decisions, verification
  workflow_engine.db    # Workflow state: tasks, phases, checkpoints
  {project_dir}/
    rules.db            # Learned rules (per-project)
```

### Why SQLite?

| Benefit | Description |
|---------|-------------|
| **Zero Configuration** | No server setup, works out of the box |
| **Single-File** | Easy backup, migration, and inspection |
| **Concurrent Reads** | WAL mode enables multiple readers |
| **Portable** | Same file format across platforms |

---

## Database Locations and Purposes

### 1. Agent Dashboard Database

**Location:** `~/.claude/agent_dashboard.db`

**Purpose:** Central event store for real-time monitoring and session tracking.

**Created by:** `src/web_server.py`

**Contains:**
- Real-time events from Claude Code hooks
- Session metadata and state
- Token usage and cost tracking
- Project grouping information

**Example queries:**
```bash
# List all tracked projects
sqlite3 ~/.claude/agent_dashboard.db "SELECT DISTINCT project FROM events ORDER BY project;"

# Count events per project
sqlite3 ~/.claude/agent_dashboard.db "SELECT project, COUNT(*) as events FROM events GROUP BY project;"

# Recent events (last 10)
sqlite3 ~/.claude/agent_dashboard.db "SELECT timestamp, agent_name, event_type, project FROM events ORDER BY timestamp DESC LIMIT 10;"

# Sessions per project with token totals
sqlite3 ~/.claude/agent_dashboard.db "SELECT project, COUNT(DISTINCT session_id) as sessions, SUM(tokens_in + tokens_out) as total_tokens FROM events GROUP BY project;"
```

### 2. Knowledge Graph Database

**Location:** `~/.claude/knowledge.db`

**Purpose:** Stores claims, entities, relationships, and embeddings for RAG retrieval.

**Created by:** `src/knowledge/storage.py` (SQLiteGraphBackend)

**Contains:**
- Claims with confidence scores and provenance
- Entities with temporal validity
- Source documents and citations
- Claim-entity-topic relationships
- Embeddings for vector search

**Example queries:**
```bash
# Count claims by session
sqlite3 ~/.claude/knowledge.db "SELECT session_id, COUNT(*) as claims FROM claims GROUP BY session_id;"

# List all tracked entities
sqlite3 ~/.claude/knowledge.db "SELECT name, entity_type, COUNT(*) as mentions FROM entities GROUP BY name, entity_type ORDER BY mentions DESC LIMIT 20;"

# View recent claims with sources
sqlite3 ~/.claude/knowledge.db "SELECT claim_id, substr(text, 1, 80) as claim_text, source_title FROM claims ORDER BY created_at DESC LIMIT 10;"
```

### 3. Audit Trail Database

**Location:** `~/.claude/audit.db`

**Purpose:** Immutable audit trail for decisions, verifications, and compliance.

**Created by:** `src/audit/storage.py` (SQLiteStorageBackend)

**Contains:**
- Decision records with reasoning
- Verification status and scores
- Hash chains for tamper evidence
- Agent and model attribution

**Example queries:**
```bash
# Count audit entries by decision type
sqlite3 ~/.claude/audit.db "SELECT decision_type, COUNT(*) FROM audit_entries GROUP BY decision_type;"

# View recent decisions
sqlite3 ~/.claude/audit.db "SELECT entry_id, decision_type, agent_id, confidence_score FROM audit_entries ORDER BY timestamp DESC LIMIT 10;"

# Check entries by session
sqlite3 ~/.claude/audit.db "SELECT session_id, COUNT(*) as entries FROM audit_entries GROUP BY session_id;"
```

### 4. Workflow Engine Database

**Location:** `~/.claude/workflow_engine.db`

**Purpose:** TDD workflow state, task tracking, and phase management.

**Created by:** `src/workflow_engine.py`

**Contains:**
- Workflow definitions and status
- Task assignments and progress
- Phase checkpoints
- Budget tracking events

**Example queries:**
```bash
# List all workflows
sqlite3 ~/.claude/workflow_engine.db "SELECT id, name, status, created_at, total_cost FROM workflows ORDER BY created_at DESC;"

# View workflow events
sqlite3 ~/.claude/workflow_engine.db "SELECT workflow_id, event_type, phase, agent, tokens_in, tokens_out, cost FROM workflow_events ORDER BY timestamp DESC LIMIT 20;"
```

### 5. Rules Database

**Location:** `{project_dir}/rules.db` or `./rules.db`

**Purpose:** Learned rules extracted from successful interactions.

**Created by:** `src/learning/store.py` (SQLiteRuleStore)

**Contains:**
- Extracted rules with conditions and recommendations
- Success/failure counts for effectiveness tracking
- Category and tag classifications
- Full-text search index

**Example queries:**
```bash
# List active rules by effectiveness
sqlite3 ./rules.db "SELECT id, condition, CAST(success_count AS REAL) / (success_count + failure_count) as effectiveness FROM rules WHERE status = 'active' ORDER BY effectiveness DESC LIMIT 10;"

# Rules by category
sqlite3 ./rules.db "SELECT category, COUNT(*) FROM rules WHERE status = 'active' GROUP BY category;"
```

---

## Schema Reference

### events (agent_dashboard.db)

```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    event_type TEXT NOT NULL,
    session_id TEXT NOT NULL,
    project TEXT NOT NULL,
    model TEXT,
    tokens_in INTEGER DEFAULT 0,
    tokens_out INTEGER DEFAULT 0,
    cost REAL DEFAULT 0.0,
    payload TEXT
);

CREATE INDEX idx_events_session ON events(session_id);
CREATE INDEX idx_events_timestamp ON events(timestamp DESC);
CREATE INDEX idx_events_project ON events(project);
```

### claims (knowledge.db)

```sql
CREATE TABLE claims (
    claim_id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    confidence REAL DEFAULT 0.0,
    source_url TEXT NOT NULL,
    source_title TEXT,
    publication_date TEXT,
    agent_id TEXT,
    session_id TEXT,
    embedding TEXT,
    created_at TEXT NOT NULL,
    metadata TEXT
);

CREATE INDEX idx_claims_source ON claims(source_url);
CREATE INDEX idx_claims_session ON claims(session_id);
```

### entities (knowledge.db)

```sql
CREATE TABLE entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    metadata TEXT,
    valid_from TEXT,
    valid_to TEXT,
    source_location TEXT,
    UNIQUE(name, entity_type)
);

CREATE INDEX idx_entities_name ON entities(name);
CREATE INDEX idx_entities_type ON entities(entity_type);
```

### audit_entries (audit.db)

```sql
CREATE TABLE audit_entries (
    entry_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    session_id TEXT,
    conversation_id TEXT,
    decision_type TEXT NOT NULL,
    agent_id TEXT,
    model_name TEXT,
    input_hash TEXT,
    reasoning_summary TEXT,
    selected_action TEXT,
    confidence_score REAL DEFAULT 0.0,
    verification_status TEXT DEFAULT 'pending',
    previous_entry_hash TEXT,
    entry_hash TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```


---

## Verification Commands

### Quick Health Check

```bash
# Check each database exists and has tables
for db in ~/.claude/agent_dashboard.db ~/.claude/knowledge.db ~/.claude/audit.db ~/.claude/workflow_engine.db; do
    if [ -f "$db" ]; then
        size=$(du -h "$db" | cut -f1)
        tables=$(sqlite3 "$db" ".tables" 2>/dev/null | wc -w)
        echo "[OK] $db ($size, $tables tables)"
    else
        echo "[--] $db (not created yet)"
    fi
done
```

### Windows PowerShell

```powershell
$databases = @(
    "$env:USERPROFILE\.claudegent_dashboard.db",
    "$env:USERPROFILE\.claude\knowledge.db",
    "$env:USERPROFILE\.claudeudit.db",
    "$env:USERPROFILE\.claude\workflow_engine.db"
)

foreach ($db in $databases) {
    if (Test-Path $db) {
        $size = (Get-Item $db).Length / 1KB
        Write-Host "[OK] $db ($([math]::Round($size, 1))KB)"
    } else {
        Write-Host "[--] $db (not created)"
    }
}
```

### Integrity Check

```bash
sqlite3 ~/.claude/agent_dashboard.db "PRAGMA integrity_check;"
sqlite3 ~/.claude/knowledge.db "PRAGMA integrity_check;"
sqlite3 ~/.claude/audit.db "PRAGMA integrity_check;"
```

---

## Project Isolation

### Method 1: Environment Variable (Recommended)

Set `AGENT_PROJECT` to tag all events with a project name:

```bash
# Set project before starting Claude Code
export AGENT_PROJECT="my-project-name"
claude

# Or inline
AGENT_PROJECT=my-project claude "start working on feature X"
```

**How it works:**
- Hook scripts read `AGENT_PROJECT` and include it in event payloads
- Events are stored with the project field in agent_dashboard.db
- Web dashboard groups sessions by project automatically

### Method 2: Session-Based Isolation

Each Claude Code session gets a unique `session_id`. Use session filtering:

```bash
# Find sessions for a specific project
sqlite3 ~/.claude/agent_dashboard.db "SELECT DISTINCT session_id, agent_name, model FROM events WHERE project = 'my-project' ORDER BY timestamp DESC;"

# Query claims by session
sqlite3 ~/.claude/knowledge.db "SELECT claim_id, substr(text, 1, 60) as claim FROM claims WHERE session_id = 'YOUR_SESSION_ID';"
```

### Method 3: Directory-Based Isolation (Complete Separation)

For projects needing completely separate knowledge bases:

```bash
# Create project-specific directory
mkdir -p ~/projects/project-alpha/.claude

# Set custom database paths
export AGENT_DASHBOARD_DB=~/projects/project-alpha/.claude/dashboard.db
export KNOWLEDGE_DB=~/projects/project-alpha/.claude/knowledge.db
```

See [Multi-Project Guide](Agent%20dashboard%20multi%20project%20guide.md) for complete details.

---

## Context Switching

### Quick Switch (Same Databases, Different Project Tag)

```bash
# Project A
export AGENT_PROJECT="project-alpha"
AGENT_NAME=researcher claude "analyze the codebase"

# Project B (new terminal or after completion)
export AGENT_PROJECT="project-beta"
AGENT_NAME=implementer claude "implement feature X"
```

### Complete Switch Script

```bash
#!/bin/bash
# save as: switch-project.sh
PROJECT=$1
if [ -z "$PROJECT" ]; then
    echo "Usage: source switch-project.sh <project-name>"
    return 1
fi

export AGENT_PROJECT="$PROJECT"
mkdir -p ~/.claude/projects/$PROJECT
echo "Switched to project: $PROJECT"
```

### Listing All Projects

```bash
sqlite3 ~/.claude/agent_dashboard.db "SELECT project, COUNT(DISTINCT session_id) as sessions, COUNT(*) as events, MAX(timestamp) as last_activity FROM events GROUP BY project ORDER BY last_activity DESC;"
```

---

## Best Practices

### 1. Regular Backups

```bash
BACKUP_DIR=~/.claude/backups/$(date +%Y%m%d)
mkdir -p "$BACKUP_DIR"
cp ~/.claude/*.db "$BACKUP_DIR/"
echo "Backed up to $BACKUP_DIR"
```

### 2. Periodic Cleanup

```bash
# Remove events older than 90 days
sqlite3 ~/.claude/agent_dashboard.db "DELETE FROM events WHERE timestamp < datetime('now', '-90 days');"
sqlite3 ~/.claude/agent_dashboard.db "VACUUM;"
```

### 3. Project Naming Convention

```
{team}-{domain}-{environment}

Examples:
- research-nlp-dev
- frontend-dashboard-prod
- backend-api-staging
```

### 4. Monitor Database Size

```bash
du -sh ~/.claude/*.db | sort -h
```

---

## Troubleshooting

### Database Locked Error

**Solution:** Enable WAL mode for better concurrency:
```bash
sqlite3 ~/.claude/agent_dashboard.db "PRAGMA journal_mode=WAL;"
```

### Corrupted Database

**Solution:** Attempt recovery:
```bash
sqlite3 ~/.claude/agent_dashboard.db ".recover" | sqlite3 ~/.claude/agent_dashboard_recovered.db
mv ~/.claude/agent_dashboard.db ~/.claude/agent_dashboard_corrupt.db
mv ~/.claude/agent_dashboard_recovered.db ~/.claude/agent_dashboard.db
```

### Missing Tables

**Solution:** Tables are created on first use. Run the dashboard once:
```bash
agent-dashboard --web
# Stop with Ctrl+C after it starts
```

---

## Related Documentation

- [Example Usage Guide](EXAMPLE_USAGE.md) - Step-by-step usage walkthrough
- [Multi-Project Guide](Agent%20dashboard%20multi%20project%20guide.md) - Complete project isolation
- [Configuration Reference](CONFIG_REFERENCE.md) - All configuration options

---

*Built for quality-focused AI workflows with comprehensive memory management.*
