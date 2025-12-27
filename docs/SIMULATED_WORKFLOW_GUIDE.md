# Simulated LLM Project Workflow Guide

## Overview

This guide provides a step-by-step simulation of a realistic LLM-assisted development workflow using the Agent Dashboard v2.7.0. Follow these instructions to evaluate the system's capabilities in a production-like scenario.

**Estimated Time:** 45-60 minutes
**Prerequisites:** Agent Dashboard running on `http://localhost:4200`

---

## Workflow Scenario

**Project:** Build a REST API for a Task Management System
**Simulated Agents:** Planner, Researcher, Implementer, Validator
**Duration:** 3 development phases over a simulated "session"

---

## Phase 1: Project Planning (15 minutes)

### Step 1.1: Start the Dashboard

```bash
# Terminal 1: Start the Agent Dashboard
cd "I:/My Drive/CSC/Projects/Datalogger harvester 2/agent-dashboard"
python src/web_server.py
```

**Success Criteria:**
- [ ] Dashboard accessible at `http://localhost:4200`
- [ ] No error messages in terminal
- [ ] WebSocket connection indicator shows "Connected"

### Step 1.2: Initialize a New Session

Open a new terminal and run:

```bash
# Terminal 2: Send session start event
cd "I:/My Drive/CSC/Projects/Datalogger harvester 2/agent-dashboard"

python -c "
import requests
import json
from datetime import datetime

event = {
    'type': 'session_start',
    'session_id': 'SIM-001',
    'timestamp': datetime.now().isoformat(),
    'data': {
        'project': 'Task Management API',
        'objective': 'Build REST API with CRUD operations',
        'agents': ['planner', 'researcher', 'implementer', 'validator']
    }
}

resp = requests.post('http://localhost:4200/api/events', json=event)
print(f'Session started: {resp.status_code}')
"
```

**Success Criteria:**
- [ ] Response status code is 200
- [ ] New session appears in Dashboard sidebar
- [ ] Session shows "Task Management API" label

### Step 1.3: Simulate Planner Agent Activity

```bash
python -c "
import requests
import json
from datetime import datetime
import time

events = [
    {
        'type': 'agent_start',
        'session_id': 'SIM-001',
        'timestamp': datetime.now().isoformat(),
        'data': {
            'agent': 'planner',
            'task': 'Create project specification'
        }
    },
    {
        'type': 'tool_call',
        'session_id': 'SIM-001',
        'timestamp': datetime.now().isoformat(),
        'data': {
            'agent': 'planner',
            'tool': 'Read',
            'args': {'file': 'requirements.md'},
            'status': 'success'
        }
    },
    {
        'type': 'knowledge_claim',
        'session_id': 'SIM-001',
        'timestamp': datetime.now().isoformat(),
        'data': {
            'agent': 'planner',
            'claim': 'The API requires User, Task, and Project entities',
            'confidence': 0.95,
            'source': 'requirements.md'
        }
    },
    {
        'type': 'agent_complete',
        'session_id': 'SIM-001',
        'timestamp': datetime.now().isoformat(),
        'data': {
            'agent': 'planner',
            'status': 'success',
            'artifacts': ['SPEC.md'],
            'summary': 'Created project specification with 3 entities and 12 endpoints'
        }
    }
]

for event in events:
    resp = requests.post('http://localhost:4200/api/events', json=event)
    print(f'{event[\"type\"]}: {resp.status_code}')
    time.sleep(0.5)
"
```

**Success Criteria:**
- [ ] All 4 events show status 200
- [ ] Dashboard timeline shows planner activity
- [ ] Events display in chronological order
- [ ] Tool call shows "Read" with file argument

### Step 1.4: Verify Phase 1 in Dashboard

Open `http://localhost:4200` and verify:

| Check | Expected | Actual | Pass? |
|-------|----------|--------|-------|
| Session visible | SIM-001 in sidebar | | |
| Event count | 5 events (1 start + 4 planner) | | |
| Agent indicator | Planner shown with color | | |
| Timeline order | Chronological | | |

---

## Phase 2: Research & Implementation (20 minutes)

### Step 2.1: Simulate Researcher Agent

```bash
python -c "
import requests
import json
from datetime import datetime
import time

events = [
    {
        'type': 'agent_start',
        'session_id': 'SIM-001',
        'timestamp': datetime.now().isoformat(),
        'data': {
            'agent': 'researcher',
            'task': 'Research REST API best practices'
        }
    },
    {
        'type': 'tool_call',
        'session_id': 'SIM-001',
        'timestamp': datetime.now().isoformat(),
        'data': {
            'agent': 'researcher',
            'tool': 'WebSearch',
            'args': {'query': 'REST API design patterns 2024'},
            'status': 'success'
        }
    },
    {
        'type': 'knowledge_claim',
        'session_id': 'SIM-001',
        'timestamp': datetime.now().isoformat(),
        'data': {
            'agent': 'researcher',
            'claim': 'Use HTTP status codes: 200 OK, 201 Created, 400 Bad Request, 404 Not Found',
            'confidence': 0.98,
            'source': 'REST API Best Practices Guide'
        }
    },
    {
        'type': 'knowledge_claim',
        'session_id': 'SIM-001',
        'timestamp': datetime.now().isoformat(),
        'data': {
            'agent': 'researcher',
            'claim': 'Implement pagination for list endpoints using limit and offset parameters',
            'confidence': 0.92,
            'source': 'API Design Guidelines'
        }
    },
    {
        'type': 'agent_complete',
        'session_id': 'SIM-001',
        'timestamp': datetime.now().isoformat(),
        'data': {
            'agent': 'researcher',
            'status': 'success',
            'artifacts': ['RESEARCH_NOTES.md'],
            'summary': 'Documented 5 best practices for REST API design'
        }
    }
]

for event in events:
    resp = requests.post('http://localhost:4200/api/events', json=event)
    print(f'{event[\"type\"]}: {resp.status_code}')
    time.sleep(0.3)
"
```

**Success Criteria:**
- [ ] All 5 events recorded successfully
- [ ] WebSearch tool call visible in timeline
- [ ] Knowledge claims displayed with confidence scores

### Step 2.2: Simulate Implementer Agent

```bash
python -c "
import requests
import json
from datetime import datetime
import time

events = [
    {
        'type': 'agent_start',
        'session_id': 'SIM-001',
        'timestamp': datetime.now().isoformat(),
        'data': {
            'agent': 'implementer',
            'task': 'Implement User API endpoints'
        }
    },
    {
        'type': 'tool_call',
        'session_id': 'SIM-001',
        'timestamp': datetime.now().isoformat(),
        'data': {
            'agent': 'implementer',
            'tool': 'Write',
            'args': {'file': 'src/api/users.py'},
            'status': 'success'
        }
    },
    {
        'type': 'tool_call',
        'session_id': 'SIM-001',
        'timestamp': datetime.now().isoformat(),
        'data': {
            'agent': 'implementer',
            'tool': 'Write',
            'args': {'file': 'src/models/user.py'},
            'status': 'success'
        }
    },
    {
        'type': 'tool_call',
        'session_id': 'SIM-001',
        'timestamp': datetime.now().isoformat(),
        'data': {
            'agent': 'implementer',
            'tool': 'Bash',
            'args': {'command': 'python -m pytest tests/test_users.py'},
            'status': 'success',
            'result': '5 passed in 0.3s'
        }
    },
    {
        'type': 'knowledge_claim',
        'session_id': 'SIM-001',
        'timestamp': datetime.now().isoformat(),
        'data': {
            'agent': 'implementer',
            'claim': 'User model has fields: id, username, email, created_at',
            'confidence': 1.0,
            'source': 'src/models/user.py'
        }
    },
    {
        'type': 'agent_complete',
        'session_id': 'SIM-001',
        'timestamp': datetime.now().isoformat(),
        'data': {
            'agent': 'implementer',
            'status': 'success',
            'artifacts': ['src/api/users.py', 'src/models/user.py', 'tests/test_users.py'],
            'summary': 'Implemented User CRUD with 5 endpoints, all tests passing'
        }
    }
]

for event in events:
    resp = requests.post('http://localhost:4200/api/events', json=event)
    print(f'{event[\"type\"]}: {resp.status_code}')
    time.sleep(0.3)
"
```

**Success Criteria:**
- [ ] All 6 events recorded
- [ ] Multiple tool calls visible (Write x2, Bash x1)
- [ ] Test result "5 passed" visible in Bash event
- [ ] Artifacts list shows 3 files

### Step 2.3: Simulate an Error Scenario

```bash
python -c "
import requests
import json
from datetime import datetime
import time

events = [
    {
        'type': 'agent_start',
        'session_id': 'SIM-001',
        'timestamp': datetime.now().isoformat(),
        'data': {
            'agent': 'implementer',
            'task': 'Implement Task API endpoints'
        }
    },
    {
        'type': 'tool_call',
        'session_id': 'SIM-001',
        'timestamp': datetime.now().isoformat(),
        'data': {
            'agent': 'implementer',
            'tool': 'Write',
            'args': {'file': 'src/api/tasks.py'},
            'status': 'success'
        }
    },
    {
        'type': 'tool_call',
        'session_id': 'SIM-001',
        'timestamp': datetime.now().isoformat(),
        'data': {
            'agent': 'implementer',
            'tool': 'Bash',
            'args': {'command': 'python -m pytest tests/test_tasks.py'},
            'status': 'error',
            'error': 'AssertionError: Expected 201, got 500'
        }
    },
    {
        'type': 'error',
        'session_id': 'SIM-001',
        'timestamp': datetime.now().isoformat(),
        'data': {
            'agent': 'implementer',
            'error_type': 'TestFailure',
            'message': 'test_create_task failed: Internal Server Error',
            'traceback': 'File \"tests/test_tasks.py\", line 42'
        }
    },
    {
        'type': 'tool_call',
        'session_id': 'SIM-001',
        'timestamp': datetime.now().isoformat(),
        'data': {
            'agent': 'implementer',
            'tool': 'Edit',
            'args': {'file': 'src/api/tasks.py', 'fix': 'Add missing database commit'},
            'status': 'success'
        }
    },
    {
        'type': 'tool_call',
        'session_id': 'SIM-001',
        'timestamp': datetime.now().isoformat(),
        'data': {
            'agent': 'implementer',
            'tool': 'Bash',
            'args': {'command': 'python -m pytest tests/test_tasks.py'},
            'status': 'success',
            'result': '4 passed in 0.2s'
        }
    },
    {
        'type': 'agent_complete',
        'session_id': 'SIM-001',
        'timestamp': datetime.now().isoformat(),
        'data': {
            'agent': 'implementer',
            'status': 'success',
            'artifacts': ['src/api/tasks.py'],
            'summary': 'Fixed database commit issue, Task API now working'
        }
    }
]

for event in events:
    resp = requests.post('http://localhost:4200/api/events', json=event)
    print(f'{event[\"type\"]}: {resp.status_code}')
    time.sleep(0.3)
"
```

**Success Criteria:**
- [ ] Error event displayed with red/warning indicator
- [ ] Error → Fix → Retry flow visible in timeline
- [ ] Final success after fix is clear

---

## Phase 3: Validation & Summary (10 minutes)

### Step 3.1: Simulate Validator Agent

```bash
python -c "
import requests
import json
from datetime import datetime
import time

events = [
    {
        'type': 'agent_start',
        'session_id': 'SIM-001',
        'timestamp': datetime.now().isoformat(),
        'data': {
            'agent': 'validator',
            'task': 'Run full test suite and validation'
        }
    },
    {
        'type': 'tool_call',
        'session_id': 'SIM-001',
        'timestamp': datetime.now().isoformat(),
        'data': {
            'agent': 'validator',
            'tool': 'Bash',
            'args': {'command': 'python -m pytest --cov=src'},
            'status': 'success',
            'result': '15 passed, coverage: 87%'
        }
    },
    {
        'type': 'tool_call',
        'session_id': 'SIM-001',
        'timestamp': datetime.now().isoformat(),
        'data': {
            'agent': 'validator',
            'tool': 'Bash',
            'args': {'command': 'python -m mypy src/'},
            'status': 'success',
            'result': 'Success: no issues found'
        }
    },
    {
        'type': 'knowledge_claim',
        'session_id': 'SIM-001',
        'timestamp': datetime.now().isoformat(),
        'data': {
            'agent': 'validator',
            'claim': 'All 15 tests passing with 87% code coverage',
            'confidence': 1.0,
            'source': 'pytest output'
        }
    },
    {
        'type': 'agent_complete',
        'session_id': 'SIM-001',
        'timestamp': datetime.now().isoformat(),
        'data': {
            'agent': 'validator',
            'status': 'success',
            'artifacts': ['coverage_report.html'],
            'summary': 'Validation complete: 15 tests, 87% coverage, 0 type errors'
        }
    }
]

for event in events:
    resp = requests.post('http://localhost:4200/api/events', json=event)
    print(f'{event[\"type\"]}: {resp.status_code}')
    time.sleep(0.3)
"
```

### Step 3.2: End the Session

```bash
python -c "
import requests
import json
from datetime import datetime

event = {
    'type': 'session_end',
    'session_id': 'SIM-001',
    'timestamp': datetime.now().isoformat(),
    'data': {
        'status': 'success',
        'duration_minutes': 45,
        'summary': {
            'agents_used': ['planner', 'researcher', 'implementer', 'validator'],
            'files_created': 6,
            'tests_written': 15,
            'coverage': '87%',
            'knowledge_claims': 5
        }
    }
}

resp = requests.post('http://localhost:4200/api/events', json=event)
print(f'Session ended: {resp.status_code}')
"
```

**Success Criteria:**
- [ ] Session marked as complete in dashboard
- [ ] Total event count matches expected (~25 events)
- [ ] Session summary visible

---

## Evaluation Checklist

### Dashboard Functionality

| Feature | Test | Pass? |
|---------|------|-------|
| Session List | Sessions appear in sidebar | |
| Event Timeline | Events display chronologically | |
| Agent Colors | Different agents have different colors | |
| Tool Calls | Tool names and arguments visible | |
| Error Display | Errors highlighted distinctly | |
| WebSocket | Real-time updates without refresh | |
| Persistence | Events persist after page reload | |

### Data Integrity

| Check | Method | Pass? |
|-------|--------|-------|
| Event Count | API returns correct count | |
| Session Data | All fields stored correctly | |
| Timestamps | Chronological order preserved | |
| No Data Loss | All sent events received | |

### Performance

| Metric | Target | Actual | Pass? |
|--------|--------|--------|-------|
| Event Ingestion | <100ms per event | | |
| Dashboard Load | <2 seconds | | |
| Timeline Scroll | Smooth (60fps) | | |
| Memory Usage | <500MB | | |

---

## Advanced Evaluation: Test the Knowledge Features

### Test BM25 Search

```bash
python -c "
from src.knowledge.bm25 import BM25Index

# Create index with session knowledge
index = BM25Index()
claims = [
    ('c1', 'The API requires User, Task, and Project entities'),
    ('c2', 'Use HTTP status codes: 200 OK, 201 Created, 400 Bad Request'),
    ('c3', 'Implement pagination using limit and offset parameters'),
    ('c4', 'User model has fields: id, username, email, created_at'),
    ('c5', 'All 15 tests passing with 87% code coverage'),
]

for cid, text in claims:
    index.add_document(cid, text)

# Search
results = index.search('User API fields', limit=3)
print('Search: \"User API fields\"')
for doc_id, score in results:
    print(f'  {doc_id}: {score:.3f}')
"
```

**Success Criteria:**
- [ ] Search returns relevant claims (c4 should rank high)
- [ ] Scores are reasonable (0.0 - 1.0 range)

### Test Provenance Tracking

```bash
python -c "
from src.audit.provenance import EntityProvenanceTracker, EntityRole
from src.knowledge.graph import Entity, EntityType

tracker = EntityProvenanceTracker()

# Record entities from session
entities = [
    ('User', EntityType.CLASS, 'implementer created User model'),
    ('Task', EntityType.CLASS, 'implementer created Task model'),
    ('users.py', EntityType.FILE, 'implementer wrote API endpoints'),
]

for name, etype, note in entities:
    entity = Entity(name=name, entity_type=etype)
    tracker.record(entity, EntityRole.SUBJECT, f'entry-{name}')

# Query provenance
print('Entities tracked:')
for name, _, _ in entities:
    ents = tracker.get_entities_by_name(name)
    print(f'  {name}: {len(ents)} record(s)')
"
```

**Success Criteria:**
- [ ] All 3 entities tracked
- [ ] Provenance queryable by name

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Dashboard won't start | Check port 4200 is free: `netstat -an \| findstr 4200` |
| Events not appearing | Verify WebSocket connection in browser DevTools |
| API returns 500 | Check terminal for Python errors |
| Session not persisting | Verify SQLite database at `~/.claude/agent_dashboard.db` |

### Debug Commands

```bash
# Check API health
curl http://localhost:4200/api/sessions

# View recent events
curl http://localhost:4200/api/events?limit=10

# Check database
sqlite3 ~/.claude/agent_dashboard.db ".tables"
```

---

## Success Criteria Summary

### Minimum Requirements (Must Pass)

- [ ] Dashboard starts and serves UI
- [ ] Events can be sent via API
- [ ] Events display in real-time
- [ ] Session data persists across restarts
- [ ] Multiple agent types display correctly

### Extended Requirements (Should Pass)

- [ ] Error events highlighted distinctly
- [ ] Knowledge claims display with confidence
- [ ] Search finds relevant claims
- [ ] Provenance tracking works
- [ ] Performance within targets

### Stretch Goals (Nice to Have)

- [ ] 100+ events handled smoothly
- [ ] Multiple concurrent sessions
- [ ] Export session to report
- [ ] Full workflow without errors

---

## Final Verification

After completing the simulation, verify:

```bash
python -c "
import requests

# Get session summary
resp = requests.get('http://localhost:4200/api/sessions')
sessions = resp.json()
print(f'Total sessions: {len(sessions)}')

# Get event count
resp = requests.get('http://localhost:4200/api/events?session_id=SIM-001')
events = resp.json()
print(f'Events in SIM-001: {len(events)}')

# Verify event types
types = {}
for e in events:
    t = e.get('type', 'unknown')
    types[t] = types.get(t, 0) + 1

print('Event breakdown:')
for t, count in sorted(types.items()):
    print(f'  {t}: {count}')
"
```

**Expected Output:**
```
Total sessions: 1
Events in SIM-001: ~25
Event breakdown:
  agent_complete: 5
  agent_start: 5
  error: 1
  knowledge_claim: 5
  session_end: 1
  session_start: 1
  tool_call: ~10
```

---

## Conclusion

If all minimum requirements pass, the Agent Dashboard is functioning correctly for production use. Document any issues found in the bug report template at `templates/bug_report_template.md`.

**Report Generated:** Agent Dashboard v2.7.0 Simulation Guide
