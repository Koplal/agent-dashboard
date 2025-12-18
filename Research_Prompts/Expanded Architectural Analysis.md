# Agent-Dashboard: Expanded Architectural Analysis (Supplement)

**Analysis Date:** December 2025  
**Version Analyzed:** v2.5.2  
**Scope:** Additional structural and workflow improvements beyond prompt engineering  
**Builds Upon:** STRUCTURAL_ARCHITECTURAL_ANALYSIS.md

---

## Executive Summary: Additional Findings

This supplement identifies **seven additional improvement areas** discovered through deep codebase analysis that were not covered in the initial structural review. These focus on internal consistency, developer experience, and operational maturity.

**New Priority Findings:**

| Category | Issue | Severity | Effort |
|----------|-------|----------|--------|
| Version Management | Inconsistent version numbers across modules | Medium | Low |
| Logging Hygiene | Mixed print()/logger patterns | Medium | Low |
| Test Coverage | Missing tests for cli.py, web_server.py | High | Medium |
| Agent Schema | No frontmatter validation | High | Medium |
| Error Contracts | Inconsistent exception handling | Medium | Medium |
| Token Counter Duplication | Same logic in 3 files | Low | Low |
| API Consistency | No versioning or rate limiting | Medium | High |

---

## Part 1: Internal Consistency Issues

### 1.1 Version Number Sprawl

**Current State:** Version numbers are inconsistent across the codebase.

| File | Version | Expected |
|------|---------|----------|
| src/cli.py | 2.2.1 | 2.5.2 |
| src/compression_gate.py | 2.2.1 | 2.5.2 |
| src/panel_selector.py | 2.2.1 | 2.5.2 |
| src/synthesis_validator.py | 2.2.1 | 2.5.2 |
| src/token_counter.py | 2.2.1 | 2.5.2 |
| src/validation.py | 2.2.1 | 2.5.2 |
| src/web_server.py | 2.4.0 | 2.5.2 |
| hooks/send_event.py | 2.4.0 | 2.5.2 |
| pyproject.toml | 2.3.0 | 2.5.2 |
| agents/*.md | 2.4.0–2.5.2 | 2.5.2 |

**Problem:** Users and developers cannot determine which version they're running. Debugging becomes difficult when version information is unreliable.

**Recommendation:** Implement single-source version management.

```python
# Proposed: src/__version__.py
__version__ = "2.5.2"
__version_info__ = tuple(int(x) for x in __version__.split("."))

# All other files import from here:
# from src.__version__ import __version__
```

Additionally, add a pre-commit hook or CI check that validates version consistency:

```bash
# scripts/check_versions.sh
#!/bin/bash
VERSION=$(grep "^version" pyproject.toml | sed 's/.*= "//' | sed 's/"//')
MISMATCHES=$(grep -r "Version:" src/ hooks/ | grep -v "$VERSION" | wc -l)
if [ "$MISMATCHES" -gt 0 ]; then
    echo "Version mismatch detected. Expected: $VERSION"
    grep -r "Version:" src/ hooks/ | grep -v "$VERSION"
    exit 1
fi
```

---

### 1.2 Logging Inconsistency

**Current State:** The codebase mixes `print()` statements with structured `logger` calls.

**Analysis:**
- 6 source modules use `logging.getLogger(__name__)` properly
- `cli.py` uses 50+ print() statements for user output
- `web_server.py` uses print() for startup messages

**Problem:** Structured logging cannot capture CLI output. Log aggregation misses critical events. Users cannot adjust verbosity.

**Recommendation:** Standardize on structured logging with a user-facing console handler.

```python
# Proposed: src/logging_config.py
import logging
import sys

def configure_logging(verbose: bool = False, json_output: bool = False):
    """Configure logging for both user output and structured logs."""
    
    root_logger = logging.getLogger("agent_dashboard")
    root_logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    # Console handler for user-facing output
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    
    if json_output:
        # Structured JSON for log aggregation
        formatter = logging.Formatter(
            '{"timestamp":"%(asctime)s","level":"%(levelname)s",'
            '"module":"%(name)s","message":"%(message)s"}'
        )
    else:
        # Human-readable for interactive use
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%H:%M:%S'
        )
    
    console.setFormatter(formatter)
    root_logger.addHandler(console)
    
    return root_logger

# Usage in cli.py:
# logger = configure_logging(verbose=args.verbose)
# logger.info("Dashboard not found at %s", dashboard_file)
```

---

### 1.3 Token Counter Code Duplication

**Current State:** Token counting logic exists in three separate locations.

| Location | Implementation |
|----------|----------------|
| src/token_counter.py | Full implementation with fallback chain |
| hooks/send_event.py | Standalone copy for import isolation |
| src/workflow_engine.py | Inline fallback implementation |

**Problem:** Bug fixes must be applied in multiple places. Behavior diverges over time.

**Recommendation:** Consolidate into single source with proper packaging.

```python
# Make token_counter importable from hooks
# hooks/__init__.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Then in hooks/send_event.py:
from token_counter import count_tokens, get_tokenizer_info
```

Alternatively, publish `token_counter` as a shared package:

```toml
# pyproject.toml
[tool.setuptools.packages.find]
include = ["src*", "hooks*"]

# This allows: from agent_dashboard.token_counter import count_tokens
```

---

## Part 2: Testing Gaps

### 2.1 Missing Module Tests

**Current State:**

| Source Module | Has Tests | Line Count |
|--------------|-----------|------------|
| compression_gate.py | ✅ | 467 |
| panel_selector.py | ✅ | 505 |
| synthesis_validator.py | ✅ | 469 |
| token_counter.py | ✅ | 270 |
| validation.py | ✅ | 242 |
| workflow_engine.py | ✅ | 1466 |
| **cli.py** | ❌ | 462 |
| **web_server.py** | ❌ | 1782 |

**Problem:** The two largest user-facing modules have no direct tests. CLI and web server bugs escape to production.

**Recommendation:** Add focused tests for critical paths.

```python
# tests/test_cli.py
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cli import (
    check_status,
    send_test_event,
    show_recent_events,
)

class TestCLI:
    """Tests for CLI commands."""
    
    def test_check_status_no_installation(self, tmp_path):
        """Status check fails gracefully when not installed."""
        with patch("cli.Path.home", return_value=tmp_path):
            result = check_status()
            assert result["installed"] is False
    
    def test_send_test_event_server_unavailable(self):
        """Test event gracefully handles server unavailable."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = ConnectionRefusedError()
            # Should not raise, should print error message
            result = send_test_event("http://localhost:4200", "test", "test")
            assert result is False
    
    @pytest.mark.parametrize("db_exists,event_count", [
        (False, 0),
        (True, 5),
    ])
    def test_show_recent_events(self, tmp_path, db_exists, event_count):
        """Recent events handles empty and populated databases."""
        db_path = tmp_path / "agent_dashboard.db"
        if db_exists:
            import sqlite3
            with sqlite3.connect(db_path) as conn:
                conn.execute("""
                    CREATE TABLE events (
                        id INTEGER PRIMARY KEY,
                        timestamp TEXT,
                        agent_name TEXT,
                        event_type TEXT
                    )
                """)
                for i in range(event_count):
                    conn.execute(
                        "INSERT INTO events VALUES (?, ?, ?, ?)",
                        (i, "2025-01-01", f"agent_{i}", "test")
                    )
        
        with patch("cli.Path.home", return_value=tmp_path.parent):
            events = show_recent_events(db_path)
            assert len(events) == event_count

# tests/test_web_server.py
import pytest
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

class TestWebServerEndpoints(AioHTTPTestCase):
    """Tests for web server API endpoints."""
    
    async def get_application(self):
        from web_server import AgentDashboard
        dashboard = AgentDashboard(db_path=":memory:")
        return dashboard.app
    
    @unittest_run_loop
    async def test_health_endpoint(self):
        """Health endpoint returns 200."""
        response = await self.client.get("/api/health")
        assert response.status == 200
        data = await response.json()
        assert data["status"] == "healthy"
    
    @unittest_run_loop
    async def test_events_post_valid(self):
        """Valid event post is accepted."""
        event = {
            "agent_name": "test",
            "event_type": "TestEvent",
            "session_id": "test-123",
            "project": "test-project",
        }
        response = await self.client.post("/events", json=event)
        assert response.status == 200
    
    @unittest_run_loop
    async def test_events_post_invalid(self):
        """Invalid event post returns 400."""
        response = await self.client.post("/events", json={})
        assert response.status == 400
```

---

### 2.2 Agent Definition Validation Tests

**Current State:** No tests verify agent definition file structure or content compliance.

**Problem:** Invalid agent definitions (typos, missing fields) are only discovered at runtime.

**Recommendation:** Add schema validation tests.

```python
# tests/test_agent_definitions.py
import pytest
from pathlib import Path
import yaml
import re

AGENTS_DIR = Path(__file__).parent.parent / "agents"

class TestAgentDefinitions:
    """Validate agent definition files against schema."""
    
    REQUIRED_FIELDS = ["name", "description", "tools", "model", "version", "tier"]
    VALID_MODELS = ["opus", "sonnet", "haiku"]
    VALID_TIERS = [0, 1, 2, 3]
    
    # Map tiers to expected models
    TIER_MODEL_MAP = {
        0: ["sonnet", "haiku"],  # Utility agents
        1: ["opus"],              # Strategic agents
        2: ["sonnet"],            # Analysis agents
        3: ["haiku"],             # Execution agents
    }
    
    @pytest.fixture
    def all_agent_files(self):
        return list(AGENTS_DIR.glob("*.md"))
    
    def parse_frontmatter(self, content: str) -> dict:
        """Extract YAML frontmatter from markdown."""
        match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if not match:
            return {}
        return yaml.safe_load(match.group(1))
    
    def test_all_agents_have_frontmatter(self, all_agent_files):
        """Every agent file must have valid YAML frontmatter."""
        for agent_file in all_agent_files:
            content = agent_file.read_text()
            assert content.startswith("---"), f"{agent_file.name}: Missing frontmatter"
            
            frontmatter = self.parse_frontmatter(content)
            assert frontmatter, f"{agent_file.name}: Invalid YAML in frontmatter"
    
    def test_required_fields_present(self, all_agent_files):
        """Every agent must have all required fields."""
        for agent_file in all_agent_files:
            content = agent_file.read_text()
            frontmatter = self.parse_frontmatter(content)
            
            for field in self.REQUIRED_FIELDS:
                assert field in frontmatter, \
                    f"{agent_file.name}: Missing required field '{field}'"
    
    def test_model_values_valid(self, all_agent_files):
        """Model field must be opus, sonnet, or haiku."""
        for agent_file in all_agent_files:
            content = agent_file.read_text()
            frontmatter = self.parse_frontmatter(content)
            model = frontmatter.get("model")
            
            assert model in self.VALID_MODELS, \
                f"{agent_file.name}: Invalid model '{model}'"
    
    def test_tier_values_valid(self, all_agent_files):
        """Tier field must be 0, 1, 2, or 3."""
        for agent_file in all_agent_files:
            content = agent_file.read_text()
            frontmatter = self.parse_frontmatter(content)
            tier = frontmatter.get("tier")
            
            assert tier in self.VALID_TIERS, \
                f"{agent_file.name}: Invalid tier '{tier}'"
    
    def test_tier_model_consistency(self, all_agent_files):
        """Agent tier should match expected model."""
        for agent_file in all_agent_files:
            content = agent_file.read_text()
            frontmatter = self.parse_frontmatter(content)
            
            tier = frontmatter.get("tier")
            model = frontmatter.get("model")
            expected_models = self.TIER_MODEL_MAP.get(tier, [])
            
            assert model in expected_models, \
                f"{agent_file.name}: Tier {tier} expects {expected_models}, got '{model}'"
    
    def test_version_consistency(self, all_agent_files):
        """All agents should have consistent version."""
        versions = set()
        for agent_file in all_agent_files:
            content = agent_file.read_text()
            frontmatter = self.parse_frontmatter(content)
            versions.add(frontmatter.get("version"))
        
        # Allow at most 2 versions during transition
        assert len(versions) <= 2, \
            f"Too many version variants: {versions}"
    
    def test_constraints_section_present(self, all_agent_files):
        """Every agent should have a Constraints section."""
        for agent_file in all_agent_files:
            content = agent_file.read_text()
            assert "## Constraints" in content, \
                f"{agent_file.name}: Missing '## Constraints' section"
    
    def test_iteration_limits_documented(self, all_agent_files):
        """Agents should document iteration limits."""
        for agent_file in all_agent_files:
            content = agent_file.read_text()
            has_limit = (
                "Iteration Limit" in content or
                "iteration" in content.lower() or
                "rounds" in content.lower() or
                "attempts" in content.lower()
            )
            # Warning only, not failure
            if not has_limit:
                pytest.skip(f"{agent_file.name}: Consider adding iteration limits")
```

---

## Part 3: API and Workflow Improvements

### 3.1 API Versioning

**Current State:** The REST API has no versioning scheme.

**Endpoints:**
```
GET  /api/events
GET  /api/sessions
GET  /api/stats
POST /events
```

**Problem:** API changes break existing integrations. No deprecation path.

**Recommendation:** Add version prefix to all endpoints.

```python
# web_server.py - route registration
def setup_routes(self):
    # Version 1 API (current)
    self.app.router.add_get("/api/v1/events", self.handle_events_get)
    self.app.router.add_get("/api/v1/sessions", self.handle_sessions)
    self.app.router.add_get("/api/v1/stats", self.handle_stats)
    self.app.router.add_post("/api/v1/events", self.handle_events_post)
    
    # Backward compatibility aliases (deprecated)
    self.app.router.add_get("/api/events", self.handle_events_get)
    self.app.router.add_get("/api/sessions", self.handle_sessions)
    
    # Health check (unversioned by convention)
    self.app.router.add_get("/api/health", self.handle_health)
    self.app.router.add_get("/health", self.handle_health)

# Add deprecation headers
async def handle_events_get(self, request):
    response = await self._get_events(request)
    if "/api/v1/" not in str(request.url):
        response.headers["Deprecation"] = "true"
        response.headers["Sunset"] = "2025-06-01"
        response.headers["Link"] = "</api/v1/events>; rel=\"successor-version\""
    return response
```

---

### 3.2 Rate Limiting

**Current State:** No rate limiting on any endpoint.

**Problem:** A misbehaving hook or client can overwhelm the dashboard with events.

**Recommendation:** Add basic rate limiting.

```python
# src/rate_limiter.py
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict
from collections import defaultdict

@dataclass
class RateLimiter:
    """Simple in-memory rate limiter."""
    
    max_requests: int = 100
    window_seconds: int = 60
    _requests: Dict[str, list] = field(default_factory=lambda: defaultdict(list))
    
    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed for key."""
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.window_seconds)
        
        # Clean old requests
        self._requests[key] = [
            ts for ts in self._requests[key] 
            if ts > cutoff
        ]
        
        if len(self._requests[key]) >= self.max_requests:
            return False
        
        self._requests[key].append(now)
        return True
    
    def remaining(self, key: str) -> int:
        """Get remaining requests for key."""
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.window_seconds)
        active = [ts for ts in self._requests[key] if ts > cutoff]
        return max(0, self.max_requests - len(active))

# Usage in web_server.py
rate_limiter = RateLimiter(max_requests=100, window_seconds=60)

async def handle_events_post(self, request):
    client_ip = request.remote
    
    if not rate_limiter.is_allowed(client_ip):
        return web.json_response(
            {"error": "Rate limit exceeded"},
            status=429,
            headers={
                "Retry-After": "60",
                "X-RateLimit-Remaining": "0",
            }
        )
    
    # Process event...
    response = await self._process_event(request)
    response.headers["X-RateLimit-Remaining"] = str(rate_limiter.remaining(client_ip))
    return response
```

---

### 3.3 Graceful Shutdown

**Current State:** Server stops immediately on signal, potentially losing in-flight events.

**Problem:** Events posted during shutdown may be lost. WebSocket connections drop abruptly.

**Recommendation:** Implement graceful shutdown with drain timeout.

```python
# web_server.py additions
import signal

class AgentDashboard:
    def __init__(self, ...):
        self._shutdown_event = asyncio.Event()
        self._active_requests = 0
        self._drain_timeout = 30  # seconds
    
    async def shutdown_handler(self):
        """Handle graceful shutdown."""
        print("Shutdown signal received, draining connections...")
        self._shutdown_event.set()
        
        # Wait for active requests to complete
        start = time.time()
        while self._active_requests > 0:
            if time.time() - start > self._drain_timeout:
                print(f"Timeout waiting for {self._active_requests} requests")
                break
            await asyncio.sleep(0.1)
        
        # Close WebSocket connections gracefully
        for ws in list(self.websockets):
            await ws.close(code=1001, message="Server shutting down")
        
        print("Shutdown complete")
    
    async def middleware(self, request, handler):
        """Track active requests for graceful shutdown."""
        if self._shutdown_event.is_set():
            return web.json_response(
                {"error": "Server shutting down"},
                status=503
            )
        
        self._active_requests += 1
        try:
            return await handler(request)
        finally:
            self._active_requests -= 1

    async def run(self):
        # Register signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda: asyncio.create_task(self.shutdown_handler())
            )
        
        # Start server with middleware
        self.app.middlewares.append(self.middleware)
        # ...existing run code...
```

---

## Part 4: Developer Experience

### 4.1 Development Mode

**Current State:** No distinction between development and production modes.

**Problem:** Developers must manually configure debug settings. Hot reload requires manual server restart.

**Recommendation:** Add development mode with auto-reload.

```python
# src/dev_server.py
import os
from watchfiles import awatch

async def run_dev_server(dashboard_class, port=4200):
    """Run server with auto-reload on file changes."""
    
    async def restart_on_change():
        async for changes in awatch("./src", "./agents"):
            print(f"Changes detected: {changes}")
            # Trigger restart logic
            
    dashboard = dashboard_class(db_path=":memory:")  # In-memory DB for dev
    dashboard.debug = True
    
    # Run both server and watcher
    await asyncio.gather(
        dashboard.run(),
        restart_on_change(),
    )

# CLI integration
# agent-dashboard --dev
if args.dev:
    os.environ["AGENT_DASHBOARD_DEBUG"] = "1"
    asyncio.run(run_dev_server(AgentDashboard, args.port))
```

---

### 4.2 Debug Endpoints

**Current State:** Limited debugging capability in production.

**Recommendation:** Add debug endpoints (protected in production).

```python
# Debug endpoints - only available when AGENT_DASHBOARD_DEBUG=1
if os.environ.get("AGENT_DASHBOARD_DEBUG"):
    async def handle_debug_state(self, request):
        """Dump internal state for debugging."""
        return web.json_response({
            "sessions": len(self.sessions),
            "events_in_memory": len(self.events),
            "websocket_connections": len(self.websockets),
            "rate_limiter_keys": len(rate_limiter._requests),
            "db_path": str(self.db_path),
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
        })
    
    async def handle_debug_config(self, request):
        """Show active configuration."""
        return web.json_response({
            "port": self.port,
            "db_path": str(self.db_path),
            "compression_budgets": self.compression_gate.budgets,
            "panel_thresholds": self.panel_selector.thresholds,
        })
    
    self.app.router.add_get("/debug/state", self.handle_debug_state)
    self.app.router.add_get("/debug/config", self.handle_debug_config)
```

---

## Part 5: Workflow Improvements

### 5.1 Workflow State Visualization

**Current State:** Workflows are created but state is only visible through CLI or API calls.

**Recommendation:** Add workflow visualization endpoint.

```python
async def handle_workflow_visualization(self, request):
    """Return workflow state as Mermaid diagram."""
    workflow_id = request.match_info.get("workflow_id")
    workflow = self.workflows.get(workflow_id)
    
    if not workflow:
        return web.json_response({"error": "Workflow not found"}, status=404)
    
    mermaid = self._generate_mermaid(workflow)
    
    return web.json_response({
        "workflow_id": workflow_id,
        "mermaid": mermaid,
        "tasks": [t.to_dict() for t in workflow.tasks],
    })

def _generate_mermaid(self, workflow) -> str:
    """Generate Mermaid flowchart for workflow."""
    lines = ["flowchart TD"]
    
    for task in workflow.tasks:
        status_class = {
            "completed": ":::completed",
            "in_progress": ":::active",
            "failed": ":::failed",
            "pending": "",
        }.get(task.status.value, "")
        
        lines.append(f"    {task.id}[{task.content}]{status_class}")
        
        for dep in task.dependencies:
            lines.append(f"    {dep} --> {task.id}")
    
    lines.extend([
        "",
        "    classDef completed fill:#90EE90",
        "    classDef active fill:#FFD700",
        "    classDef failed fill:#FF6B6B",
    ])
    
    return "\n".join(lines)
```

---

### 5.2 Workflow Templates

**Current State:** Users must construct workflows programmatically or through detailed prompts.

**Recommendation:** Add pre-built workflow templates.

```yaml
# templates/research_workflow.yaml
name: Multi-Source Research
description: Parallel research with synthesis and review
version: 1.0.0

phases:
  - name: research
    parallel: true
    tasks:
      - agent: researcher
        description: "Search documentation and official sources"
      - agent: web-search-researcher
        description: "Search web for recent information"
      - agent: perplexity-researcher
        description: "Get AI-synthesized answers"
  
  - name: synthesis
    tasks:
      - agent: synthesis
        input_from: research
        description: "Combine findings into unified report"
  
  - name: review
    optional: true
    tasks:
      - agent: critic
        input_from: synthesis
        description: "Challenge conclusions and find weaknesses"

parameters:
  query:
    type: string
    required: true
  depth:
    type: enum
    values: [quick, standard, deep]
    default: standard

budget:
  max_cost: 2.00
  warning_at: 1.50
```

```python
# src/workflow_templates.py
from pathlib import Path
import yaml

class WorkflowTemplateLoader:
    """Load and instantiate workflow templates."""
    
    def __init__(self, templates_dir: Path = None):
        self.templates_dir = templates_dir or Path(__file__).parent.parent / "templates"
    
    def list_templates(self) -> list:
        """List available templates."""
        templates = []
        for f in self.templates_dir.glob("*.yaml"):
            with open(f) as fh:
                data = yaml.safe_load(fh)
                templates.append({
                    "name": data["name"],
                    "description": data["description"],
                    "file": f.name,
                })
        return templates
    
    def instantiate(self, template_name: str, parameters: dict) -> "Workflow":
        """Create workflow from template with parameters."""
        template_file = self.templates_dir / f"{template_name}.yaml"
        with open(template_file) as f:
            template = yaml.safe_load(f)
        
        # Validate required parameters
        for param_name, param_spec in template.get("parameters", {}).items():
            if param_spec.get("required") and param_name not in parameters:
                raise ValueError(f"Missing required parameter: {param_name}")
        
        # Build workflow from template
        return self._build_workflow(template, parameters)
```

---

## Part 6: Updated Priority Matrix

Incorporating all findings from both analyses:

| Priority | Improvement | Category | Effort | Impact |
|----------|-------------|----------|--------|--------|
| **P0** | Fix version inconsistencies | Consistency | Low | High |
| **P0** | Add agent schema validation tests | Testing | Medium | High |
| **P1** | Configuration management system | Architecture | Medium | High |
| **P1** | Add cli.py and web_server.py tests | Testing | Medium | High |
| **P1** | Error recovery/diagnostics (doctor) | UX | Medium | High |
| **P2** | Standardize logging (remove print) | Consistency | Low | Medium |
| **P2** | API versioning | API | Medium | Medium |
| **P2** | Health check endpoints | Operations | Low | Medium |
| **P2** | Consolidate token counter | Code Quality | Low | Low |
| **P3** | Rate limiting | API | Medium | Medium |
| **P3** | Graceful shutdown | Operations | Medium | Medium |
| **P3** | Development mode | DX | Medium | Medium |
| **P4** | Workflow templates | Features | Medium | Low |
| **P4** | Workflow visualization | Features | Low | Low |
| **P4** | Plugin architecture | Extensibility | High | Medium |

---

## Immediate Action Items

Based on severity and effort, the following should be addressed first:

### This Week
1. **Fix version numbers** across all source files (30 min)
2. **Add agent schema validation tests** (2 hours)
3. **Create single-source version management** (1 hour)

### This Sprint
4. **Add cli.py tests** for critical paths (4 hours)
5. **Add web_server.py tests** for API endpoints (4 hours)
6. **Implement configuration management** (8 hours)
7. **Standardize logging** in cli.py (2 hours)

### Next Sprint
8. **Add API versioning** with deprecation headers
9. **Implement rate limiting**
10. **Add health check endpoints**

---

## Conclusion

This supplement identifies seven additional improvement areas that complement the initial structural analysis. The most critical findings are version inconsistencies and missing test coverage for user-facing modules. These can be addressed quickly and will significantly improve maintainability and reliability.

The combination of the original analysis and this supplement provides a comprehensive roadmap for evolving the agent-dashboard from a functional prototype to a production-grade system.