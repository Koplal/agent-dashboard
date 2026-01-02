# Manual Testing Strategy - Agent Dashboard v2.7.0

## Overview

This document defines the manual testing strategy for Agent Dashboard v2.7.0, addressing testing gaps that cannot be covered by automated tests:
- Cross-module integration with live LLM
- Dashboard UI/UX verification
- Performance at scale (>100K claims)
- Cross-platform installation validation

**Automated Test Coverage:** 1,240 tests (1,226 passed, 14 skipped)
**Manual Test Coverage:** 25 test cases across 6 categories

---

## Table of Contents

1. [Test Categories](#1-test-categories)
2. [Test Environments](#2-test-environments)
3. [Test Data Requirements](#3-test-data-requirements)
4. [Detailed Test Cases](#4-detailed-test-cases)
5. [Execution Checklists](#5-execution-checklists)
6. [Bug Reporting Template](#6-bug-reporting-template)
7. [Sign-Off Criteria](#7-sign-off-criteria)

---

## 1. Test Categories

| Category | Purpose | Duration | When Executed |
|----------|---------|----------|---------------|
| **Smoke Tests** | Quick validation of core functionality | 15 min | Every build |
| **Integration Tests** | Cross-module interaction verification | 2-4 hours | Before release |
| **End-to-End Tests** | Full workflow validation | 4-8 hours | Before release |
| **Performance Tests** | Scale and load testing | 2-8 hours | Major releases |
| **UI/UX Tests** | Dashboard visual verification | 1-2 hours | Before release |
| **Installation Tests** | Cross-platform validation | 2-4 hours | Major releases |

---

## 2. Test Environments

### 2.1 Local Development
```
OS: Windows 10/11, macOS 12+, Ubuntu 22.04+
Python: 3.10+
Node.js: 18+ (optional, for xenova tokenizer)
Browser: Chrome 120+
Database: SQLite (default)
```

### 2.2 CI/CD Environment
```
Platform: GitHub Actions / GitLab CI
Runners: ubuntu-latest, windows-latest, macos-latest
Parallel: Up to 3 concurrent jobs
```

### 2.3 Staging Environment
```
Server: Linux VM (4 CPU, 8GB RAM)
Database: SQLite with 10K sample claims
LLM: Claude API (test key with rate limits)
Monitoring: Basic logging enabled
```

### 2.4 Production-Like Environment
```
Server: Linux VM (8 CPU, 16GB RAM)
Database: SQLite with 100K+ claims
LLM: Claude API (production key)
Monitoring: Full observability stack
Load: Simulated 10+ concurrent users
```

---

## 3. Test Data Requirements

### 3.1 Sample Knowledge Graphs

| Dataset | Size | Purpose | Location |
|---------|------|---------|----------|
| `minimal.json` | 10 claims | Smoke tests | `tests/fixtures/` |
| `standard.json` | 1,000 claims | Integration tests | `tests/fixtures/` |
| `large.json` | 10,000 claims | Performance baseline | `tests/fixtures/` |
| `scale.json` | 100,000+ claims | Scale testing | Generated on-demand |

### 3.2 Test Queries

```python
SMOKE_QUERIES = [
    "What is Python?",
    "machine learning frameworks",
    "error handling best practices",
]

INTEGRATION_QUERIES = [
    "Find all claims related to Python and machine learning",
    "What changed in the last session?",
    "Summarize the authentication module",
]

STRESS_QUERIES = [
    # 100 random queries from diverse topics
    # Generated using: python scripts/generate_test_queries.py
]
```

### 3.3 Expected Results

Test queries should return results matching these criteria:
- Smoke queries: >0 results within 2 seconds
- Integration queries: Semantically relevant results
- Stress queries: No timeouts, no crashes

---

## 4. Detailed Test Cases

### 4.1 Smoke Tests (ST)

#### ST-001: Dashboard Startup
| Field | Value |
|-------|-------|
| **ID** | ST-001 |
| **Name** | Dashboard starts and serves homepage |
| **Priority** | Critical |
| **Prerequisites** | Python 3.10+ installed, dependencies installed |
| **Steps** | 1. Run `python src/web_server.py`<br>2. Open browser to `http://localhost:4200`<br>3. Verify homepage loads |
| **Expected** | Dashboard loads within 5 seconds, no console errors |
| **Pass Criteria** | Homepage displays session list and event panels |

#### ST-002: WebSocket Connection
| Field | Value |
|-------|-------|
| **ID** | ST-002 |
| **Name** | WebSocket connection established |
| **Priority** | Critical |
| **Prerequisites** | Dashboard running |
| **Steps** | 1. Open browser DevTools (Network tab)<br>2. Navigate to dashboard<br>3. Filter by "WS" |
| **Expected** | WebSocket connection shows "101 Switching Protocols" |
| **Pass Criteria** | Connection status shows "Connected" in UI |

#### ST-003: Event Ingestion
| Field | Value |
|-------|-------|
| **ID** | ST-003 |
| **Name** | Events are ingested and displayed |
| **Priority** | Critical |
| **Prerequisites** | Dashboard running |
| **Steps** | 1. Run `python hooks/send_event.py --type tool_start --tool Read`<br>2. Observe dashboard |
| **Expected** | Event appears in timeline within 1 second |
| **Pass Criteria** | Event shows correct type, timestamp, and details |

#### ST-004: API Health Check
| Field | Value |
|-------|-------|
| **ID** | ST-004 |
| **Name** | API endpoints respond correctly |
| **Priority** | High |
| **Prerequisites** | Dashboard running |
| **Steps** | 1. `curl http://localhost:4200/api/sessions`<br>2. `curl http://localhost:4200/api/events` |
| **Expected** | HTTP 200 with JSON response |
| **Pass Criteria** | Valid JSON returned, no 500 errors |

#### ST-005: Database Access
| Field | Value |
|-------|-------|
| **ID** | ST-005 |
| **Name** | Database is accessible and functional |
| **Priority** | High |
| **Prerequisites** | Dashboard running |
| **Steps** | 1. Send test event<br>2. Restart dashboard<br>3. Verify event persisted |
| **Expected** | Events persist across restarts |
| **Pass Criteria** | Previously sent events visible after restart |

---

### 4.2 Integration Tests (IT)

#### IT-001: Knowledge Graph to Retriever Pipeline
| Field | Value |
|-------|-------|
| **ID** | IT-001 |
| **Name** | Claims flow from KG through hybrid retriever |
| **Priority** | High |
| **Prerequisites** | Standard test dataset loaded |
| **Steps** | 1. Store 100 claims via `KnowledgeGraphManager`<br>2. Query via `HybridRetriever`<br>3. Verify results include stored claims |
| **Expected** | Relevant claims returned with scores |
| **Pass Criteria** | Top 10 results contain at least 3 relevant claims |

#### IT-002: Summarizer to Dashboard Display
| Field | Value |
|-------|-------|
| **ID** | IT-002 |
| **Name** | Session summaries display correctly |
| **Priority** | High |
| **Prerequisites** | Session with 10+ tasks |
| **Steps** | 1. Generate hierarchical summary<br>2. Send summary to dashboard<br>3. Verify display |
| **Expected** | Summary shows phases, accomplishments, blockers |
| **Pass Criteria** | All summary levels expandable in UI |

#### IT-003: BM25 + Vector Hybrid Search
| Field | Value |
|-------|-------|
| **ID** | IT-003 |
| **Name** | Three-way hybrid search returns fused results |
| **Priority** | High |
| **Prerequisites** | BM25 index built, embeddings generated |
| **Steps** | 1. Query "Python machine learning"<br>2. Inspect result scores |
| **Expected** | Results have vector_score, graph_score, bm25_score |
| **Pass Criteria** | RRF fusion produces reasonable ranking |

#### IT-004: Community Detection with Visualization
| Field | Value |
|-------|-------|
| **ID** | IT-004 |
| **Name** | Communities detected and visualized |
| **Priority** | Medium |
| **Prerequisites** | Large knowledge graph (1000+ nodes) |
| **Steps** | 1. Run Leiden community detection<br>2. Generate visualization<br>3. Open HTML output |
| **Expected** | Interactive Plotly chart with colored communities |
| **Pass Criteria** | At least 3 distinct communities visible |

#### IT-005: Provenance Tracking Through Audit Trail
| Field | Value |
|-------|-------|
| **ID** | IT-005 |
| **Name** | Entity provenance traces back to sources |
| **Priority** | High |
| **Prerequisites** | Claims with audit entries |
| **Steps** | 1. Store claim with source<br>2. Query provenance for entity<br>3. Verify chain |
| **Expected** | Provenance shows claim → source → agent |
| **Pass Criteria** | Full provenance chain reconstructable |

---

### 4.3 End-to-End Tests (E2E)

#### E2E-001: Complete Agent Session Workflow
| Field | Value |
|-------|-------|
| **ID** | E2E-001 |
| **Name** | Full agent session from start to summary |
| **Priority** | Critical |
| **Prerequisites** | Clean environment, LLM API access |
| **Steps** | 1. Start new session via Claude Code<br>2. Perform 5+ tool operations<br>3. End session<br>4. Generate summary<br>5. View in dashboard |
| **Expected** | Complete session visible with all events |
| **Pass Criteria** | Session timeline accurate, summary correct |

#### E2E-002: Knowledge Acquisition and Retrieval
| Field | Value |
|-------|-------|
| **ID** | E2E-002 |
| **Name** | Learn fact, retrieve later |
| **Priority** | High |
| **Prerequisites** | Empty knowledge graph |
| **Steps** | 1. Store claim "Python 3.12 released in Oct 2023"<br>2. Wait 5 seconds<br>3. Query "When was Python 3.12 released?" |
| **Expected** | Query returns the stored claim |
| **Pass Criteria** | Exact claim in top 3 results |

#### E2E-003: Multi-User Dashboard Access
| Field | Value |
|-------|-------|
| **ID** | E2E-003 |
| **Name** | Multiple users view dashboard simultaneously |
| **Priority** | Medium |
| **Prerequisites** | Dashboard running |
| **Steps** | 1. Open dashboard in 3 different browsers<br>2. Send event from one source<br>3. Verify all browsers update |
| **Expected** | All browsers show event within 2 seconds |
| **Pass Criteria** | WebSocket broadcast works to all clients |

---

### 4.4 Performance Tests (PT)

#### PT-001: 100K Claim Ingestion
| Field | Value |
|-------|-------|
| **ID** | PT-001 |
| **Name** | Ingest 100,000 claims |
| **Priority** | High |
| **Prerequisites** | Scale test dataset |
| **Steps** | 1. Time ingestion of 100K claims<br>2. Measure memory usage<br>3. Verify all claims stored |
| **Expected** | Complete in <10 minutes, <4GB RAM |
| **Pass Criteria** | All claims retrievable after ingestion |

#### PT-002: Search Latency at Scale
| Field | Value |
|-------|-------|
| **ID** | PT-002 |
| **Name** | Search latency with 100K claims |
| **Priority** | High |
| **Prerequisites** | 100K claims indexed |
| **Steps** | 1. Execute 100 random queries<br>2. Measure p50, p95, p99 latency |
| **Expected** | p50 < 100ms, p95 < 500ms, p99 < 1s |
| **Pass Criteria** | No queries timeout (>5s) |

#### PT-003: Dashboard with 1000 Sessions
| Field | Value |
|-------|-------|
| **ID** | PT-003 |
| **Name** | Dashboard performance with many sessions |
| **Priority** | Medium |
| **Prerequisites** | 1000 sessions in database |
| **Steps** | 1. Load dashboard<br>2. Scroll through session list<br>3. Open random sessions |
| **Expected** | Smooth scrolling, <2s session load |
| **Pass Criteria** | No UI freezing or crashes |

#### PT-004: WebSocket Broadcast Scalability
| Field | Value |
|-------|-------|
| **ID** | PT-004 |
| **Name** | Broadcast events to 100 clients |
| **Priority** | Medium |
| **Prerequisites** | Dashboard running, load test tool |
| **Steps** | 1. Connect 100 WebSocket clients<br>2. Send event burst (10 events/second)<br>3. Verify all clients receive |
| **Expected** | All clients receive events within 5 seconds |
| **Pass Criteria** | No dropped connections, no missed events |

---

### 4.5 UI/UX Tests (UI)

#### UI-001: Responsive Layout - Mobile
| Field | Value |
|-------|-------|
| **ID** | UI-001 |
| **Name** | Dashboard usable on mobile viewport |
| **Priority** | Medium |
| **Prerequisites** | Dashboard running |
| **Steps** | 1. Open Chrome DevTools<br>2. Set viewport to 375x667 (iPhone SE)<br>3. Navigate dashboard |
| **Expected** | All content accessible, no horizontal scroll |
| **Pass Criteria** | Can view sessions, events, and details |

#### UI-002: Session Panel Interactions
| Field | Value |
|-------|-------|
| **ID** | UI-002 |
| **Name** | Session panel collapse/expand works |
| **Priority** | Medium |
| **Prerequisites** | Dashboard with sessions |
| **Steps** | 1. Click session to expand<br>2. Click again to collapse<br>3. Verify animation smoothness |
| **Expected** | Smooth animation, correct state toggle |
| **Pass Criteria** | No visual glitches, state persists |

#### UI-003: Event Timeline Scrolling
| Field | Value |
|-------|-------|
| **ID** | UI-003 |
| **Name** | Event timeline scrolls smoothly |
| **Priority** | Medium |
| **Prerequisites** | Session with 100+ events |
| **Steps** | 1. Open session with many events<br>2. Scroll through timeline<br>3. Check for jank |
| **Expected** | 60 FPS scrolling, no dropped frames |
| **Pass Criteria** | Smooth scrolling in Chrome/Firefox |

#### UI-004: Agent Color Coding
| Field | Value |
|-------|-------|
| **ID** | UI-004 |
| **Name** | Agent types have consistent colors |
| **Priority** | Low |
| **Prerequisites** | Events from multiple agent types |
| **Steps** | 1. View events from different agents<br>2. Verify color consistency<br>3. Check color contrast |
| **Expected** | Each agent type has unique, consistent color |
| **Pass Criteria** | Colors match Tokyo Night theme |

#### UI-005: Dark Theme Accessibility
| Field | Value |
|-------|-------|
| **ID** | UI-005 |
| **Name** | Dark theme meets contrast requirements |
| **Priority** | Medium |
| **Prerequisites** | Dashboard running |
| **Steps** | 1. Use browser accessibility tools<br>2. Check text contrast ratios<br>3. Verify focus indicators |
| **Expected** | WCAG AA compliance (4.5:1 contrast) |
| **Pass Criteria** | All text readable, focus visible |

---

### 4.6 Installation Tests (IN)

#### IN-001: Windows Installation
| Field | Value |
|-------|-------|
| **ID** | IN-001 |
| **Name** | Install on Windows 10/11 |
| **Priority** | High |
| **Prerequisites** | Clean Windows VM, Python 3.10+ |
| **Steps** | 1. Clone repository<br>2. Run `python scripts/install.py`<br>3. Start dashboard<br>4. Verify functionality |
| **Expected** | Installation completes without errors |
| **Pass Criteria** | Dashboard starts, events can be sent |

#### IN-002: macOS Installation
| Field | Value |
|-------|-------|
| **ID** | IN-002 |
| **Name** | Install on macOS 12+ |
| **Priority** | High |
| **Prerequisites** | Clean macOS VM, Python 3.10+ |
| **Steps** | 1. Clone repository<br>2. Run `python scripts/install.py`<br>3. Start dashboard<br>4. Verify functionality |
| **Expected** | Installation completes without errors |
| **Pass Criteria** | Dashboard starts, events can be sent |

#### IN-003: Linux Installation
| Field | Value |
|-------|-------|
| **ID** | IN-003 |
| **Name** | Install on Ubuntu 22.04 |
| **Priority** | High |
| **Prerequisites** | Clean Ubuntu VM, Python 3.10+ |
| **Steps** | 1. Clone repository<br>2. Run `python scripts/install.py`<br>3. Start dashboard<br>4. Verify functionality |
| **Expected** | Installation completes without errors |
| **Pass Criteria** | Dashboard starts, events can be sent |

#### IN-004: WSL2 Installation
| Field | Value |
|-------|-------|
| **ID** | IN-004 |
| **Name** | Install on Windows WSL2 |
| **Priority** | Medium |
| **Prerequisites** | Windows with WSL2, Ubuntu distro |
| **Steps** | 1. Clone repository in WSL2<br>2. Run `python scripts/install.py`<br>3. Access from Windows browser |
| **Expected** | Installation completes, accessible from Windows |
| **Pass Criteria** | Dashboard accessible at localhost from Windows |

---

## 5. Execution Checklists

### 5.1 Pre-Deployment Checklist

- [ ] All automated tests pass (1,226/1,240)
- [ ] Smoke tests pass on target environment
- [ ] No critical/high bugs open
- [ ] Documentation updated (CHANGELOG, README)
- [ ] Version numbers aligned across codebase
- [ ] Dependencies pinned in requirements.txt
- [ ] Database migrations tested (if applicable)
- [ ] Rollback procedure documented

### 5.2 Deployment Execution Checklist

- [ ] Backup current production database
- [ ] Deploy to staging environment first
- [ ] Run smoke tests on staging
- [ ] Run critical integration tests on staging
- [ ] Verify logging and monitoring active
- [ ] Deploy to production
- [ ] Run smoke tests on production
- [ ] Monitor error rates for 1 hour

### 5.3 Post-Deployment Checklist

- [ ] All smoke tests pass on production
- [ ] No elevated error rates
- [ ] Dashboard accessible and responsive
- [ ] WebSocket connections stable
- [ ] Database performance acceptable
- [ ] Notify stakeholders of successful deployment
- [ ] Update deployment log

### 5.4 Rollback Criteria

Initiate rollback if ANY of the following occur:
- [ ] Smoke tests fail on production
- [ ] Error rate exceeds 5% for 10+ minutes
- [ ] Dashboard inaccessible for 5+ minutes
- [ ] Data corruption detected
- [ ] Critical security vulnerability discovered

---

## 6. Bug Reporting Template

```markdown
## Bug Report

### Summary
[One-line description of the issue]

### Environment
- **OS:** [e.g., Windows 11, macOS 14, Ubuntu 22.04]
- **Python Version:** [e.g., 3.10.12]
- **Browser:** [e.g., Chrome 120.0.6099.109]
- **Dashboard Version:** [e.g., 2.7.0]

### Steps to Reproduce
1. [First step]
2. [Second step]
3. [Third step]

### Expected Behavior
[What should happen]

### Actual Behavior
[What actually happens]

### Evidence
- **Screenshots:** [Attach if applicable]
- **Console Logs:** [Paste relevant logs]
- **Network Tab:** [If API-related]

### Impact Assessment
- **Severity:** [Critical / High / Medium / Low]
- **Frequency:** [Always / Sometimes / Rarely]
- **Workaround:** [Yes - describe / No]

### Additional Context
[Any other relevant information]
```

---

## 7. Sign-Off Criteria

### 7.1 Release Approval Requirements

| Criteria | Threshold | Required |
|----------|-----------|----------|
| Automated tests | 100% pass (excluding expected skips) | Yes |
| Smoke tests | 100% pass | Yes |
| Critical integration tests | 100% pass | Yes |
| High-priority tests | 95% pass | Yes |
| Medium-priority tests | 90% pass | No |
| Open critical bugs | 0 | Yes |
| Open high bugs | ≤2 | Yes |
| Performance regression | <20% | Yes |

### 7.2 Sign-Off Authorities

| Role | Responsibility |
|------|----------------|
| **QA Lead** | Test execution completeness |
| **Dev Lead** | Technical approval |
| **Product Owner** | Feature acceptance |
| **DevOps** | Deployment readiness |

### 7.3 Sign-Off Form

```markdown
## Release Sign-Off: Agent Dashboard v2.7.0

### Test Results Summary
- **Automated Tests:** ____/1240 passed
- **Smoke Tests:** ____/5 passed
- **Integration Tests:** ____/5 passed
- **E2E Tests:** ____/3 passed
- **Performance Tests:** ____/4 passed
- **UI/UX Tests:** ____/5 passed
- **Installation Tests:** ____/4 passed

### Open Issues
- **Critical:** ____
- **High:** ____
- **Medium:** ____
- **Low:** ____

### Approvals
- [ ] QA Lead: _________________ Date: _______
- [ ] Dev Lead: ________________ Date: _______
- [ ] Product Owner: ___________ Date: _______
- [ ] DevOps: __________________ Date: _______

### Decision
- [ ] **APPROVED** for release
- [ ] **CONDITIONAL** - requires: _______________
- [ ] **REJECTED** - reason: ___________________
```

---

## Appendix A: Test Data Generation

### Generate Large Dataset
```bash
python scripts/generate_test_data.py --claims 100000 --output tests/fixtures/scale.json
```

### Generate Test Queries
```bash
python scripts/generate_test_queries.py --count 100 --output tests/fixtures/stress_queries.json
```

---

## Appendix B: Quick Reference

### Smoke Test Commands
```bash
# Start dashboard
python src/web_server.py

# Send test event
python hooks/send_event.py --type tool_start --tool Read

# Check API health
curl http://localhost:4200/api/sessions
```

### Performance Test Commands
```bash
# Run benchmarks
python -m pytest tests/benchmarks/ -v --benchmark-only

# Load test WebSocket
python scripts/websocket_load_test.py --clients 100 --duration 60
```

---

*Document Version: 1.0*
*Created: 2025-12-26*
*Last Updated: 2025-12-26*
*Author: Agent Dashboard Team*
