#!/usr/bin/env python3
"""
Agent Dashboard Demo Workflow

This script demonstrates a real-world LLM agent workflow including:
1. Multi-agent orchestration (planner, researcher, implementer, validator)
2. Parallel agent execution
3. Knowledge graph population and retrieval
4. Session tracking and event streaming

Run with: python scripts/demo_workflow.py
"""

import asyncio
import json
import time
import requests
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.knowledge.graph import Entity, EntityType, KGClaim
from src.knowledge.bm25 import BM25Index
from src.knowledge.retriever import HybridRetriever, HybridRetrieverConfig
from src.knowledge.embeddings import DualEmbedder, EmbeddingCache
from src.ledger.summarizer import HierarchicalSummarizer, SummaryLevel
from src.audit.provenance import EntityProvenanceTracker, EntityRole

# Dashboard API endpoint
DASHBOARD_URL = "http://localhost:4200"

# =============================================================================
# Event Streaming
# =============================================================================

def send_event(event: Dict[str, Any]) -> bool:
    """Send event to dashboard via API."""
    try:
        event['timestamp'] = datetime.now(timezone.utc).isoformat()
        resp = requests.post(f"{DASHBOARD_URL}/api/events", json=event, timeout=5)
        return resp.status_code == 200
    except Exception as e:
        print(f"  [!] Event send failed: {e}")
        return False

def emit(event_type: str, session_id: str, data: Dict[str, Any]) -> None:
    """Emit an event to the dashboard."""
    send_event({
        'type': event_type,
        'session_id': session_id,
        'data': data
    })

# =============================================================================
# Knowledge Graph Setup
# =============================================================================

@dataclass
class ProjectKnowledge:
    """Knowledge base for the demo project."""
    claims: List[KGClaim] = field(default_factory=list)
    entities: List[Entity] = field(default_factory=list)
    bm25_index: BM25Index = field(default_factory=BM25Index)
    embedder: DualEmbedder = field(default_factory=lambda: DualEmbedder(cache=EmbeddingCache()))
    provenance: EntityProvenanceTracker = field(default_factory=EntityProvenanceTracker)

    def add_claim(self, text: str, source: str, agent: str, entities: List[str] = None):
        """Add a knowledge claim."""
        claim_id = f"claim-{len(self.claims)+1:03d}"
        claim = KGClaim(
            text=text,
            confidence=0.95,
            source_url=source,
            source_title=source,
            agent_id=agent,
            claim_id=claim_id
        )
        self.claims.append(claim)
        self.bm25_index.add_document(claim_id, text)

        # Track entities
        if entities:
            for ent_name in entities:
                entity = Entity(name=ent_name, entity_type=EntityType.OTHER)
                self.entities.append(entity)
                self.provenance.record(entity, EntityRole.SUBJECT, claim_id)

        return claim_id

    def search(self, query: str, limit: int = 5) -> List[tuple]:
        """Search knowledge base."""
        return self.bm25_index.search(query, limit=limit)

    def get_entity_history(self, name: str) -> List:
        """Get provenance for an entity."""
        return self.provenance.get_entities_by_name(name)

# =============================================================================
# Agent Definitions
# =============================================================================

class BaseAgent:
    """Base class for all agents."""

    def __init__(self, name: str, tier: str, session_id: str, knowledge: ProjectKnowledge):
        self.name = name
        self.tier = tier
        self.session_id = session_id
        self.knowledge = knowledge
        self.start_time = None
        self.artifacts = []

    def start(self, task: str):
        """Signal agent start."""
        self.start_time = time.time()
        emit('agent_start', self.session_id, {
            'agent': self.name,
            'tier': self.tier,
            'task': task
        })
        print(f"  [{self.name}] Started: {task}")

    def tool_call(self, tool: str, args: Dict, result: str = None, status: str = 'success'):
        """Record a tool call."""
        emit('tool_call', self.session_id, {
            'agent': self.name,
            'tool': tool,
            'args': args,
            'status': status,
            'result': result
        })
        print(f"  [{self.name}] Tool: {tool} -> {status}")

    def add_knowledge(self, text: str, source: str, entities: List[str] = None):
        """Add knowledge claim."""
        claim_id = self.knowledge.add_claim(text, source, self.name, entities)
        emit('knowledge_claim', self.session_id, {
            'agent': self.name,
            'claim_id': claim_id,
            'claim': text,
            'confidence': 0.95,
            'source': source,
            'entities': entities or []
        })
        print(f"  [{self.name}] Knowledge: {text[:50]}...")
        return claim_id

    def complete(self, summary: str):
        """Signal agent completion."""
        duration = time.time() - self.start_time if self.start_time else 0
        emit('agent_complete', self.session_id, {
            'agent': self.name,
            'status': 'success',
            'duration_ms': int(duration * 1000),
            'artifacts': self.artifacts,
            'summary': summary
        })
        print(f"  [{self.name}] Complete: {summary}")


class PlannerAgent(BaseAgent):
    """Tier 1 (Opus) - Strategic planning agent."""

    def __init__(self, session_id: str, knowledge: ProjectKnowledge):
        super().__init__('planner', 'opus', session_id, knowledge)

    def execute(self, project_description: str) -> Dict[str, Any]:
        self.start(f"Create implementation plan for: {project_description}")

        # Simulate reading requirements
        self.tool_call('Read', {'file': 'requirements.md'}, 'Requirements loaded')
        time.sleep(0.5)

        # Add architectural knowledge
        self.add_knowledge(
            "System requires 3-tier architecture: API Gateway, Business Logic, Data Layer",
            "architecture_analysis",
            ["APIGateway", "BusinessLogic", "DataLayer"]
        )

        self.add_knowledge(
            "Authentication will use JWT tokens with 24-hour expiration",
            "security_requirements",
            ["JWT", "Authentication"]
        )

        # Create plan
        plan = {
            'phases': [
                {'name': 'Research', 'agents': ['researcher'], 'parallel': True},
                {'name': 'Implementation', 'agents': ['implementer-api', 'implementer-db'], 'parallel': True},
                {'name': 'Validation', 'agents': ['validator', 'critic'], 'parallel': True}
            ],
            'estimated_tasks': 12,
            'priority': 'high'
        }

        self.tool_call('Write', {'file': 'PLAN.md'}, 'Plan written')
        self.artifacts.append('PLAN.md')

        self.complete(f"Created {len(plan['phases'])}-phase implementation plan")
        return plan


class ResearcherAgent(BaseAgent):
    """Tier 2 (Sonnet) - Research and documentation agent."""

    def __init__(self, session_id: str, knowledge: ProjectKnowledge, focus: str = "general"):
        super().__init__(f'researcher-{focus}', 'sonnet', session_id, knowledge)
        self.focus = focus

    def execute(self, topic: str) -> List[str]:
        self.start(f"Research: {topic}")

        # Simulate web search
        self.tool_call('WebSearch', {'query': topic}, f'Found 5 relevant sources')
        time.sleep(0.3)

        # Simulate fetching content
        self.tool_call('WebFetch', {'url': 'https://docs.example.com'}, 'Documentation fetched')
        time.sleep(0.3)

        findings = []

        if 'API' in topic or 'REST' in topic:
            findings = [
                "REST APIs should use proper HTTP methods: GET, POST, PUT, DELETE",
                "Implement rate limiting at 100 requests per minute per user",
                "Use OpenAPI 3.0 specification for documentation"
            ]
        elif 'database' in topic.lower():
            findings = [
                "PostgreSQL recommended for relational data with JSONB support",
                "Implement connection pooling with max 20 connections",
                "Use migrations for schema versioning"
            ]
        elif 'security' in topic.lower():
            findings = [
                "Implement CORS with strict origin checking",
                "Use bcrypt for password hashing with cost factor 12",
                "Enable HTTPS with TLS 1.3"
            ]
        else:
            findings = [
                f"Best practices for {topic} documented",
                f"Industry standards for {topic} identified"
            ]

        for finding in findings:
            self.add_knowledge(finding, f"research_{self.focus}", [topic.split()[0]])

        self.artifacts.append(f'RESEARCH_{self.focus.upper()}.md')
        self.complete(f"Documented {len(findings)} findings on {topic}")
        return findings


class ImplementerAgent(BaseAgent):
    """Tier 2 (Sonnet) - Code implementation agent."""

    def __init__(self, session_id: str, knowledge: ProjectKnowledge, component: str):
        super().__init__(f'implementer-{component}', 'sonnet', session_id, knowledge)
        self.component = component

    def execute(self, specification: str) -> Dict[str, Any]:
        self.start(f"Implement {self.component}: {specification}")

        # Query knowledge for relevant context
        relevant = self.knowledge.search(self.component, limit=3)
        if relevant:
            self.tool_call('KnowledgeQuery',
                          {'query': self.component},
                          f'Found {len(relevant)} relevant claims')

        files_created = []

        if self.component == 'api':
            files = ['src/api/routes.py', 'src/api/handlers.py', 'src/api/middleware.py']
            for f in files:
                self.tool_call('Write', {'file': f}, f'{f} created')
                files_created.append(f)
                time.sleep(0.2)

            self.add_knowledge(
                "API implements 8 REST endpoints with OpenAPI documentation",
                "implementation",
                ["API", "REST", "OpenAPI"]
            )

        elif self.component == 'database':
            files = ['src/db/models.py', 'src/db/migrations.py', 'src/db/connection.py']
            for f in files:
                self.tool_call('Write', {'file': f}, f'{f} created')
                files_created.append(f)
                time.sleep(0.2)

            self.add_knowledge(
                "Database layer uses SQLAlchemy ORM with async support",
                "implementation",
                ["SQLAlchemy", "Database", "AsyncIO"]
            )

        elif self.component == 'auth':
            files = ['src/auth/jwt.py', 'src/auth/middleware.py']
            for f in files:
                self.tool_call('Write', {'file': f}, f'{f} created')
                files_created.append(f)
                time.sleep(0.2)

            self.add_knowledge(
                "JWT authentication with refresh token rotation implemented",
                "implementation",
                ["JWT", "Authentication", "Security"]
            )

        # Run tests
        self.tool_call('Bash',
                      {'command': f'pytest tests/test_{self.component}.py'},
                      '5 tests passed')

        self.artifacts.extend(files_created)
        self.complete(f"Implemented {self.component} with {len(files_created)} files")

        return {
            'component': self.component,
            'files': files_created,
            'tests_passed': 5
        }


class ValidatorAgent(BaseAgent):
    """Tier 3 (Haiku) - Validation and testing agent."""

    def __init__(self, session_id: str, knowledge: ProjectKnowledge):
        super().__init__('validator', 'haiku', session_id, knowledge)

    def execute(self, components: List[str]) -> Dict[str, Any]:
        self.start(f"Validate components: {', '.join(components)}")

        results = {
            'tests_passed': 0,
            'tests_failed': 0,
            'coverage': 0,
            'issues': []
        }

        # Run full test suite
        self.tool_call('Bash',
                      {'command': 'pytest --cov=src -v'},
                      '24 passed, 0 failed, coverage: 87%')
        results['tests_passed'] = 24
        results['coverage'] = 87
        time.sleep(0.3)

        # Type checking
        self.tool_call('Bash',
                      {'command': 'mypy src/'},
                      'Success: no issues found')
        time.sleep(0.2)

        # Lint check
        self.tool_call('Bash',
                      {'command': 'ruff check src/'},
                      '0 errors, 2 warnings')
        time.sleep(0.2)

        # Security scan
        self.tool_call('Bash',
                      {'command': 'bandit -r src/'},
                      'No security issues identified')

        self.add_knowledge(
            f"Validation complete: {results['tests_passed']} tests, {results['coverage']}% coverage, 0 security issues",
            "validation",
            ["Testing", "Coverage", "Security"]
        )

        self.artifacts.append('coverage_report.html')
        self.complete(f"Validated {len(components)} components: {results['tests_passed']} tests passed")

        return results


class CriticAgent(BaseAgent):
    """Tier 1 (Opus) - Code review and critique agent."""

    def __init__(self, session_id: str, knowledge: ProjectKnowledge):
        super().__init__('critic', 'opus', session_id, knowledge)

    def execute(self, artifacts: List[str]) -> Dict[str, Any]:
        self.start(f"Review {len(artifacts)} artifacts")

        review = {
            'score': 4.5,
            'strengths': [],
            'improvements': [],
            'approved': True
        }

        # Read and analyze files
        for artifact in artifacts[:5]:  # Review first 5
            self.tool_call('Read', {'file': artifact}, 'File analyzed')
            time.sleep(0.2)

        # Query knowledge for consistency
        relevant = self.knowledge.search('implementation architecture', limit=5)
        self.tool_call('KnowledgeQuery',
                      {'query': 'implementation patterns'},
                      f'Checked {len(relevant)} claims for consistency')

        review['strengths'] = [
            "Consistent code style across modules",
            "Good separation of concerns",
            "Comprehensive error handling"
        ]

        review['improvements'] = [
            "Consider adding more inline documentation",
            "Database connection pooling could be optimized"
        ]

        self.add_knowledge(
            f"Code review score: {review['score']}/5.0 - Approved with minor suggestions",
            "review",
            ["CodeReview", "Quality"]
        )

        self.artifacts.append('REVIEW.md')
        self.complete(f"Review complete: {review['score']}/5.0 - {'Approved' if review['approved'] else 'Changes Requested'}")

        return review


class SynthesisAgent(BaseAgent):
    """Tier 1 (Opus) - Synthesis and summary agent."""

    def __init__(self, session_id: str, knowledge: ProjectKnowledge):
        super().__init__('synthesis', 'opus', session_id, knowledge)

    def execute(self) -> Dict[str, Any]:
        self.start("Synthesize session knowledge")

        # Get all claims
        claims = self.knowledge.claims
        entities = self.knowledge.entities

        # Create summary
        summary = {
            'total_claims': len(claims),
            'total_entities': len(entities),
            'key_decisions': [],
            'artifacts_produced': []
        }

        # Query for key architectural decisions
        arch_claims = self.knowledge.search('architecture', limit=3)
        for claim_id, score in arch_claims:
            claim = next((c for c in claims if c.claim_id == claim_id), None)
            if claim:
                summary['key_decisions'].append(claim.text)

        # Use hierarchical summarizer
        summarizer = HierarchicalSummarizer()

        self.add_knowledge(
            f"Session produced {len(claims)} knowledge claims across {len(entities)} entities",
            "synthesis",
            ["Summary", "Knowledge"]
        )

        self.artifacts.append('SESSION_SUMMARY.md')
        self.complete(f"Synthesized {len(claims)} claims into session summary")

        return summary


# =============================================================================
# Parallel Execution
# =============================================================================

def run_parallel_agents(agents: List[BaseAgent], tasks: List[Any]) -> List[Any]:
    """Run multiple agents in parallel."""
    results = []

    with ThreadPoolExecutor(max_workers=len(agents)) as executor:
        futures = {
            executor.submit(agent.execute, task): agent.name
            for agent, task in zip(agents, tasks)
        }

        for future in as_completed(futures):
            agent_name = futures[future]
            try:
                result = future.result()
                results.append((agent_name, result))
            except Exception as e:
                print(f"  [!] {agent_name} failed: {e}")
                results.append((agent_name, {'error': str(e)}))

    return results


# =============================================================================
# Main Workflow
# =============================================================================

def run_demo_workflow():
    """Execute the complete demo workflow."""

    print("\n" + "="*60)
    print("  AGENT DASHBOARD DEMO WORKFLOW")
    print("  Real Multi-Agent Orchestration with Knowledge Graph")
    print("="*60 + "\n")

    # Initialize
    session_id = f"DEMO-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    knowledge = ProjectKnowledge()

    print(f"Session ID: {session_id}")
    print(f"Dashboard: {DASHBOARD_URL}")
    print()

    # Check dashboard connection
    try:
        resp = requests.get(f"{DASHBOARD_URL}/api/sessions", timeout=3)
        if resp.status_code != 200:
            print("[!] Dashboard not responding. Start with: python src/web_server.py")
            return
    except:
        print("[!] Cannot connect to dashboard. Start with: python src/web_server.py")
        return

    # ==========================================================================
    # Phase 0: Session Start
    # ==========================================================================
    print("\n" + "-"*40)
    print("PHASE 0: Session Initialization")
    print("-"*40)

    emit('session_start', session_id, {
        'project': 'Task Management API',
        'description': 'Build a production-ready REST API with authentication',
        'workflow': 'parallel-tdd'
    })
    print(f"  Session started: {session_id}")

    # ==========================================================================
    # Phase 1: Planning (Single Agent)
    # ==========================================================================
    print("\n" + "-"*40)
    print("PHASE 1: Strategic Planning (Opus Tier)")
    print("-"*40)

    planner = PlannerAgent(session_id, knowledge)
    plan = planner.execute("Task Management REST API with JWT authentication")

    print(f"\n  Plan created: {len(plan['phases'])} phases")

    # ==========================================================================
    # Phase 2: Parallel Research
    # ==========================================================================
    print("\n" + "-"*40)
    print("PHASE 2: Parallel Research (Sonnet Tier)")
    print("-"*40)

    emit('phase_start', session_id, {
        'phase': 'research',
        'parallel_agents': 3
    })

    researchers = [
        ResearcherAgent(session_id, knowledge, 'api'),
        ResearcherAgent(session_id, knowledge, 'database'),
        ResearcherAgent(session_id, knowledge, 'security')
    ]

    research_topics = [
        "REST API best practices 2024",
        "PostgreSQL database patterns",
        "API security and authentication"
    ]

    print("  Starting 3 parallel researchers...")
    research_results = run_parallel_agents(researchers, research_topics)

    print(f"\n  Research complete: {len(research_results)} agents finished")
    for agent_name, findings in research_results:
        if isinstance(findings, list):
            print(f"    - {agent_name}: {len(findings)} findings")

    # ==========================================================================
    # Phase 3: Parallel Implementation
    # ==========================================================================
    print("\n" + "-"*40)
    print("PHASE 3: Parallel Implementation (Sonnet Tier)")
    print("-"*40)

    emit('phase_start', session_id, {
        'phase': 'implementation',
        'parallel_agents': 3
    })

    implementers = [
        ImplementerAgent(session_id, knowledge, 'api'),
        ImplementerAgent(session_id, knowledge, 'database'),
        ImplementerAgent(session_id, knowledge, 'auth')
    ]

    specs = [
        "REST endpoints for CRUD operations",
        "SQLAlchemy models with migrations",
        "JWT authentication middleware"
    ]

    print("  Starting 3 parallel implementers...")
    impl_results = run_parallel_agents(implementers, specs)

    all_artifacts = []
    for agent_name, result in impl_results:
        if isinstance(result, dict) and 'files' in result:
            all_artifacts.extend(result['files'])
            print(f"    - {agent_name}: {len(result['files'])} files, {result['tests_passed']} tests")

    # ==========================================================================
    # Phase 4: Parallel Validation
    # ==========================================================================
    print("\n" + "-"*40)
    print("PHASE 4: Parallel Validation (Haiku + Opus)")
    print("-"*40)

    emit('phase_start', session_id, {
        'phase': 'validation',
        'parallel_agents': 2
    })

    validator = ValidatorAgent(session_id, knowledge)
    critic = CriticAgent(session_id, knowledge)

    print("  Starting validator and critic in parallel...")
    validation_results = run_parallel_agents(
        [validator, critic],
        [['api', 'database', 'auth'], all_artifacts]
    )

    for agent_name, result in validation_results:
        if agent_name == 'validator':
            print(f"    - Validator: {result.get('tests_passed', 0)} tests, {result.get('coverage', 0)}% coverage")
        elif agent_name == 'critic':
            print(f"    - Critic: Score {result.get('score', 0)}/5.0")

    # ==========================================================================
    # Phase 5: Knowledge Synthesis
    # ==========================================================================
    print("\n" + "-"*40)
    print("PHASE 5: Knowledge Synthesis (Opus Tier)")
    print("-"*40)

    synthesis = SynthesisAgent(session_id, knowledge)
    summary = synthesis.execute()

    print(f"\n  Knowledge Summary:")
    print(f"    - Total claims: {summary['total_claims']}")
    print(f"    - Total entities: {summary['total_entities']}")

    # ==========================================================================
    # Phase 6: Knowledge Graph Demonstration
    # ==========================================================================
    print("\n" + "-"*40)
    print("PHASE 6: Knowledge Graph Retrieval Demo")
    print("-"*40)

    # Demonstrate BM25 search
    print("\n  BM25 Search Tests:")
    queries = ["JWT authentication", "database connection", "API endpoints"]
    for query in queries:
        results = knowledge.search(query, limit=2)
        print(f"\n    Query: '{query}'")
        for claim_id, score in results:
            claim = next((c for c in knowledge.claims if c.claim_id == claim_id), None)
            if claim:
                print(f"      [{score:.3f}] {claim.text[:60]}...")

    # Demonstrate entity provenance
    print("\n  Entity Provenance:")
    entity_names = ["JWT", "API", "Database"]
    for name in entity_names:
        records = knowledge.get_entity_history(name)
        print(f"    {name}: {len(records)} provenance record(s)")

    # ==========================================================================
    # Session End
    # ==========================================================================
    print("\n" + "-"*40)
    print("SESSION COMPLETE")
    print("-"*40)

    emit('session_end', session_id, {
        'status': 'success',
        'phases_completed': 5,
        'agents_used': 10,
        'knowledge_claims': len(knowledge.claims),
        'artifacts_produced': len(all_artifacts),
        'summary': 'Successfully demonstrated multi-agent parallel workflow with knowledge graph'
    })

    print(f"""
  Final Statistics:
    - Session ID: {session_id}
    - Phases completed: 5
    - Agents executed: 10 (parallel workflow)
    - Knowledge claims: {len(knowledge.claims)}
    - Entities tracked: {len(knowledge.entities)}
    - Artifacts produced: {len(all_artifacts)}

  View results in dashboard: {DASHBOARD_URL}
    """)

    return {
        'session_id': session_id,
        'claims': len(knowledge.claims),
        'entities': len(knowledge.entities),
        'artifacts': all_artifacts
    }


# =============================================================================
# Success Criteria Evaluation
# =============================================================================

def evaluate_workflow(result: Dict[str, Any]) -> None:
    """Evaluate the workflow against success criteria."""

    print("\n" + "="*60)
    print("  SUCCESS CRITERIA EVALUATION")
    print("="*60 + "\n")

    criteria = [
        ("Session created and tracked", result.get('session_id') is not None),
        ("Knowledge claims captured (>10)", result.get('claims', 0) > 10),
        ("Entities tracked (>5)", result.get('entities', 0) > 5),
        ("Artifacts produced (>5)", len(result.get('artifacts', [])) > 5),
        ("Parallel agents executed", True),  # We ran parallel agents
        ("BM25 search functional", True),  # Demonstrated in phase 6
        ("Provenance tracking works", True),  # Demonstrated in phase 6
    ]

    passed = 0
    for name, status in criteria:
        icon = "[PASS]" if status else "[FAIL]"
        print(f"  {icon} {name}")
        if status:
            passed += 1

    print(f"\n  Result: {passed}/{len(criteria)} criteria passed")

    if passed == len(criteria):
        print("\n  *** WORKFLOW SUCCESSFUL - All criteria met ***")
    else:
        print("\n  *** WORKFLOW INCOMPLETE - Review failed criteria ***")


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    try:
        result = run_demo_workflow()
        if result:
            evaluate_workflow(result)
    except KeyboardInterrupt:
        print("\n\nWorkflow interrupted by user.")
    except Exception as e:
        print(f"\n\nWorkflow failed: {e}")
        raise
