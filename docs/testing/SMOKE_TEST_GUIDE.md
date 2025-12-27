# Smoke Test Guide

## Overview

This guide covers the execution of smoke tests (ST-001 through ST-005) for Agent Dashboard v2.7.0. Smoke tests verify core functionality and should complete in under 15 minutes.

## Objectives

- Verify dashboard starts and serves homepage
- Confirm WebSocket connections are established
- Validate event ingestion pipeline
- Check API health endpoints
- Verify database persistence

## Prerequisites

- Python 3.10+ installed
- Dependencies installed (aiohttp, rich)
- No other service running on port 4200
- Terminal/command prompt access

## Setup

1. Navigate to project directory:
   ```bash
   cd agent-dashboard
   ```

2. Verify environment:
   ```bash
   python scripts/manual_tests/check_test_environment.py
   ```

3. Start the dashboard (in a separate terminal):
   ```bash
   python src/web_server.py --port 4200
   ```

## Test Execution

### Automated Execution

Run all smoke tests automatically:

```bash
python scripts/manual_tests/run_smoke_tests.py --verbose
```

### Manual Execution

#### ST-001: Dashboard Startup

**Steps:**
1. Open browser to http://localhost:4200
2. Verify page loads within 5 seconds
3. Check for no console errors (F12 > Console)

**Expected Results:**
- Homepage displays with Agent Dashboard title
- Session list panel visible
- No JavaScript errors in console

**Pass Criteria:** Page loads, no errors

---

#### ST-002: WebSocket Connection

**Steps:**
1. Open browser DevTools (F12)
2. Navigate to Network tab
3. Filter by "WS" (WebSocket)
4. Refresh the dashboard

**Expected Results:**
- WebSocket connection shows "101 Switching Protocols"
- Connection status in UI shows "Connected"

**Pass Criteria:** WebSocket established

---

#### ST-003: Event Ingestion

**Steps:**
1. In terminal, run:
   ```bash
   python hooks/send_event.py --event-type PreToolUse --agent-name test
   ```
2. Observe dashboard

**Expected Results:**
- Event appears in timeline within 1 second
- Event shows correct type and timestamp

**Pass Criteria:** Event visible in dashboard

---

#### ST-004: API Health Check

**Steps:**
1. Run in terminal:
   ```bash
   curl http://localhost:4200/api/sessions
   curl http://localhost:4200/api/events
   ```

**Expected Results:**
- Both return HTTP 200
- Valid JSON responses

**Pass Criteria:** HTTP 200, valid JSON

---

#### ST-005: Database Access

**Steps:**
1. Send a test event
2. Restart the dashboard (Ctrl+C, then restart)
3. Check if event persisted

**Expected Results:**
- Previous events visible after restart

**Pass Criteria:** Data persists across restarts

---

## Reporting

After running tests:

1. Record results in test report:
   ```bash
   python scripts/manual_tests/run_smoke_tests.py --output smoke_results.json
   ```

2. For failures, capture:
   - Screenshot of the issue
   - Console logs
   - Network tab output
   - Steps to reproduce

## Common Issues

| Issue | Solution |
|-------|----------|
| Port 4200 in use | Kill existing process or use --port flag |
| WebSocket fails | Check firewall settings |
| Events not appearing | Verify dashboard URL in hooks |
| Database errors | Check ~/.claude/agent_dashboard.db permissions |

## Metrics to Collect

- [ ] Dashboard load time (target: <5s)
- [ ] WebSocket connection time (target: <1s)
- [ ] Event display latency (target: <1s)
- [ ] API response time (target: <500ms)

## Sign-Off

- [ ] All 5 smoke tests pass
- [ ] No critical errors in logs
- [ ] Performance within targets

---

*Document Version: 1.0.0*
*Last Updated: 2025-12-26*
