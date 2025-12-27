# Integration Test Guide

## Overview

Integration tests (IT-001 through IT-005) verify cross-module interactions in Agent Dashboard. These tests take 2-4 hours and should be run before each release.

## Objectives

- Verify knowledge graph to retriever pipeline
- Validate summarizer to dashboard display
- Test BM25 + Vector hybrid search
- Confirm community detection visualization
- Check provenance tracking

## Prerequisites

- All smoke tests pass
- Standard test dataset loaded (1,000 claims)
- Optional dependencies installed (networkx, sentence-transformers)

## Setup

1. Generate test data:
   ```bash
   python scripts/generate_test_data.py --claims 1000 --output tests/fixtures/standard_kg.json
   ```

2. Verify fixtures:
   ```bash
   python scripts/manual_tests/check_test_environment.py
   ```

3. Start dashboard with verbose logging:
   ```bash
   python src/web_server.py --verbose
   ```

## Test Procedures

### IT-001: Knowledge Graph to Retriever Pipeline

**Objective:** Verify claims flow from KG through hybrid retriever

**Steps:**
1. Load standard_kg.json via KnowledgeGraphManager
2. Execute query "Python machine learning"
3. Verify results include relevant claims

**Expected Results:**
- Top 10 results contain relevant claims
- Results have vector_score, graph_score, bm25_score
- Query completes in <5 seconds

**Pass Criteria:** At least 3 relevant claims in top 10

---

### IT-002: Summarizer to Dashboard Display

**Objective:** Session summaries display correctly

**Steps:**
1. Create session with 10+ tasks
2. Generate hierarchical summary
3. Verify display in dashboard

**Expected Results:**
- Summary shows phases, accomplishments, blockers
- All summary levels are expandable
- Formatting is correct

**Pass Criteria:** Summary displays correctly

---

### IT-003: BM25 + Vector Hybrid Search

**Objective:** Three-way hybrid search returns fused results

**Steps:**
1. Query "Python machine learning frameworks"
2. Inspect result scores in response

**Expected Results:**
- Results have vector_score, graph_score, bm25_score
- RRF fusion produces reasonable ranking
- Mixed results from different sources

**Pass Criteria:** All three scores present

---

### IT-004: Community Detection with Visualization

**Objective:** Communities detected and visualized

**Steps:**
1. Run Leiden community detection on knowledge graph
2. Generate visualization HTML
3. Open and verify interactive chart

**Expected Results:**
- Interactive Plotly chart with colored communities
- At least 3 distinct communities visible
- Nodes are clickable

**Pass Criteria:** Visualization loads, communities visible

---

### IT-005: Provenance Tracking Through Audit Trail

**Objective:** Entity provenance traces back to sources

**Steps:**
1. Store claim with source attribution
2. Query provenance for an entity
3. Verify complete chain

**Expected Results:**
- Provenance shows claim -> source -> agent
- Full chain is reconstructable
- Timestamps are accurate

**Pass Criteria:** Complete provenance chain

---

## Metrics to Collect

| Metric | Target | Actual |
|--------|--------|--------|
| KG load time | <10s | _____ |
| Query latency | <5s | _____ |
| Visualization render | <3s | _____ |
| Memory usage | <2GB | _____ |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Import errors | Install optional dependencies |
| Slow queries | Check index status |
| Visualization blank | Update Plotly version |
| Memory issues | Reduce dataset size |

## Sign-Off

- [ ] All 5 integration tests pass
- [ ] Performance within targets
- [ ] No errors in logs

---

*Document Version: 1.0.0*
*Last Updated: 2025-12-26*
