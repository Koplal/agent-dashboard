# Post-Deployment Checklist

## Agent Dashboard v2.7.0

**Deployment Completed:** _______________
**Verified By:** _______________
**Environment:** [ ] Staging [ ] Production

---

## 1. Immediate Verification (0-5 minutes)

| Check | Status | Time |
|-------|--------|------|
| Dashboard accessible | [ ] Yes [ ] No | _____ |
| Homepage loads | [ ] Yes [ ] No | _____ |
| No console errors | [ ] Yes [ ] No | _____ |
| WebSocket connects | [ ] Yes [ ] No | _____ |

---

## 2. Smoke Tests (5-15 minutes)

| Test | Status | Notes |
|------|--------|-------|
| ST-001: Dashboard Startup | [ ] Pass | |
| ST-002: WebSocket Connection | [ ] Pass | |
| ST-003: Event Ingestion | [ ] Pass | |
| ST-004: API Health Check | [ ] Pass | |
| ST-005: Database Access | [ ] Pass | |

---

## 3. Monitoring (15-60 minutes)

| Metric | Expected | Actual | Alert |
|--------|----------|--------|-------|
| Error rate | <1% | _____ | [ ] OK |
| Response time | <500ms | _____ | [ ] OK |
| CPU usage | <50% | _____ | [ ] OK |
| Memory usage | <2GB | _____ | [ ] OK |

---

## 4. Logging

| Check | Status |
|-------|--------|
| Logs being generated | [ ] Yes |
| No error spikes | [ ] Verified |
| Log level appropriate | [ ] Yes |

---

## 5. Database

| Check | Status |
|-------|--------|
| Connections stable | [ ] Yes |
| No lock issues | [ ] Verified |
| Queries performing well | [ ] Yes |

---

## 6. User Verification

| Check | Status |
|-------|--------|
| Key workflows tested | [ ] Yes |
| No user-reported issues | [ ] Verified |
| Performance acceptable | [ ] Yes |

---

## Rollback Criteria Met?

[ ] No - Continue monitoring
[ ] Yes - Initiate rollback (see rollback_checklist.md)

---

## Sign-Off

**Deployment verified by:**

| Role | Name | Time | Status |
|------|------|------|--------|
| DevOps | _________ | _____ | [ ] OK |
| QA | _________ | _____ | [ ] OK |

---

**Status:** [ ] DEPLOYMENT SUCCESSFUL [ ] REQUIRES ATTENTION

**Notes:**
_____________________________________________

---

*Template Version: 1.0.0*
