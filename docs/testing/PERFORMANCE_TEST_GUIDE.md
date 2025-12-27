# Performance Test Guide

## Overview

Performance tests (PT-001 through PT-004) evaluate Agent Dashboard at scale. These tests require 2-8 hours depending on dataset size.

## Objectives

- Benchmark 100K claim ingestion
- Measure search latency at scale
- Test dashboard with 1000 sessions
- Evaluate WebSocket broadcast scalability

## Prerequisites

- Large test dataset (10K+ claims)
- 8GB+ RAM available
- Dashboard running in production mode

## Setup

1. Generate large dataset:
   ```bash
   python scripts/generate_test_data.py --claims 100000 --output tests/fixtures/scale.json
   ```

2. Start dashboard with monitoring:
   ```bash
   python src/web_server.py --port 4200
   ```

## Test Procedures

### PT-001: 100K Claim Ingestion

**Objective:** Ingest 100,000 claims within performance targets

**Steps:**
1. Time ingestion of 100K claims
2. Monitor memory usage
3. Verify all claims stored

**Target Metrics:**
- Duration: <10 minutes
- Memory: <4GB RAM
- Success: 100% claims stored

**Commands:**
```bash
python scripts/manual_tests/run_performance_tests.py --fixture tests/fixtures/scale.json
```

---

### PT-002: Search Latency at Scale

**Objective:** Search performance with 100K claims indexed

**Steps:**
1. Execute 100 random queries
2. Measure p50, p95, p99 latency
3. Verify no timeouts

**Target Metrics:**
- p50: <100ms
- p95: <500ms
- p99: <1s
- Timeouts: 0

---

### PT-003: Dashboard with 1000 Sessions

**Objective:** UI performance with many sessions

**Steps:**
1. Populate 1000 sessions in database
2. Load dashboard
3. Scroll through session list
4. Open random sessions

**Target Metrics:**
- Initial load: <5s
- Scroll: 60 FPS
- Session load: <2s

---

### PT-004: WebSocket Broadcast Scalability

**Objective:** Broadcast events to 100 concurrent clients

**Steps:**
1. Connect 100 WebSocket clients
2. Send event burst (10 events/second)
3. Verify all clients receive

**Commands:**
```bash
python scripts/manual_tests/websocket_load_test.py --clients 100 --duration 60 --events-per-sec 10
```

**Target Metrics:**
- Connections: 100% successful
- Delivery: <5s latency
- Drops: 0%

---

## Performance Metrics Collection

| Metric | Tool | Command |
|--------|------|---------|
| Memory | psutil | python -c "import psutil; print(psutil.Process().memory_info().rss / 1024**2)" |
| CPU | psutil | python -c "import psutil; print(psutil.cpu_percent())" |
| Latency | time | Built into test scripts |

## Baseline Comparison

| Metric | v2.6.0 | v2.7.0 | Delta |
|--------|--------|--------|-------|
| Ingestion (100K) | 8 min | _____ | _____ |
| Query p50 | 80ms | _____ | _____ |
| Memory peak | 3.2GB | _____ | _____ |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| OOM errors | Increase memory, use batching |
| Slow queries | Rebuild indexes |
| WebSocket drops | Check event loop blocking |

## Sign-Off

- [ ] All performance tests pass
- [ ] No regression from baseline
- [ ] Memory stable under load

---

*Document Version: 1.0.0*
*Last Updated: 2025-12-26*
