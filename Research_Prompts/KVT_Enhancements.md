# Claude Code Implementation Guide: KVT Enhancements

## Actionable Implementation Plan for Agent Dashboard

**Document Type:** Executable Implementation Guide  
**Target System:** Agent Dashboard v2.5.2  
**Methodology:** TDD (Test-Driven Development)  
**Total Effort:** 80-100 hours across 4 enhancements

---

## 🚀 STARTING AGENT: `orchestrator`

**The `orchestrator` agent is the designated entry point for this implementation.**

Per the agent definition:
> "Strategic coordinator for multi-agent research workflows. Use as the PRIMARY entry point for complex research tasks."

### Initial Dispatch Command

Copy and execute this prompt to begin implementation:

```
@orchestrator Execute the KVT Enhancement Implementation Plan for Agent Dashboard.

## Context
We have completed analysis comparing KVT (Key Vector Token) recommendations against the existing codebase. Four enhancements have been identified with detailed specifications ready.

## Enhancements to Implement (Priority Order)

1. **HIER-001: Hierarchical Session Summarizer** (HIGH priority, 16h)
   - Module: src/ledger/summarizer.py (NEW)
   - Enables efficient context loading for long-form workflows

2. **KG-001/002: Temporal Entity Extensions** (MEDIUM priority, 8h)
   - Module: src/knowledge/graph.py (MODIFY)
   - Adds valid_from/valid_to fields and code entity types

3. **RETR-001: Hybrid Vector-Graph Retriever** (HIGH priority, 24h)
   - Module: src/knowledge/retriever.py (NEW)
   - Unified retrieval with automatic strategy selection

4. **AUDIT-001: Entity-Aware Provenance** (MEDIUM priority, 8h)
   - Module: src/audit/query.py (EXTEND)
   - Adds entity-specific provenance queries

## Execution Instructions

1. Start with HIER-001 (highest priority)
2. Follow TDD workflow: SPEC → TEST_DESIGN → TEST_IMPL → IMPLEMENT → VALIDATE → REVIEW
3. Delegate to appropriate agents per phase:
   - SPEC: planner
   - TEST_DESIGN/TEST_IMPL: test-writer
   - IMPLEMENT: implementer
   - VALIDATE: validator
   - REVIEW: critic + panel-coordinator

4. Track progress using Progress Ledger pattern
5. Enforce iteration limits per agent constraints
6. Request human approval at phase transitions  

## Success Criteria
- All tests pass (100% pass rate)
- Zero TODOs in production code
- Zero mocks in production code
- Panel review approval (≥4.0/5.0 mean score)

Begin with HIER-001 SPEC phase. Delegate to planner agent.
```

---

## Agent Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR (Opus)                          │
│              Entry Point & Workflow Coordinator                  │
└─────────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
         ▼                    ▼                    ▼
    ┌─────────┐         ┌──────────┐        ┌──────────┐
    │ PLANNER │         │ CRITIC   │        │ SYNTHESIS│
    │ (Opus)  │         │ (Opus)   │        │ (Opus)   │
    │ SPEC    │         │ Quality  │        │ Combine  │
    └────┬────┘         └────┬─────┘        └──────────┘
         │                   │
         ▼                   │
    ┌───────────┐            │
    │TEST-WRITER│            │
    │ (Haiku)   │            │
    │TEST_DESIGN│            │
    │TEST_IMPL  │            │
    └─────┬─────┘            │
          │                  │
          ▼                  │
    ┌────────────┐           │
    │IMPLEMENTER │           │
    │ (Sonnet)   │◄──────────┘ (critique loop)
    │ IMPLEMENT  │
    └─────┬──────┘
          │
          ▼
    ┌───────────┐
    │ VALIDATOR │
    │ (Haiku)   │
    │ VALIDATE  │
    └─────┬─────┘
          │
          ▼
    ┌─────────────────┐
    │PANEL-COORDINATOR│
    │ (Sonnet)        │
    │ REVIEW          │
    └─────────────────┘
          │
          ▼
      [DELIVER]
```

---

## Enhancement 1: HIER-001 - Hierarchical Session Summarizer

### Phase 1: SPEC (Agent: `planner`)

**Delegation Prompt:**

```
@planner Create a product specification for the Hierarchical Session Summarizer.

## Context
This enhancement adds multi-level session summarization to the ledger module,
enabling efficient context loading when resuming long programming sessions.

## Existing Code to Reference
- src/ledger/runtime_tracker.py (existing runtime metrics)
- src/ledger/task_ledger.py (TaskLedger, ProgressEntry dataclasses)
- src/ledger/operations.py (LedgerManager class)

## Requirements Overview

### Functional Requirements
1. SummaryLevel enum: SESSION(0), PHASE(1), TASK(2), ATOMIC(3)
2. HierarchicalSummary dataclass (immutable/frozen)
3. Phase detection: Group tasks by time proximity (90-min threshold)
4. Task summarization: Extract accomplishments/blockers from progress_history
5. Phase summarization: Aggregate child task summaries
6. Session summarization: Top-level summary of all phases
7. Context loading: Query-aware summary selection within token budget
8. Integration with RuntimeLedgerTracker

### Non-Functional Requirements
- Phase detection: < 100ms for 100 tasks
- Full session summary: < 2 seconds
- Each summary level: < 500 tokens

### Constraints
- NO LLM calls for summarization (rule-based extraction)
- Backward compatible with existing ledger APIs
- Follow existing dataclass patterns from task_ledger.py

## Output
Produce a complete SPEC document following your specification template.
Define WHAT the feature does, not HOW to implement it.
Request panel review for security/core module before TEST_DESIGN.

Research Assessment: NO external research needed.
```

### Phase 2: TEST_DESIGN (Agent: `test-writer`)

**Delegation Prompt:**

```
@test-writer Design tests for the Hierarchical Session Summarizer based on the approved specification.

## Specification Reference
[Insert approved SPEC from planner]

## Test Coverage Requirements

### Unit Tests (Target: 20 tests)
| Requirement | Test Cases |
|-------------|------------|
| FR-001 SummaryLevel | test_summary_level_has_four_values, test_summary_level_ordering |
| FR-002 HierarchicalSummary | test_creation, test_with_children, test_immutability |
| FR-003 Phase Detection | test_groups_close_tasks, test_single_task, test_empty_list, test_boundary |
| FR-004 Task Summarization | test_extracts_accomplishments, test_extracts_blockers, test_empty_progress |
| FR-005 Phase Summarization | test_aggregates_children, test_deduplicates_entities |
| FR-006 Session Summarization | test_complete, test_empty_phases |
| FR-007 Context Loading | test_respects_budget, test_classifies_scope, test_empty_budget_error |
| Error Conditions | test_invalid_time_range |

### Integration Tests (Target: 2 tests)
- test_integration_with_runtime_tracker
- test_full_session_summary_workflow

## Output Format
Produce TEST_DESIGN document with:
1. Coverage matrix linking requirements to tests
2. Test case descriptions with inputs and expected outputs
3. Test file structure recommendation

Do NOT implement tests yet. Design only.
Request approval before TEST_IMPL phase.
```

### Phase 3: TEST_IMPL (Agent: `test-writer`)

**Delegation Prompt:**

```
@test-writer Implement tests for the Hierarchical Session Summarizer.

## Approved Test Design
[Insert approved TEST_DESIGN]

## Implementation Requirements

### File: tests/test_summarizer.py

```python
"""
Unit tests for Hierarchical Summarizer.
Tests are IMMUTABLE after approval.
"""
import pytest
from datetime import datetime, timedelta
from dataclasses import FrozenInstanceError

from src.ledger.summarizer import (
    SummaryLevel,
    HierarchicalSummary,
    HierarchicalSummarizer,
)
from src.ledger.task_ledger import TaskLedger, TaskStatus, TaskPriority, ProgressEntry


# FR-001: Summary Level Enumeration
def test_summary_level_has_four_values():
    """SummaryLevel enum must have exactly 4 levels."""
    assert len(SummaryLevel) == 4
    assert SummaryLevel.SESSION.value == 0
    assert SummaryLevel.PHASE.value == 1
    assert SummaryLevel.TASK.value == 2
    assert SummaryLevel.ATOMIC.value == 3


def test_summary_level_ordering():
    """SESSION < PHASE < TASK < ATOMIC in hierarchy."""
    assert SummaryLevel.SESSION.value < SummaryLevel.PHASE.value
    assert SummaryLevel.PHASE.value < SummaryLevel.TASK.value
    assert SummaryLevel.TASK.value < SummaryLevel.ATOMIC.value


# FR-002: HierarchicalSummary dataclass
def test_hierarchical_summary_creation():
    """HierarchicalSummary can be created with required fields."""
    now = datetime.utcnow()
    summary = HierarchicalSummary(
        level=SummaryLevel.TASK,
        time_range=(now, now + timedelta(hours=1)),
        summary_text="Test summary",
        key_accomplishments=["Done task 1"],
        key_blockers=[],
        entities_affected=["file.py"],
        token_cost=100,
    )
    assert summary.level == SummaryLevel.TASK
    assert summary.summary_text == "Test summary"
    assert len(summary.child_summaries) == 0


def test_hierarchical_summary_with_children():
    """HierarchicalSummary can contain child summaries."""
    now = datetime.utcnow()
    child = HierarchicalSummary(
        level=SummaryLevel.TASK,
        time_range=(now, now + timedelta(minutes=30)),
        summary_text="Child task",
        key_accomplishments=["Sub-task done"],
        key_blockers=[],
        entities_affected=[],
        token_cost=50,
    )
    parent = HierarchicalSummary(
        level=SummaryLevel.PHASE,
        time_range=(now, now + timedelta(hours=1)),
        summary_text="Phase summary",
        key_accomplishments=["Phase complete"],
        key_blockers=[],
        entities_affected=[],
        token_cost=150,
        child_summaries=[child],
    )
    assert len(parent.child_summaries) == 1
    assert parent.child_summaries[0].level == SummaryLevel.TASK


def test_hierarchical_summary_immutability():
    """HierarchicalSummary should be immutable (frozen)."""
    now = datetime.utcnow()
    summary = HierarchicalSummary(
        level=SummaryLevel.TASK,
        time_range=(now, now + timedelta(hours=1)),
        summary_text="Test",
        key_accomplishments=[],
        key_blockers=[],
        entities_affected=[],
        token_cost=10,
    )
    with pytest.raises((FrozenInstanceError, AttributeError)):
        summary.summary_text = "Modified"


# FR-003: Phase Detection
@pytest.fixture
def sample_tasks():
    """Create sample tasks for testing phase detection."""
    base_time = datetime(2025, 1, 1, 9, 0, 0)
    tasks = []
    # Tasks at 0, 30, 60, 180, 210 minutes
    for i, offset_minutes in enumerate([0, 30, 60, 180, 210]):
        task = TaskLedger(
            task_id=f"TASK-{i:03d}",
            phase="test",
            category="test",
            title=f"Task {i}",
            objective="Test objective",
            status=TaskStatus.COMPLETED,
            priority=TaskPriority.MEDIUM,
            created_at=base_time + timedelta(minutes=offset_minutes),
            updated_at=base_time + timedelta(minutes=offset_minutes + 20),
            estimated_effort="1h",
        )
        tasks.append(task)
    return tasks


def test_phase_detection_groups_close_tasks(sample_tasks):
    """Tasks within threshold should be grouped into same phase."""
    summarizer = HierarchicalSummarizer(gap_threshold_minutes=90)
    phases = summarizer.detect_phases(sample_tasks)
    # Tasks at 0, 30, 60 → Phase 1 (gaps < 90 min)
    # Tasks at 180, 210 → Phase 2 (gap from 60 to 180 = 120 min > 90)
    assert len(phases) == 2
    assert len(phases[0]) == 3
    assert len(phases[1]) == 2


def test_phase_detection_single_task():
    """Single task should form single phase."""
    task = TaskLedger(
        task_id="TASK-001", phase="test", category="test",
        title="Single task", objective="Test",
        status=TaskStatus.COMPLETED, priority=TaskPriority.MEDIUM,
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        estimated_effort="1h",
    )
    summarizer = HierarchicalSummarizer()
    phases = summarizer.detect_phases([task])
    assert len(phases) == 1
    assert len(phases[0]) == 1


def test_phase_detection_empty_list():
    """Empty task list should return empty phases."""
    summarizer = HierarchicalSummarizer()
    phases = summarizer.detect_phases([])
    assert len(phases) == 0


def test_phase_detection_boundary_threshold():
    """Tasks exactly at threshold boundary should be same phase."""
    base_time = datetime(2025, 1, 1, 9, 0, 0)
    task1 = TaskLedger(
        task_id="TASK-001", phase="test", category="test",
        title="Task 1", objective="Test",
        status=TaskStatus.COMPLETED, priority=TaskPriority.MEDIUM,
        created_at=base_time, updated_at=base_time,
        estimated_effort="1h",
    )
    task2 = TaskLedger(
        task_id="TASK-002", phase="test", category="test",
        title="Task 2", objective="Test",
        status=TaskStatus.COMPLETED, priority=TaskPriority.MEDIUM,
        created_at=base_time + timedelta(minutes=89),
        updated_at=base_time + timedelta(minutes=89),
        estimated_effort="1h",
    )
    summarizer = HierarchicalSummarizer(gap_threshold_minutes=90)
    phases = summarizer.detect_phases([task1, task2])
    assert len(phases) == 1  # Same phase (89 < 90)


# FR-004: Task Summarization
def test_task_summarization_extracts_accomplishments():
    """Task summary extracts accomplishments from progress history."""
    task = TaskLedger(
        task_id="TASK-001", phase="test", category="test",
        title="Feature implementation", objective="Implement feature X",
        status=TaskStatus.COMPLETED, priority=TaskPriority.HIGH,
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        estimated_effort="2h",
        progress_history=[
            ProgressEntry(
                timestamp=datetime.utcnow(),
                agent_id="implementer",
                action_taken="Created initial implementation",
                outcome="success",
                artifacts_produced=["src/feature.py"],
            ),
            ProgressEntry(
                timestamp=datetime.utcnow(),
                agent_id="implementer",
                action_taken="Added error handling",
                outcome="success",
            ),
        ],
    )
    summarizer = HierarchicalSummarizer()
    summary = summarizer.summarize_task(task)
    assert summary.level == SummaryLevel.TASK
    assert "Created initial implementation" in summary.key_accomplishments
    assert "Added error handling" in summary.key_accomplishments


def test_task_summarization_extracts_blockers():
    """Task summary extracts blockers from progress history."""
    task = TaskLedger(
        task_id="TASK-001", phase="test", category="test",
        title="Feature implementation", objective="Implement feature X",
        status=TaskStatus.BLOCKED, priority=TaskPriority.HIGH,
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        estimated_effort="2h",
        progress_history=[
            ProgressEntry(
                timestamp=datetime.utcnow(),
                agent_id="implementer",
                action_taken="Attempted implementation",
                outcome="blocked",
                blockers_encountered=["Missing dependency: libfoo"],
            ),
        ],
    )
    summarizer = HierarchicalSummarizer()
    summary = summarizer.summarize_task(task)
    assert "Missing dependency: libfoo" in summary.key_blockers


def test_task_summarization_empty_progress():
    """Task with no progress returns summary indicating no activity."""
    task = TaskLedger(
        task_id="TASK-001", phase="test", category="test",
        title="Empty task", objective="Nothing done",
        status=TaskStatus.NOT_STARTED, priority=TaskPriority.LOW,
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        estimated_effort="1h",
        progress_history=[],
    )
    summarizer = HierarchicalSummarizer()
    summary = summarizer.summarize_task(task)
    assert "No activity recorded" in summary.summary_text or len(summary.key_accomplishments) == 0


# FR-005: Phase Summarization
def test_phase_summarization_aggregates_children():
    """Phase summary aggregates accomplishments from child tasks."""
    now = datetime.utcnow()
    task_summaries = [
        HierarchicalSummary(
            level=SummaryLevel.TASK,
            time_range=(now, now + timedelta(minutes=30)),
            summary_text="Task 1",
            key_accomplishments=["Built auth module"],
            key_blockers=[],
            entities_affected=["auth.py"],
            token_cost=50,
        ),
        HierarchicalSummary(
            level=SummaryLevel.TASK,
            time_range=(now + timedelta(minutes=30), now + timedelta(hours=1)),
            summary_text="Task 2",
            key_accomplishments=["Added tests"],
            key_blockers=[],
            entities_affected=["test_auth.py"],
            token_cost=50,
        ),
    ]
    summarizer = HierarchicalSummarizer()
    phase_summary = summarizer.summarize_phase(task_summaries)
    assert phase_summary.level == SummaryLevel.PHASE
    assert len(phase_summary.child_summaries) == 2
    assert "Built auth module" in phase_summary.key_accomplishments
    assert "Added tests" in phase_summary.key_accomplishments


def test_phase_summarization_deduplicates_entities():
    """Phase summary deduplicates affected entities."""
    now = datetime.utcnow()
    task_summaries = [
        HierarchicalSummary(
            level=SummaryLevel.TASK,
            time_range=(now, now + timedelta(minutes=30)),
            summary_text="Task 1",
            key_accomplishments=["Change 1"],
            key_blockers=[],
            entities_affected=["shared.py", "module_a.py"],
            token_cost=50,
        ),
        HierarchicalSummary(
            level=SummaryLevel.TASK,
            time_range=(now + timedelta(minutes=30), now + timedelta(hours=1)),
            summary_text="Task 2",
            key_accomplishments=["Change 2"],
            key_blockers=[],
            entities_affected=["shared.py", "module_b.py"],
            token_cost=50,
        ),
    ]
    summarizer = HierarchicalSummarizer()
    phase_summary = summarizer.summarize_phase(task_summaries)
    assert len(phase_summary.entities_affected) == 3  # Deduplicated


# FR-006: Session Summarization
def test_session_summarization_complete():
    """Session summary includes all phases as children."""
    now = datetime.utcnow()
    phase_summaries = [
        HierarchicalSummary(
            level=SummaryLevel.PHASE,
            time_range=(now, now + timedelta(hours=1)),
            summary_text="Morning work",
            key_accomplishments=["Setup complete"],
            key_blockers=[],
            entities_affected=["config.py"],
            token_cost=100,
        ),
        HierarchicalSummary(
            level=SummaryLevel.PHASE,
            time_range=(now + timedelta(hours=2), now + timedelta(hours=3)),
            summary_text="Afternoon work",
            key_accomplishments=["Feature done"],
            key_blockers=[],
            entities_affected=["feature.py"],
            token_cost=100,
        ),
    ]
    summarizer = HierarchicalSummarizer()
    session_summary = summarizer.summarize_session(phase_summaries)
    assert session_summary.level == SummaryLevel.SESSION
    assert len(session_summary.child_summaries) == 2


def test_session_summarization_empty_phases():
    """Session with no phases returns minimal summary."""
    summarizer = HierarchicalSummarizer()
    session_summary = summarizer.summarize_session([])
    assert session_summary.level == SummaryLevel.SESSION
    assert len(session_summary.child_summaries) == 0


# FR-007: Context Loading
def test_context_loading_respects_budget():
    """Context loading stays within token budget."""
    now = datetime.utcnow()
    summary = HierarchicalSummary(
        level=SummaryLevel.SESSION,
        time_range=(now, now + timedelta(hours=4)),
        summary_text="A" * 1000,
        key_accomplishments=["Done"] * 10,
        key_blockers=[],
        entities_affected=["file.py"] * 10,
        token_cost=500,
    )
    summarizer = HierarchicalSummarizer()
    summarizer._cached_session_summary = summary
    context = summarizer.load_context_for_query("What did we do?", token_budget=100)
    # Rough: 1 token ≈ 4 chars, budget 100 → ~400 chars
    assert len(context) <= 500


def test_context_loading_classifies_query_scope():
    """Context loading uses appropriate level based on query."""
    summarizer = HierarchicalSummarizer()
    broad_scope = summarizer._classify_query_scope("What's the overall status?")
    specific_scope = summarizer._classify_query_scope("Why did test_auth fail?")
    assert broad_scope <= 1  # SESSION or PHASE
    assert specific_scope >= 2  # TASK or ATOMIC


def test_context_loading_empty_budget_raises_error():
    """Zero or negative budget raises ValueError."""
    summarizer = HierarchicalSummarizer()
    with pytest.raises(ValueError):
        summarizer.load_context_for_query("test", token_budget=0)
    with pytest.raises(ValueError):
        summarizer.load_context_for_query("test", token_budget=-1)


# Error Conditions
def test_invalid_time_range_raises_error():
    """Creating summary with end before start raises error."""
    now = datetime.utcnow()
    with pytest.raises(ValueError, match="end.*before.*start"):
        HierarchicalSummary(
            level=SummaryLevel.TASK,
            time_range=(now, now - timedelta(hours=1)),
            summary_text="Invalid",
            key_accomplishments=[],
            key_blockers=[],
            entities_affected=[],
            token_cost=10,
        )
```

## Verification Requirements
1. Run tests to verify they FAIL (no implementation yet)
2. Confirm zero TODOs in test code
3. Confirm zero skipped tests

## Test Lock Confirmation
After this phase, tests become IMMUTABLE.
```

### Phase 4: IMPLEMENT (Agent: `implementer`)

**Delegation Prompt:**

```
@implementer Implement the Hierarchical Session Summarizer to pass all LOCKED tests.

## LOCKED Test File
tests/test_summarizer.py (22 tests)

## Pre-Implementation Checklist
- [x] Tests are LOCKED (approved in TEST_IMPL phase)
- [x] I understand I CANNOT modify tests
- [x] I will iterate until ALL tests pass

## Files to Create
- src/ledger/summarizer.py (NEW - main implementation)

## Files to Modify  
- src/ledger/__init__.py (add exports)

## Implementation Template

```python
"""
Hierarchical Session Summarizer.

Generates multi-level summaries of programming sessions for efficient
context loading when resuming work.

Version: 2.6.0
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Tuple, Optional


class SummaryLevel(Enum):
    """Hierarchy levels for summaries."""
    SESSION = 0   # Entire session
    PHASE = 1     # Major work phases (1-2 hours)
    TASK = 2      # Individual tasks (15-30 min)
    ATOMIC = 3    # Individual progress entries


@dataclass(frozen=True)
class HierarchicalSummary:
    """
    Immutable summary node in the hierarchy.
    
    Attributes:
        level: Position in summary hierarchy
        time_range: (start, end) datetime tuple
        summary_text: Human-readable summary
        key_accomplishments: List of completed items
        key_blockers: List of blocking issues
        entities_affected: Files/functions modified
        token_cost: Estimated tokens for this summary
        child_summaries: Nested summaries (lower levels)
    """
    level: SummaryLevel
    time_range: Tuple[datetime, datetime]
    summary_text: str
    key_accomplishments: List[str]
    key_blockers: List[str]
    entities_affected: List[str]
    token_cost: int
    child_summaries: List['HierarchicalSummary'] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate time range."""
        start, end = self.time_range
        if end < start:
            raise ValueError(f"Invalid time range: end ({end}) before start ({start})")


class HierarchicalSummarizer:
    """
    Generates hierarchical summaries from task ledger data.
    """
    
    def __init__(self, gap_threshold_minutes: int = 90):
        """
        Initialize summarizer.
        
        Args:
            gap_threshold_minutes: Gap size that defines phase boundary
        """
        self.gap_threshold = timedelta(minutes=gap_threshold_minutes)
        self._cached_session_summary: Optional[HierarchicalSummary] = None
    
    def detect_phases(self, tasks: List['TaskLedger']) -> List[List['TaskLedger']]:
        """
        Group tasks into phases based on time proximity.
        
        Args:
            tasks: List of TaskLedger objects
            
        Returns:
            List of task clusters (phases)
        """
        # TODO: Implement phase detection logic
        pass
    
    def summarize_task(self, task: 'TaskLedger') -> HierarchicalSummary:
        """
        Create TASK-level summary from a TaskLedger.
        
        Args:
            task: TaskLedger to summarize
            
        Returns:
            HierarchicalSummary at TASK level
        """
        # TODO: Implement task summarization
        pass
    
    def summarize_phase(
        self, 
        task_summaries: List[HierarchicalSummary]
    ) -> HierarchicalSummary:
        """
        Create PHASE-level summary from task summaries.
        
        Args:
            task_summaries: List of TASK-level summaries
            
        Returns:
            HierarchicalSummary at PHASE level
        """
        # TODO: Implement phase summarization
        pass
    
    def summarize_session(
        self, 
        phase_summaries: List[HierarchicalSummary]
    ) -> HierarchicalSummary:
        """
        Create SESSION-level summary from phase summaries.
        
        Args:
            phase_summaries: List of PHASE-level summaries
            
        Returns:
            HierarchicalSummary at SESSION level
        """
        # TODO: Implement session summarization
        pass
    
    def load_context_for_query(
        self, 
        query: str, 
        token_budget: int
    ) -> str:
        """
        Load appropriate context for a query within token budget.
        
        Args:
            query: User query to contextualize
            token_budget: Maximum tokens to return
            
        Returns:
            Formatted context string
            
        Raises:
            ValueError: If token_budget <= 0
        """
        # TODO: Implement context loading
        pass
    
    def _classify_query_scope(self, query: str) -> int:
        """
        Classify query to determine appropriate summary level.
        
        Args:
            query: User query
            
        Returns:
            SummaryLevel value (0-3)
        """
        # TODO: Implement query classification
        pass
```

## Iteration Protocol
```
TEST ITERATION: [N]/50
- Command: python3 -m pytest tests/test_summarizer.py -v --tb=short
- Status: [X]/22 passing
- Focus: [current failing test]
```

## Constraints
- NEVER modify test files
- NO TODOs in final code
- NO mocks in production code
- Run tests after EVERY change
- Escalate at iteration 50 if not complete
```

### Phase 5: VALIDATE (Agent: `validator`)

**Delegation Prompt:**

```
@validator Run TDD validation stack on HIER-001 implementation.

## Target Files
- src/ledger/summarizer.py
- src/ledger/__init__.py

## Validation Stack

### Layer 1: Static Analysis
```bash
python3 -m py_compile src/ledger/summarizer.py
python3 -m mypy src/ledger/summarizer.py --ignore-missing-imports
```

### Layer 2: Test Suite (100% Required)
```bash
python3 -m pytest tests/test_summarizer.py -v --tb=short
```

### Layer 3: TODO/FIXME Check
```bash
grep -rn "TODO\|FIXME\|HACK" src/ledger/summarizer.py || echo "None found"
```

### Layer 4: Mock Detection
```bash
grep -rn "Mock\|MagicMock\|patch" src/ledger/summarizer.py || echo "None found"
```

### Layer 5: Integration (if applicable)
```bash
python3 -m pytest tests/test_summarizer_integration.py -v || echo "Skipped"
```

## Pass Criteria
| Check | Requirement |
|-------|-------------|
| Tests | 22/22 passing (100%) |
| TODOs | 0 in production code |
| Mocks | 0 in production code |
| Types | 0 errors |

## Output
Produce TDD Validation Report with pass/fail verdict.
```

### Phase 6: REVIEW (Agents: `critic` + `panel-coordinator`)

**Delegation Prompt for Critic:**

```
@critic Review the HIER-001 implementation for quality and correctness.

## Implementation
- File: src/ledger/summarizer.py
- Tests: tests/test_summarizer.py (22 tests, all passing)
- Validation: PASSED

## Critique Focus Areas
1. Code quality and maintainability
2. Edge case handling
3. Performance characteristics
4. Integration concerns
5. Backward compatibility

## Constraints
- Maximum 3 critique rounds
- Read-only (do not modify implementation)
- Provide constructive recommendations

## Output
Critical Analysis with verdict: Approve/Revise/Reject
```

**Delegation Prompt for Panel Coordinator:**

```
@panel-coordinator Orchestrate panel review for HIER-001 implementation.

## Subject
Hierarchical Session Summarizer implementation

## Panel Configuration
- Minimum: 5 judges
- Required perspectives: Technical, Completeness, Practicality

## Evaluation Criteria
1. Technical correctness
2. Test coverage completeness
3. Code quality
4. Performance
5. Maintainability

## Threshold
- Mean score ≥ 4.0/5.0 for approval
- No critical issues from any judge

## Output
Panel verdict with aggregated scores and recommendations.
```

---

## Enhancement 2: KG-001/002 - Temporal Entity Extensions

### Orchestrator Dispatch

```
@orchestrator Execute KG-001/002: Temporal Entity Extensions

## Context
Extend the existing Entity class in src/knowledge/graph.py with:
1. Temporal validity fields (valid_from, valid_to)
2. Code-specific entity types (FILE, FUNCTION, CLASS, MODULE, VARIABLE, DEPENDENCY)
3. Source location field (source_location)
4. Validity check method (is_valid())

## Constraints
- Backward compatible with existing Entity usage
- Default values for new fields
- No breaking changes to existing tests

## Delegation
Start with planner for SPEC phase.
```

### Quick Specification Summary

**New EntityType Values:**
```python
class EntityType(str, Enum):
    # Existing values...
    FILE = "file"
    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"
    VARIABLE = "variable"
    DEPENDENCY = "dependency"
```

**Extended Entity Fields:**
```python
@dataclass
class Entity:
    name: str
    entity_type: EntityType = EntityType.OTHER
    metadata: Dict[str, Any] = field(default_factory=dict)
    # NEW fields
    valid_from: datetime = field(default_factory=utc_now)
    valid_to: Optional[datetime] = None
    source_location: Optional[str] = None  # "file:line" format
    
    def is_valid(self, reference_time: Optional[datetime] = None) -> bool:
        """Check if entity is valid at reference time."""
        ref = reference_time or utc_now()
        if self.valid_to is None:
            return True
        return self.valid_to > ref
```

**Test Count:** 14 unit tests

---

## Enhancement 3: RETR-001 - Hybrid Vector-Graph Retriever

### Orchestrator Dispatch

```
@orchestrator Execute RETR-001: Hybrid Vector-Graph Retriever

## Context
Create unified retrieval interface that combines:
1. Vector similarity search (find_claims_by_embedding)
2. Graph traversal (find_claims_by_entity, get_related_claims)
3. Automatic query classification
4. Result fusion and reranking

## Module
src/knowledge/retriever.py (NEW)

## Dependencies
- src/knowledge/storage.py (existing backends)
- src/knowledge/graph.py (existing types)

## Key Components
1. QueryType enum: SEMANTIC, ENTITY_CENTRIC, TEMPORAL, CAUSAL, GLOBAL
2. HybridRetriever class with retrieve() method
3. Query classification heuristics
4. Result fusion logic

## Delegation
Start with planner for SPEC phase.
```

### Quick Specification Summary

```python
class QueryType(Enum):
    SEMANTIC = "semantic"       # "Find similar discussions"
    ENTITY_CENTRIC = "entity"   # "What do we know about X?"
    TEMPORAL = "temporal"       # "What changed since yesterday?"
    CAUSAL = "causal"          # "Why did X happen?"
    GLOBAL = "global"          # "Summarize all knowledge"


class HybridRetriever:
    def __init__(self, storage: GraphStorageBackend, embedder: Callable = None):
        self.storage = storage
        self.embedder = embedder
    
    async def retrieve(
        self,
        query: str,
        strategy: Optional[str] = None,
        limit: int = 10
    ) -> RetrievalResult:
        """Unified retrieval with automatic strategy selection."""
        query_type = self._classify_query(query) if not strategy else QueryType(strategy)
        
        if query_type == QueryType.SEMANTIC:
            return await self._semantic_retrieval(query, limit)
        elif query_type == QueryType.ENTITY_CENTRIC:
            return await self._entity_retrieval(query, limit)
        elif query_type == QueryType.CAUSAL:
            return await self._hybrid_retrieval(query, limit)  # Combine both
        else:
            return await self._hybrid_retrieval(query, limit)
```

**Test Count:** 18 unit tests

---

## Enhancement 4: AUDIT-001 - Entity-Aware Provenance

### Orchestrator Dispatch

```
@orchestrator Execute AUDIT-001: Entity-Aware Provenance Queries

## Context
Extend src/audit/query.py with entity-specific provenance queries:
1. get_provenance_for_entity(entity_name, entity_type)
2. get_decision_chain_for_file(file_path)

## Integration
Cross-link audit entries with KG claims via audit_entry_ids field.

## Delegation
Start with planner for SPEC phase.
```

**Test Count:** 8 unit tests

---

## Progress Tracking Template

Use this format to track implementation progress:

```markdown
## KVT Enhancement Progress Ledger

### HIER-001: Hierarchical Summarizer
| Phase | Status | Agent | Started | Completed | Notes |
|-------|--------|-------|---------|-----------|-------|
| SPEC | ⬜ | planner | - | - | |
| TEST_DESIGN | ⬜ | test-writer | - | - | |
| TEST_IMPL | ⬜ | test-writer | - | - | Tests LOCKED |
| IMPLEMENT | ⬜ | implementer | - | - | Iteration: 0/50 |
| VALIDATE | ⬜ | validator | - | - | |
| REVIEW | ⬜ | critic | - | - | |
| DELIVER | ⬜ | orchestrator | - | - | |

### KG-001/002: Temporal Entity Extensions
| Phase | Status | Agent | Started | Completed | Notes |
|-------|--------|-------|---------|-----------|-------|
| SPEC | ⬜ | planner | - | - | |
| ... | | | | | |

### RETR-001: Hybrid Retriever
| Phase | Status | Agent | Started | Completed | Notes |
|-------|--------|-------|---------|-----------|-------|
| SPEC | ⬜ | planner | - | - | |
| ... | | | | | |

### AUDIT-001: Entity-Aware Provenance
| Phase | Status | Agent | Started | Completed | Notes |
|-------|--------|-------|---------|-----------|-------|
| SPEC | ⬜ | planner | - | - | |
| ... | | | | | |

**Legend:** ⬜ Not Started | 🔄 In Progress | ✅ Complete | ❌ Blocked
```

---

## Handoff Schema

All agent handoffs must include:

```json
{
  "task_id": "HIER-001",
  "phase": "SPEC|TEST_DESIGN|TEST_IMPL|IMPLEMENT|VALIDATE|REVIEW",
  "status": "COMPLETE|IN_PROGRESS|BLOCKED",
  "from_agent": "planner",
  "to_agent": "test-writer",
  "artifacts": [
    "path/to/file.py"
  ],
  "summary": "Brief description (≤100 tokens)",
  "next_action": "What the receiving agent should do",
  "blockers": [],
  "confidence": "HIGH|MEDIUM|LOW",
  "token_count": 500,
  "iteration": "1/5"
}
```

---

## Success Metrics

| Enhancement | Tests | Pass Rate | TODOs | Mocks | Panel Score |
|-------------|-------|-----------|-------|-------|-------------|
| HIER-001 | 22 | 100% | 0 | 0 | ≥4.0 |
| KG-001/002 | 14 | 100% | 0 | 0 | ≥4.0 |
| RETR-001 | 18 | 100% | 0 | 0 | ≥4.0 |
| AUDIT-001 | 8 | 100% | 0 | 0 | ≥4.0 |
| **Total** | **62** | **100%** | **0** | **0** | **≥4.0** |

---

## Quick Reference: Agent Capabilities

| Agent | Model | Tier | Tools | Primary Role |
|-------|-------|------|-------|--------------|
| orchestrator | Opus | 1 | Task, Read, Grep, Glob, Bash | Workflow coordination |
| planner | Opus | 1 | Task, Read, Grep, Glob | Product specifications |
| test-writer | Haiku | 3 | Read, Write, Edit, Bash, Grep, Glob | Test design & implementation |
| implementer | Sonnet | 2 | Read, Edit, Write, Bash, Grep, Glob | Code implementation |
| validator | Haiku | 3 | Bash, Read, Grep, Glob | TDD validation |
| critic | Opus | 1 | Read, Grep, Glob, WebSearch, WebFetch | Quality challenges |
| panel-coordinator | Sonnet | 2 | Task, Read, Grep, Glob | Judge panel orchestration |
| synthesis | Opus | 1 | Read, Grep, Glob | Combine outputs |

---

## Document Version

**Version:** 2.0  
**Created:** December 2025  
**Status:** Ready for Execution

**🚀 START HERE:** Execute the Initial Dispatch Command to `orchestrator` at the top of this document.