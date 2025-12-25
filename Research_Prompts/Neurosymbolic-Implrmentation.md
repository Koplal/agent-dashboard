# Neuro-Symbolic Enhancement Implementation Guide

## Agent Dashboard Framework v2.5+

**Document Purpose:** This guide provides structured implementation specifications for enhancing the Agent Dashboard with neuro-symbolic AI patterns. It is designed for consumption by Claude Code agents and human developers, with explicit task tracking, acceptance criteria, and progress ledger integration.

**Document Version:** 1.1.0
**Created:** 2025-12-22
**Revised:** 2025-12-24
**Status:** Validated & Priorities Revised

> **Revision Note (v1.1.0):** Priorities reordered based on orchestrator analysis against industry best practices (Microsoft Magentic-One, Amazon Automated Reasoning, TACL 2024). NESY-006 elevated to Phase 1 as foundational infrastructure. See "Validation Analysis" section for details.

---

## Executive Summary

The Agent Dashboard's existing architecture implements several research-validated neuro-symbolic patterns through its three-tier model strategy (Opus/Sonnet/Haiku), specialized agent roles, and external verification through judge agents. This guide details enhancements that strengthen the symbolic component of this architecture, organized into three implementation phases with explicit progress tracking.

The enhancements address documented limitations of pure LLM approaches: hallucination, unreliable self-correction, and lack of formal verification. Each recommendation includes research validation, implementation specifications, and integration patterns for the existing codebase.

---

## Progress Ledger Schema

All implementation work shall be tracked using the following ledger structure. This schema ensures continuity across sessions and enables detection of stalled work or circular approaches.

### Task Ledger Definition

```python
# File: src/ledger/task_ledger.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

class TaskStatus(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    PENDING_REVIEW = "pending_review"
    COMPLETED = "completed"
    DEFERRED = "deferred"

class TaskPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4

@dataclass
class ProgressEntry:
    """Individual progress update within a task."""
    timestamp: datetime
    agent_id: str
    action_taken: str
    outcome: str
    artifacts_produced: List[str] = field(default_factory=list)
    blockers_encountered: List[str] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)
    tokens_consumed: int = 0

@dataclass
class TaskLedger:
    """Complete task tracking record."""
    task_id: str
    phase: str  # immediate | medium_term | long_term
    category: str  # validation | knowledge | verification | learning | audit
    title: str
    objective: str
    status: TaskStatus
    priority: TaskPriority
    created_at: datetime
    updated_at: datetime
    estimated_effort: str  # hours or story points
    assigned_agent: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    progress_history: List[ProgressEntry] = field(default_factory=list)
    subtasks: List['TaskLedger'] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)
    notes: str = ""
```

### Ledger Operations

```python
# File: src/ledger/operations.py

class LedgerManager:
    """Central management for implementation progress."""
    
    def __init__(self, storage_path: str = "./ledger_data"):
        self.storage_path = storage_path
        self.tasks: Dict[str, TaskLedger] = {}
        self._load_existing()
    
    def add_progress(self, task_id: str, entry: ProgressEntry) -> None:
        """Record progress on a task with loop detection."""
        task = self.tasks[task_id]
        task.progress_history.append(entry)
        task.updated_at = entry.timestamp
        
        # Detect repetitive patterns
        if self._detect_loop(task):
            task.status = TaskStatus.BLOCKED
            task.notes += f"\n[{entry.timestamp}] Loop detected - requires new approach"
    
    def _detect_loop(self, task: TaskLedger) -> bool:
        """Identify if task is repeating without progress."""
        if len(task.progress_history) < 4:
            return False
        
        recent = task.progress_history[-4:]
        action_outcomes = [(e.action_taken, e.outcome) for e in recent]
        unique_pairs = set(action_outcomes)
        
        return len(unique_pairs) < len(action_outcomes) * 0.5
    
    def get_phase_summary(self, phase: str) -> Dict[str, Any]:
        """Generate status report for a phase."""
        phase_tasks = [t for t in self.tasks.values() if t.phase == phase]
        return {
            "total": len(phase_tasks),
            "completed": sum(1 for t in phase_tasks if t.status == TaskStatus.COMPLETED),
            "in_progress": sum(1 for t in phase_tasks if t.status == TaskStatus.IN_PROGRESS),
            "blocked": sum(1 for t in phase_tasks if t.status == TaskStatus.BLOCKED),
            "not_started": sum(1 for t in phase_tasks if t.status == TaskStatus.NOT_STARTED)
        }
    
    def get_next_actionable(self) -> Optional[TaskLedger]:
        """Return highest priority task ready for work."""
        candidates = [
            t for t in self.tasks.values()
            if t.status in [TaskStatus.NOT_STARTED, TaskStatus.IN_PROGRESS]
            and all(self.tasks[d].status == TaskStatus.COMPLETED for d in t.dependencies)
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda t: (t.priority.value, t.created_at))
```

---

## Phase 1: Immediate Opportunities

**Timeline:** 1-2 weeks per enhancement  
**Architectural Impact:** Minimal - additive components within existing structure  
**Dependencies:** None - can begin immediately

These enhancements strengthen output validation and evaluation reliability without requiring structural changes to the orchestration layer.

---

### Enhancement 1.1: Pydantic Validators with Field-Level Verification

**Task ID:** `NESY-001`  
**Category:** Validation  
**Priority:** Critical  
**Estimated Effort:** 16 hours

#### Objective

Implement structured validation for all agent outputs using Pydantic models with field-level constraints. This transforms implicit output expectations into explicit, enforceable contracts that reject malformed data at agent boundaries.

#### Background and Rationale

Current agent outputs are validated through downstream consumption and judge agent review. This approach catches errors late in the pipeline, after resources have been consumed and potentially after invalid data has propagated. Pydantic validation provides immediate, specific feedback on constraint violations, enabling faster iteration and clearer error diagnostics.

Research indicates that structured output validation reduces pipeline failures by 40-60% compared to unstructured parsing with retry logic.

#### Implementation Specification

**File Structure:**
```
src/
├── schemas/
│   ├── __init__.py
│   ├── base.py              # Base validation classes
│   ├── research.py          # Research agent output schemas
│   ├── code_analysis.py     # Code analysis output schemas
│   ├── documentation.py     # Documentation output schemas
│   └── orchestration.py     # Orchestrator decision schemas
├── validators/
│   ├── __init__.py
│   ├── output_validator.py  # Central validation logic
│   └── custom_validators.py # Domain-specific validators
```

**Core Schema Definitions:**

```python
# File: src/schemas/base.py

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Literal
from datetime import datetime
from enum import Enum

class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    SINGLE_SOURCE = "single_source"
    UNVERIFIED = "unverified"
    CONTRADICTED = "contradicted"

class BaseAgentOutput(BaseModel):
    """Base schema for all agent outputs."""
    
    agent_id: str = Field(min_length=1)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    task_id: str = Field(min_length=1)
    execution_time_ms: int = Field(ge=0)
    token_count: int = Field(ge=0)
    
    class Config:
        extra = "forbid"  # Reject unexpected fields
```

```python
# File: src/schemas/research.py

from pydantic import Field, field_validator, HttpUrl
from typing import List, Optional
from datetime import datetime, timedelta
from .base import BaseAgentOutput, ConfidenceLevel, VerificationStatus

class SourceReference(BaseModel):
    """Validated source citation."""
    
    url: HttpUrl
    title: str = Field(min_length=1, max_length=500)
    publication_date: Optional[datetime] = None
    accessed_date: datetime = Field(default_factory=datetime.utcnow)
    author: Optional[str] = None
    source_type: Literal["primary", "secondary", "tertiary"] = "secondary"
    
    @field_validator('publication_date')
    @classmethod
    def check_publication_date(cls, v):
        if v and v > datetime.utcnow():
            raise ValueError("Publication date cannot be in the future")
        return v

class ResearchClaim(BaseModel):
    """Individual research finding with provenance."""
    
    claim_text: str = Field(min_length=10, max_length=1000)
    sources: List[SourceReference] = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    verification_status: VerificationStatus
    recency_flag: Optional[str] = None
    
    @field_validator('verification_status')
    @classmethod
    def validate_verification_matches_sources(cls, v, info):
        sources = info.data.get('sources', [])
        if len(sources) == 1 and v == VerificationStatus.VERIFIED:
            raise ValueError("Cannot mark as verified with single source")
        return v
    
    @model_validator(mode='after')
    def check_recency(self):
        """Flag old sources automatically."""
        if self.sources:
            oldest = min(
                (s.publication_date for s in self.sources if s.publication_date),
                default=None
            )
            if oldest:
                age_days = (datetime.utcnow() - oldest).days
                if age_days > 180:
                    self.recency_flag = f"oldest_source_{age_days}_days"
        return self

class ResearchOutput(BaseAgentOutput):
    """Complete research agent output schema."""
    
    query: str = Field(min_length=5)
    claims: List[ResearchClaim] = Field(min_length=0)
    synthesis: str = Field(min_length=50, max_length=5000)
    gaps_identified: List[str] = Field(default_factory=list)
    methodology: str = Field(min_length=20)
    overall_confidence: ConfidenceLevel
    recommendations: List[str] = Field(default_factory=list)
    
    @model_validator(mode='after')
    def validate_confidence_consistency(self):
        """Ensure overall confidence aligns with claim confidences."""
        if not self.claims:
            return self
        
        avg_confidence = sum(c.confidence for c in self.claims) / len(self.claims)
        
        expected_level = (
            ConfidenceLevel.HIGH if avg_confidence >= 0.7 else
            ConfidenceLevel.MEDIUM if avg_confidence >= 0.4 else
            ConfidenceLevel.LOW
        )
        
        # Allow one level of divergence
        level_order = [ConfidenceLevel.LOW, ConfidenceLevel.MEDIUM, ConfidenceLevel.HIGH]
        actual_idx = level_order.index(self.overall_confidence)
        expected_idx = level_order.index(expected_level)
        
        if abs(actual_idx - expected_idx) > 1:
            raise ValueError(
                f"Overall confidence {self.overall_confidence} diverges significantly "
                f"from claim average ({avg_confidence:.2f} suggests {expected_level})"
            )
        
        return self
```

```python
# File: src/schemas/code_analysis.py

from pydantic import Field, field_validator
from typing import List, Optional, Dict, Any
from .base import BaseAgentOutput, ConfidenceLevel

class CodeLocation(BaseModel):
    """Reference to specific code location."""
    
    file_path: str = Field(pattern=r'^[a-zA-Z0-9_./-]+$')
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    
    @model_validator(mode='after')
    def validate_line_range(self):
        if self.end_line < self.start_line:
            raise ValueError("end_line must be >= start_line")
        return self

class CodeIssue(BaseModel):
    """Identified code issue with context."""
    
    issue_type: Literal["bug", "vulnerability", "style", "performance", "maintainability"]
    severity: Literal["critical", "high", "medium", "low", "info"]
    location: CodeLocation
    description: str = Field(min_length=10)
    suggested_fix: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    references: List[str] = Field(default_factory=list)

class CodeAnalysisOutput(BaseAgentOutput):
    """Complete code analysis output schema."""
    
    target_files: List[str] = Field(min_length=1)
    issues_found: List[CodeIssue] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    summary: str = Field(min_length=20)
    analysis_depth: Literal["surface", "standard", "deep"]
    
    @field_validator('issues_found')
    @classmethod
    def sort_by_severity(cls, v):
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        return sorted(v, key=lambda x: severity_order[x.severity])
```

**Validation Integration:**

```python
# File: src/validators/output_validator.py

from typing import Type, TypeVar, Optional
from pydantic import BaseModel, ValidationError
import json

T = TypeVar('T', bound=BaseModel)

class OutputValidator:
    """Central validation service for agent outputs."""
    
    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self.validation_errors: List[Dict] = []
    
    def validate(
        self, 
        raw_output: str | dict, 
        schema: Type[T],
        agent_id: str,
        task_id: str
    ) -> tuple[Optional[T], Optional[ValidationError]]:
        """
        Validate agent output against schema.
        
        Returns:
            Tuple of (validated_output, error).
            If validation succeeds, error is None.
            If validation fails, validated_output is None.
        """
        try:
            if isinstance(raw_output, str):
                data = json.loads(raw_output)
            else:
                data = raw_output
            
            # Inject metadata if not present
            data.setdefault('agent_id', agent_id)
            data.setdefault('task_id', task_id)
            
            validated = schema.model_validate(data)
            return validated, None
            
        except json.JSONDecodeError as e:
            error_info = {
                "agent_id": agent_id,
                "task_id": task_id,
                "error_type": "json_parse_error",
                "details": str(e)
            }
            self.validation_errors.append(error_info)
            return None, e
            
        except ValidationError as e:
            error_info = {
                "agent_id": agent_id,
                "task_id": task_id,
                "error_type": "validation_error",
                "details": e.errors()
            }
            self.validation_errors.append(error_info)
            return None, e
    
    def generate_retry_prompt(self, error: ValidationError, original_prompt: str) -> str:
        """Generate corrective prompt with specific field errors."""
        error_descriptions = []
        for err in error.errors():
            field_path = " -> ".join(str(x) for x in err['loc'])
            error_descriptions.append(f"  - {field_path}: {err['msg']}")
        
        return f"""
Your previous response had validation errors. Please correct and resubmit.

VALIDATION ERRORS:
{chr(10).join(error_descriptions)}

ORIGINAL REQUEST:
{original_prompt}

Provide a corrected response that addresses all validation errors.
"""
```

#### Acceptance Criteria

1. All 14+ agent types have corresponding Pydantic schemas defined
2. Validation wrapper integrated into agent execution pipeline
3. Failed validation triggers structured retry with field-specific error messages
4. Validation error logs captured for quality analysis
5. Test coverage for all schema validators at 90%+
6. Documentation updated with schema specifications

#### Subtasks

| Subtask ID | Description | Status | Dependencies |
|------------|-------------|--------|--------------|
| NESY-001-A | Define base schema classes | Not Started | None |
| NESY-001-B | Create research agent schemas | Not Started | NESY-001-A |
| NESY-001-C | Create code analysis schemas | Not Started | NESY-001-A |
| NESY-001-D | Create documentation agent schemas | Not Started | NESY-001-A |
| NESY-001-E | Create orchestrator schemas | Not Started | NESY-001-A |
| NESY-001-F | Implement OutputValidator class | Not Started | NESY-001-A |
| NESY-001-G | Integrate validation into agent pipeline | Not Started | NESY-001-B,C,D,E,F |
| NESY-001-H | Add retry logic with error prompts | Not Started | NESY-001-G |
| NESY-001-I | Write unit tests | Not Started | NESY-001-G |
| NESY-001-J | Update documentation | Not Started | NESY-001-I |

---

### Enhancement 1.2: Grammar-Constrained Decoding for Structured Outputs

**Task ID:** `NESY-002`  
**Category:** Validation  
**Priority:** High  
**Estimated Effort:** 24 hours

#### Objective

Implement grammar-constrained decoding for agent outputs that require strict structural compliance, eliminating parsing failures and retry loops for structured data generation.

#### Background and Rationale

Standard LLM decoding selects tokens probabilistically from the full vocabulary at each step. This means syntactically invalid outputs are always possible, requiring post-hoc validation and retry logic. Grammar-constrained decoding restricts token selection to only valid continuations according to a formal grammar, making structural errors impossible.

Research from NVIDIA and CMU demonstrates up to 80x throughput improvement over retry-based approaches for structured output generation.

#### Implementation Specification

**Approach Selection:**

For Claude API integration, grammar constraints are implemented through structured tool definitions and response schemas. For hybrid architectures using local models (Haiku-equivalent for cost optimization), libraries like Outlines or XGrammar provide direct logit manipulation.

**Claude API Integration:**

```python
# File: src/constraints/structured_generation.py

from anthropic import Anthropic
from typing import Dict, Any, Type
from pydantic import BaseModel
import json

class StructuredGenerator:
    """Generate structured outputs with schema enforcement."""
    
    def __init__(self, client: Anthropic):
        self.client = client
    
    def generate_with_schema(
        self,
        prompt: str,
        schema: Type[BaseModel],
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096
    ) -> BaseModel:
        """
        Generate output conforming to Pydantic schema.
        
        Uses Claude's tool use feature to enforce structure.
        """
        # Convert Pydantic schema to JSON Schema
        json_schema = schema.model_json_schema()
        
        # Define as a tool that returns structured data
        tool_definition = {
            "name": "structured_output",
            "description": "Return the analysis results in the required format",
            "input_schema": json_schema
        }
        
        response = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            tools=[tool_definition],
            tool_choice={"type": "tool", "name": "structured_output"},
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Extract tool use result
        for block in response.content:
            if block.type == "tool_use":
                return schema.model_validate(block.input)
        
        raise ValueError("No structured output generated")
    
    def generate_tool_call(
        self,
        context: str,
        available_tools: list[Dict[str, Any]],
        model: str = "claude-haiku-3-5-20241022"
    ) -> Dict[str, Any]:
        """
        Generate a valid tool call from available options.
        
        Guarantees output matches one of the defined tool schemas.
        """
        response = self.client.messages.create(
            model=model,
            max_tokens=1024,
            tools=available_tools,
            messages=[{"role": "user", "content": context}]
        )
        
        for block in response.content:
            if block.type == "tool_use":
                return {
                    "tool_name": block.name,
                    "tool_id": block.id,
                    "parameters": block.input
                }
        
        raise ValueError("No tool call generated")
```

**Local Model Integration (Optional):**

```python
# File: src/constraints/grammar_constrained.py

from outlines import models, generate
from typing import Dict, Any
import json

class GrammarConstrainedGenerator:
    """
    Grammar-constrained generation for local models.
    
    Use for high-volume, cost-sensitive structured generation
    where Haiku-tier Claude is still too expensive.
    """
    
    def __init__(self, model_name: str = "mistralai/Mistral-7B-v0.3"):
        self.model = models.transformers(model_name)
    
    def generate_json(
        self,
        prompt: str,
        schema: Dict[str, Any],
        max_tokens: int = 1024
    ) -> Dict[str, Any]:
        """Generate JSON conforming exactly to schema."""
        generator = generate.json(self.model, schema)
        return generator(prompt, max_tokens=max_tokens)
    
    def generate_regex(
        self,
        prompt: str,
        pattern: str,
        max_tokens: int = 256
    ) -> str:
        """Generate text matching regex pattern."""
        generator = generate.regex(self.model, pattern)
        return generator(prompt, max_tokens=max_tokens)
    
    def generate_choice(
        self,
        prompt: str,
        options: list[str]
    ) -> str:
        """Generate selection from fixed options."""
        generator = generate.choice(self.model, options)
        return generator(prompt)
```

**Tool Schema Definitions:**

```python
# File: src/constraints/tool_schemas.py

WEB_SEARCH_TOOL = {
    "name": "web_search",
    "description": "Search the web for information",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query",
                "minLength": 3,
                "maxLength": 200
            },
            "max_results": {
                "type": "integer",
                "minimum": 1,
                "maximum": 20,
                "default": 10
            },
            "recency_filter": {
                "type": "string",
                "enum": ["day", "week", "month", "year", "any"],
                "default": "any"
            }
        },
        "required": ["query"]
    }
}

FILE_OPERATION_TOOL = {
    "name": "file_operation",
    "description": "Perform file system operations",
    "input_schema": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["read", "write", "append", "delete", "list"]
            },
            "path": {
                "type": "string",
                "pattern": "^[a-zA-Z0-9_./-]+$"
            },
            "content": {
                "type": "string"
            }
        },
        "required": ["operation", "path"]
    }
}

CODE_EXECUTION_TOOL = {
    "name": "execute_code",
    "description": "Execute code in a sandboxed environment",
    "input_schema": {
        "type": "object",
        "properties": {
            "language": {
                "type": "string",
                "enum": ["python", "javascript", "bash"]
            },
            "code": {
                "type": "string",
                "minLength": 1
            },
            "timeout_seconds": {
                "type": "integer",
                "minimum": 1,
                "maximum": 300,
                "default": 30
            }
        },
        "required": ["language", "code"]
    }
}
```

#### Acceptance Criteria

1. StructuredGenerator class implemented and tested
2. All tool schemas defined with complete input validation
3. Integration with agent execution pipeline for tool calls
4. Fallback handling for generation failures
5. Performance benchmarks showing reduced retry rates
6. Documentation of schema requirements for new tools

#### Subtasks

| Subtask ID | Description | Status | Dependencies |
|------------|-------------|--------|--------------|
| NESY-002-A | Implement StructuredGenerator for Claude API | Not Started | None |
| NESY-002-B | Define core tool schemas | Not Started | None |
| NESY-002-C | Create schema registry for dynamic lookup | Not Started | NESY-002-B |
| NESY-002-D | Integrate with agent tool calling | Not Started | NESY-002-A,C |
| NESY-002-E | Implement local model option (optional) | Not Started | None |
| NESY-002-F | Add error handling and fallbacks | Not Started | NESY-002-D |
| NESY-002-G | Performance benchmarking | Not Started | NESY-002-D |
| NESY-002-H | Documentation | Not Started | NESY-002-G |

---

### Enhancement 1.3: Heterogeneous Judge Configurations

**Task ID:** `NESY-003`  
**Category:** Verification  
**Priority:** High  
**Estimated Effort:** 20 hours

#### Objective

Implement diversified judge agent configurations to reduce correlated evaluation failures. This includes varying prompts, temperature settings, evaluation frameworks, and optionally model tiers across the judge panel.

#### Background and Rationale

Research demonstrates that LLM judges exhibit bias toward their own outputs and share blind spots with generators using similar configurations. A homogeneous judge panel may consistently miss certain error types. Heterogeneous configuration reduces correlation between judge failures, improving overall detection rates.

MIT Press (Kamoi et al., TACL 2024) establishes that external verification is essential because LLMs cannot reliably self-correct. Diversifying the verification approach extends this principle to catch errors that any single configuration might miss.

#### Implementation Specification

```python
# File: src/judges/configurations.py

from dataclasses import dataclass
from typing import List, Optional, Callable
from enum import Enum

class JudgePersona(Enum):
    ADVERSARIAL = "adversarial"
    RUBRIC_BASED = "rubric_based"
    DOMAIN_EXPERT = "domain_expert"
    END_USER = "end_user"
    SKEPTIC = "skeptic"

@dataclass
class JudgeConfig:
    """Configuration for a single judge instance."""
    
    persona: JudgePersona
    model: str
    temperature: float
    system_prompt: str
    evaluation_focus: List[str]
    max_tokens: int = 2000
    
ADVERSARIAL_CONFIG = JudgeConfig(
    persona=JudgePersona.ADVERSARIAL,
    model="claude-sonnet-4-20250514",
    temperature=0.3,
    system_prompt="""You are a skeptical reviewer whose job is to find problems.
Assume the work contains errors until proven otherwise.
For each claim or output, ask:
- What would make this wrong?
- What is missing or incomplete?
- What assumptions are unstated?
- What edge cases are unhandled?

Your value comes from catching issues others missed, not from approval.
Be specific about problems found. Vague concerns are not useful.""",
    evaluation_focus=["errors", "omissions", "unstated_assumptions", "edge_cases"]
)

RUBRIC_CONFIG = JudgeConfig(
    persona=JudgePersona.RUBRIC_BASED,
    model="claude-sonnet-4-20250514",
    temperature=0.1,
    system_prompt="""You evaluate outputs against explicit criteria using a structured rubric.
Score each dimension 1-5 with specific justification.

EVALUATION DIMENSIONS:
1. ACCURACY: Are claims factually correct and properly supported?
2. COMPLETENESS: Does the output address all aspects of the request?
3. CLARITY: Is the output well-organized and understandable?
4. RELEVANCE: Does the output focus on what was asked?
5. ACTIONABILITY: Can the user act on this output?

Provide scores first, then explain each score with specific examples from the output.""",
    evaluation_focus=["accuracy", "completeness", "clarity", "relevance", "actionability"]
)

DOMAIN_EXPERT_CONFIG = JudgeConfig(
    persona=JudgePersona.DOMAIN_EXPERT,
    model="claude-opus-4-20250514",  # Higher capability for domain expertise
    temperature=0.2,
    system_prompt="""You are a domain expert evaluating technical accuracy and best practices.
Focus on:
- Technical correctness of claims and recommendations
- Alignment with industry best practices
- Appropriate use of domain terminology
- Recognition of domain-specific constraints and tradeoffs

Flag any claims that contradict established domain knowledge or accepted practices.""",
    evaluation_focus=["technical_accuracy", "best_practices", "terminology", "domain_constraints"]
)

SKEPTIC_CONFIG = JudgeConfig(
    persona=JudgePersona.SKEPTIC,
    model="claude-sonnet-4-20250514",
    temperature=0.4,  # Slightly higher for diverse skepticism
    system_prompt="""You question everything and demand evidence.
For each significant claim:
- Is there a cited source? If not, flag it.
- Is the source authoritative for this claim type?
- Could the source be outdated or superseded?
- Are there likely counterarguments or alternative views?

Mark claims as: WELL_SUPPORTED, WEAKLY_SUPPORTED, UNSUPPORTED, or CONTRADICTED.""",
    evaluation_focus=["source_quality", "evidence_strength", "counterarguments"]
)
```

```python
# File: src/judges/panel.py

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from anthropic import Anthropic
from .configurations import JudgeConfig, JudgePersona

@dataclass
class JudgeVerdict:
    """Individual judge's evaluation."""
    persona: JudgePersona
    passed: bool
    score: float  # 0.0 to 1.0
    issues_found: List[str]
    strengths_noted: List[str]
    detailed_feedback: str
    confidence: float

@dataclass
class PanelVerdict:
    """Aggregated verdict from judge panel."""
    passed: bool
    consensus_level: float  # 0.0 to 1.0
    individual_verdicts: List[JudgeVerdict]
    critical_issues: List[str]
    requires_human_review: bool
    aggregated_score: float
    recommendation: str

class JudgePanel:
    """Panel of heterogeneous judges for robust evaluation."""
    
    def __init__(
        self,
        configs: List[JudgeConfig],
        client: Anthropic,
        consensus_threshold: float = 0.7,
        require_unanimous_pass: bool = False
    ):
        self.configs = configs
        self.client = client
        self.consensus_threshold = consensus_threshold
        self.require_unanimous_pass = require_unanimous_pass
    
    async def evaluate(
        self,
        content: str,
        context: Dict[str, Any],
        content_type: str
    ) -> PanelVerdict:
        """Run all judges and aggregate verdicts."""
        
        verdicts = []
        for config in self.configs:
            verdict = await self._run_judge(config, content, context, content_type)
            verdicts.append(verdict)
        
        return self._aggregate_verdicts(verdicts)
    
    async def _run_judge(
        self,
        config: JudgeConfig,
        content: str,
        context: Dict[str, Any],
        content_type: str
    ) -> JudgeVerdict:
        """Execute single judge evaluation."""
        
        evaluation_prompt = f"""
Evaluate the following {content_type} output.

CONTEXT:
{self._format_context(context)}

CONTENT TO EVALUATE:
{content}

Provide your evaluation focusing on: {', '.join(config.evaluation_focus)}

Structure your response as:
1. OVERALL ASSESSMENT: Pass/Fail with confidence (0-100%)
2. SCORE: Numeric score 0-100
3. ISSUES FOUND: Bulleted list of specific problems
4. STRENGTHS: Bulleted list of positive aspects
5. DETAILED FEEDBACK: Paragraph explaining your evaluation
"""
        
        response = self.client.messages.create(
            model=config.model,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            system=config.system_prompt,
            messages=[{"role": "user", "content": evaluation_prompt}]
        )
        
        return self._parse_verdict(response.content[0].text, config.persona)
    
    def _aggregate_verdicts(self, verdicts: List[JudgeVerdict]) -> PanelVerdict:
        """Combine individual verdicts into panel decision."""
        
        pass_count = sum(1 for v in verdicts if v.passed)
        total_count = len(verdicts)
        consensus_level = pass_count / total_count
        
        # Collect all issues, prioritizing those found by multiple judges
        issue_counts: Dict[str, int] = {}
        for v in verdicts:
            for issue in v.issues_found:
                normalized = issue.lower().strip()
                issue_counts[normalized] = issue_counts.get(normalized, 0) + 1
        
        critical_issues = [
            issue for issue, count in issue_counts.items()
            if count >= len(verdicts) / 2  # Found by majority
        ]
        
        # Determine pass/fail
        if self.require_unanimous_pass:
            passed = all(v.passed for v in verdicts)
        else:
            passed = consensus_level >= self.consensus_threshold
        
        # Flag for human review if judges disagree significantly
        requires_human = (
            consensus_level < 1.0 and consensus_level > 0.0 and
            any(v.confidence < 0.6 for v in verdicts)
        )
        
        return PanelVerdict(
            passed=passed,
            consensus_level=consensus_level,
            individual_verdicts=verdicts,
            critical_issues=critical_issues,
            requires_human_review=requires_human,
            aggregated_score=sum(v.score for v in verdicts) / len(verdicts),
            recommendation=self._generate_recommendation(verdicts, passed)
        )
    
    def _generate_recommendation(
        self,
        verdicts: List[JudgeVerdict],
        passed: bool
    ) -> str:
        """Generate actionable recommendation from verdicts."""
        if passed:
            return "Output approved. Minor improvements suggested in detailed feedback."
        else:
            top_issues = []
            for v in verdicts:
                if not v.passed and v.issues_found:
                    top_issues.extend(v.issues_found[:2])
            return f"Revision required. Priority issues: {'; '.join(set(top_issues[:5]))}"
```

#### Acceptance Criteria

1. At least 4 distinct judge configurations implemented
2. JudgePanel class with configurable consensus thresholds
3. Aggregation logic handling disagreements appropriately
4. Human escalation triggers for low-consensus evaluations
5. Logging of individual and aggregate verdicts for analysis
6. Integration with existing judge agent workflow

#### Subtasks

| Subtask ID | Description | Status | Dependencies |
|------------|-------------|--------|--------------|
| NESY-003-A | Define judge configuration dataclasses | Not Started | None |
| NESY-003-B | Create 4+ judge prompt configurations | Not Started | NESY-003-A |
| NESY-003-C | Implement JudgePanel class | Not Started | NESY-003-B |
| NESY-003-D | Implement verdict aggregation logic | Not Started | NESY-003-C |
| NESY-003-E | Add human escalation workflow | Not Started | NESY-003-D |
| NESY-003-F | Integrate with existing pipeline | Not Started | NESY-003-E |
| NESY-003-G | Add evaluation logging and metrics | Not Started | NESY-003-F |
| NESY-003-H | Write tests and documentation | Not Started | NESY-003-G |

---

## Phase 2: Medium-Term Enhancements

**Timeline:** 2-4 weeks per enhancement  
**Architectural Impact:** Moderate - new components with integration points  
**Dependencies:** Phase 1 completion recommended but not required

These enhancements add new capabilities that compound value over time through accumulated knowledge and formal verification.

---

### Enhancement 2.1: Knowledge Graph Layer for Research Outputs

**Task ID:** `NESY-004`  
**Category:** Knowledge  
**Priority:** High  
**Estimated Effort:** 40 hours

#### Objective

Implement a knowledge graph infrastructure that captures entities, relationships, and provenance from research agent outputs. This creates institutional memory that grows more valuable over time and enables provenance tracking for audit requirements.

#### Background and Rationale

Research outputs currently flow through the system and are consumed, but the knowledge they contain is not systematically captured for reuse. A knowledge graph stores information as entities connected by typed relationships, enabling queries like "what sources discuss both X and Y" or "trace this claim back to its original source."

Microsoft Research demonstrates that knowledge graph-enhanced RAG substantially outperforms vector-only retrieval for multi-hop reasoning and connecting information across documents. The graph structure provides explicit provenance chains that vector similarity cannot.

#### Implementation Specification

**Technology Selection:**

For development and small-scale deployment, use Neo4j (graph database with mature Python drivers and Cypher query language). For larger scale, consider Amazon Neptune or Azure Cosmos DB with Gremlin.

**Schema Design:**

```cypher
// Neo4j schema definition

// Entity types
CREATE CONSTRAINT claim_id IF NOT EXISTS FOR (c:Claim) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT source_url IF NOT EXISTS FOR (s:Source) REQUIRE s.url IS UNIQUE;
CREATE CONSTRAINT entity_key IF NOT EXISTS FOR (e:Entity) REQUIRE (e.name, e.type) IS UNIQUE;
CREATE CONSTRAINT topic_name IF NOT EXISTS FOR (t:Topic) REQUIRE t.name IS UNIQUE;
CREATE CONSTRAINT session_id IF NOT EXISTS FOR (se:Session) REQUIRE se.id IS UNIQUE;

// Indexes for common queries
CREATE INDEX claim_timestamp IF NOT EXISTS FOR (c:Claim) ON (c.created_at);
CREATE INDEX source_pub_date IF NOT EXISTS FOR (s:Source) ON (s.publication_date);
CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type);

// Vector index for semantic search
CALL db.index.vector.createNodeIndex(
    'claim_embeddings',
    'Claim',
    'embedding',
    384,  // Dimension for all-MiniLM-L6-v2
    'cosine'
);
```

**Python Implementation:**

```python
# File: src/knowledge/graph.py

from neo4j import GraphDatabase, Driver
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import uuid

@dataclass
class KGClaim:
    """Claim to be stored in knowledge graph."""
    text: str
    confidence: float
    source_url: str
    source_title: str
    publication_date: Optional[datetime]
    entities: List[Dict[str, str]]  # [{"name": "...", "type": "..."}]
    topics: List[str]
    agent_id: str
    session_id: str

@dataclass
class KGQueryResult:
    """Result from knowledge graph query."""
    claims: List[Dict[str, Any]]
    sources: List[Dict[str, Any]]
    related_entities: List[Dict[str, Any]]
    provenance_chain: List[Dict[str, Any]]

class ResearchKnowledgeGraph:
    """Knowledge graph for research output storage and retrieval."""
    
    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        self.driver: Driver = GraphDatabase.driver(uri, auth=(user, password))
        self.embedder = SentenceTransformer(embedding_model)
    
    def close(self):
        self.driver.close()
    
    def add_claim(self, claim: KGClaim) -> str:
        """Store a claim with full provenance and relationships."""
        
        claim_id = str(uuid.uuid4())
        embedding = self.embedder.encode(claim.text).tolist()
        
        with self.driver.session() as session:
            session.run("""
                // Create or merge source
                MERGE (source:Source {url: $source_url})
                SET source.title = $source_title,
                    source.publication_date = $pub_date,
                    source.last_accessed = datetime()
                
                // Create session if not exists
                MERGE (sess:Session {id: $session_id})
                SET sess.last_active = datetime()
                
                // Create claim
                CREATE (claim:Claim {
                    id: $claim_id,
                    text: $claim_text,
                    confidence: $confidence,
                    embedding: $embedding,
                    created_at: datetime(),
                    agent_id: $agent_id
                })
                
                // Link claim to source
                CREATE (claim)-[:SOURCED_FROM {
                    extraction_date: datetime(),
                    agent_id: $agent_id
                }]->(source)
                
                // Link claim to session
                CREATE (claim)-[:GENERATED_IN]->(sess)
                
                // Create and link entities
                WITH claim
                UNWIND $entities AS entity_data
                MERGE (e:Entity {name: entity_data.name, type: entity_data.type})
                CREATE (claim)-[:MENTIONS]->(e)
                
                // Create and link topics
                WITH claim
                UNWIND $topics AS topic_name
                MERGE (t:Topic {name: topic_name})
                CREATE (claim)-[:ABOUT]->(t)
            """,
                claim_id=claim_id,
                source_url=claim.source_url,
                source_title=claim.source_title,
                pub_date=claim.publication_date.isoformat() if claim.publication_date else None,
                session_id=claim.session_id,
                claim_text=claim.text,
                confidence=claim.confidence,
                embedding=embedding,
                agent_id=claim.agent_id,
                entities=claim.entities,
                topics=claim.topics
            )
        
        return claim_id
    
    def find_related_claims(
        self,
        query: str,
        max_hops: int = 2,
        min_confidence: float = 0.5,
        limit: int = 10
    ) -> KGQueryResult:
        """Find claims related by semantic similarity and entity co-occurrence."""
        
        query_embedding = self.embedder.encode(query).tolist()
        
        with self.driver.session() as session:
            result = session.run("""
                // Semantic search for similar claims
                CALL db.index.vector.queryNodes('claim_embeddings', $limit * 2, $embedding)
                YIELD node AS claim, score
                WHERE claim.confidence >= $min_confidence
                
                // Get source information
                MATCH (claim)-[:SOURCED_FROM]->(source:Source)
                
                // Get related claims through shared entities
                OPTIONAL MATCH path = (claim)-[:MENTIONS]->(:Entity)<-[:MENTIONS]-(related:Claim)
                WHERE related.id <> claim.id AND length(path) <= $max_hops * 2
                
                // Get entities mentioned
                OPTIONAL MATCH (claim)-[:MENTIONS]->(entity:Entity)
                
                RETURN 
                    claim.id AS claim_id,
                    claim.text AS claim_text,
                    claim.confidence AS confidence,
                    score AS similarity_score,
                    source.url AS source_url,
                    source.title AS source_title,
                    source.publication_date AS pub_date,
                    collect(DISTINCT related.id) AS related_claim_ids,
                    collect(DISTINCT {name: entity.name, type: entity.type}) AS entities
                ORDER BY score DESC
                LIMIT $limit
            """,
                embedding=query_embedding,
                limit=limit,
                min_confidence=min_confidence,
                max_hops=max_hops
            )
            
            claims = []
            sources = []
            entities_seen = set()
            all_entities = []
            
            for record in result:
                claims.append({
                    "id": record["claim_id"],
                    "text": record["claim_text"],
                    "confidence": record["confidence"],
                    "similarity": record["similarity_score"],
                    "related_claims": record["related_claim_ids"]
                })
                
                sources.append({
                    "url": record["source_url"],
                    "title": record["source_title"],
                    "publication_date": record["pub_date"]
                })
                
                for entity in record["entities"]:
                    key = (entity["name"], entity["type"])
                    if key not in entities_seen:
                        entities_seen.add(key)
                        all_entities.append(entity)
            
            return KGQueryResult(
                claims=claims,
                sources=sources,
                related_entities=all_entities,
                provenance_chain=[]  # Populated separately if needed
            )
    
    def get_provenance_chain(self, claim_id: str) -> List[Dict[str, Any]]:
        """Trace claim back to its sources."""
        
        with self.driver.session() as session:
            result = session.run("""
                MATCH (claim:Claim {id: $claim_id})
                MATCH path = (claim)-[:SOURCED_FROM|DERIVED_FROM*1..5]->(origin)
                RETURN 
                    [node IN nodes(path) | 
                        CASE 
                            WHEN node:Claim THEN {type: 'claim', id: node.id, text: node.text}
                            WHEN node:Source THEN {type: 'source', url: node.url, title: node.title}
                            ELSE {type: labels(node)[0], id: id(node)}
                        END
                    ] AS chain
                ORDER BY length(path)
            """, claim_id=claim_id)
            
            chains = [record["chain"] for record in result]
            return chains[0] if chains else []
    
    def find_contradictions(self, claim_id: str) -> List[Dict[str, Any]]:
        """Find claims that potentially contradict a given claim."""
        
        with self.driver.session() as session:
            # Get the claim and its embedding
            claim_result = session.run("""
                MATCH (c:Claim {id: $claim_id})
                RETURN c.text AS text, c.embedding AS embedding
            """, claim_id=claim_id)
            
            claim_data = claim_result.single()
            if not claim_data:
                return []
            
            # Find claims on same topic with different sources
            result = session.run("""
                MATCH (original:Claim {id: $claim_id})-[:ABOUT]->(topic:Topic)
                MATCH (other:Claim)-[:ABOUT]->(topic)
                WHERE other.id <> $claim_id
                
                // Get different source chains
                MATCH (original)-[:SOURCED_FROM]->(orig_source:Source)
                MATCH (other)-[:SOURCED_FROM]->(other_source:Source)
                WHERE orig_source.url <> other_source.url
                
                // Calculate semantic similarity (lower = more different = potential contradiction)
                WITH other, other_source,
                     gds.similarity.cosine($embedding, other.embedding) AS similarity
                WHERE similarity < 0.3  // Dissimilar claims on same topic
                
                RETURN 
                    other.id AS claim_id,
                    other.text AS claim_text,
                    other_source.url AS source_url,
                    similarity
                ORDER BY similarity ASC
                LIMIT 5
            """, 
                claim_id=claim_id,
                embedding=claim_data["embedding"]
            )
            
            return [dict(record) for record in result]
```

**Integration with Research Agents:**

```python
# File: src/agents/research_with_kg.py

class KGEnhancedResearchAgent:
    """Research agent with knowledge graph integration."""
    
    def __init__(self, base_agent, knowledge_graph: ResearchKnowledgeGraph):
        self.agent = base_agent
        self.kg = knowledge_graph
    
    async def research(self, query: str, session_id: str) -> ResearchOutput:
        # Check knowledge graph for existing knowledge
        existing = self.kg.find_related_claims(query, limit=5)
        
        context_from_kg = ""
        if existing.claims:
            context_from_kg = self._format_existing_knowledge(existing)
        
        # Augment query with existing knowledge
        augmented_query = f"""
{query}

EXISTING KNOWLEDGE (from previous research):
{context_from_kg if context_from_kg else "No directly relevant prior research found."}

Build upon existing knowledge where relevant. Avoid redundant research.
"""
        
        # Execute research
        output = await self.agent.research(augmented_query)
        
        # Store new findings in knowledge graph
        for claim in output.claims:
            kg_claim = KGClaim(
                text=claim.claim_text,
                confidence=claim.confidence,
                source_url=str(claim.sources[0].url),
                source_title=claim.sources[0].title,
                publication_date=claim.sources[0].publication_date,
                entities=self._extract_entities(claim.claim_text),
                topics=self._extract_topics(query),
                agent_id=output.agent_id,
                session_id=session_id
            )
            self.kg.add_claim(kg_claim)
        
        return output
```

#### Acceptance Criteria

1. Neo4j schema deployed with all node types and relationships
2. Python client library for graph operations implemented
3. Vector similarity search with cosine scoring functional
4. Provenance chain traversal returning complete paths
5. Integration with research agent pipeline for automatic storage
6. Query interface for finding related claims across sessions
7. Contradiction detection implemented and tested
8. Performance acceptable for interactive use (<500ms query time)

#### Subtasks

| Subtask ID | Description | Status | Dependencies |
|------------|-------------|--------|--------------|
| NESY-004-A | Design and document graph schema | Not Started | None |
| NESY-004-B | Set up Neo4j instance (dev/test) | Not Started | None |
| NESY-004-C | Implement ResearchKnowledgeGraph class | Not Started | NESY-004-A,B |
| NESY-004-D | Add vector index for semantic search | Not Started | NESY-004-C |
| NESY-004-E | Implement entity extraction for claims | Not Started | NESY-004-C |
| NESY-004-F | Implement provenance chain traversal | Not Started | NESY-004-C |
| NESY-004-G | Implement contradiction detection | Not Started | NESY-004-D |
| NESY-004-H | Create KGEnhancedResearchAgent wrapper | Not Started | NESY-004-C |
| NESY-004-I | Integration testing with research pipeline | Not Started | NESY-004-H |
| NESY-004-J | Performance optimization and benchmarking | Not Started | NESY-004-I |
| NESY-004-K | Documentation and usage examples | Not Started | NESY-004-J |

---

### Enhancement 2.2: Symbolic Constraint Solver Integration (Z3)

**Task ID:** `NESY-005`  
**Category:** Verification  
**Priority:** Medium  
**Estimated Effort:** 32 hours

#### Objective

Integrate the Z3 theorem prover to provide formal verification of claims with logical or mathematical structure. This complements LLM-based evaluation with provably correct verification for appropriate claim types.

#### Background and Rationale

LLM judges evaluate quality heuristically and can miss logical errors, particularly in arithmetic, constraint satisfaction, and formal reasoning. Z3 is a Satisfiability Modulo Theories (SMT) solver that can definitively verify or refute logical claims. For appropriate claim types, this provides certainty rather than probability.

Amazon's Automated Reasoning Group uses similar techniques in production, achieving 96% correctness within 3 iterations for code verification tasks.

#### Implementation Specification

```python
# File: src/verification/symbolic_solver.py

from z3 import (
    Solver, Int, Real, Bool, String,
    And, Or, Not, Implies, If,
    sat, unsat, unknown,
    ForAll, Exists
)
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

class VerificationResult(Enum):
    VERIFIED = "verified"
    REFUTED = "refuted"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"

@dataclass
class SymbolicVerificationOutput:
    """Result of symbolic verification."""
    result: VerificationResult
    explanation: str
    counterexample: Optional[Dict[str, Any]] = None
    proof_steps: Optional[List[str]] = None
    verification_time_ms: int = 0

class SymbolicVerifier:
    """Formal verification using Z3 theorem prover."""
    
    def __init__(self, timeout_ms: int = 5000):
        self.timeout_ms = timeout_ms
    
    def verify_arithmetic(
        self,
        values: Dict[str, float],
        claimed_result: float,
        operation: str,
        tolerance: float = 0.001
    ) -> SymbolicVerificationOutput:
        """
        Verify arithmetic claims.
        
        Example:
            values = {"total": 50000, "spent": 42000}
            claimed_result = 10000
            operation = "total - spent"
            -> REFUTED: actual result is 8000
        """
        s = Solver()
        s.set("timeout", self.timeout_ms)
        
        # Create Z3 variables for each value
        z3_vars = {name: Real(name) for name in values}
        
        # Constrain to given values
        for name, value in values.items():
            s.add(z3_vars[name] == value)
        
        # Parse and evaluate operation
        try:
            actual_result = eval(operation, {"__builtins__": {}}, values)
        except Exception as e:
            return SymbolicVerificationOutput(
                result=VerificationResult.NOT_APPLICABLE,
                explanation=f"Could not evaluate operation: {e}"
            )
        
        # Check if claimed result matches
        if abs(actual_result - claimed_result) <= tolerance:
            return SymbolicVerificationOutput(
                result=VerificationResult.VERIFIED,
                explanation=f"Arithmetic verified: {operation} = {actual_result}"
            )
        else:
            return SymbolicVerificationOutput(
                result=VerificationResult.REFUTED,
                explanation=f"Arithmetic error: {operation} = {actual_result}, not {claimed_result}",
                counterexample={"expected": claimed_result, "actual": actual_result}
            )
    
    def verify_constraints(
        self,
        constraints: List[str],
        variable_types: Dict[str, str],  # "int", "real", "bool"
        should_be_satisfiable: bool = True
    ) -> SymbolicVerificationOutput:
        """
        Verify that a set of constraints is satisfiable (or unsatisfiable).
        
        Example:
            constraints = ["x > 0", "x < 0"]
            variable_types = {"x": "real"}
            should_be_satisfiable = True
            -> REFUTED: constraints are unsatisfiable
        """
        s = Solver()
        s.set("timeout", self.timeout_ms)
        
        # Create typed Z3 variables
        z3_vars = {}
        for name, vtype in variable_types.items():
            if vtype == "int":
                z3_vars[name] = Int(name)
            elif vtype == "real":
                z3_vars[name] = Real(name)
            elif vtype == "bool":
                z3_vars[name] = Bool(name)
        
        # Parse and add constraints
        for constraint in constraints:
            try:
                z3_constraint = self._parse_constraint(constraint, z3_vars)
                s.add(z3_constraint)
            except Exception as e:
                return SymbolicVerificationOutput(
                    result=VerificationResult.NOT_APPLICABLE,
                    explanation=f"Could not parse constraint '{constraint}': {e}"
                )
        
        # Check satisfiability
        result = s.check()
        
        if result == sat:
            if should_be_satisfiable:
                model = s.model()
                satisfying_assignment = {
                    str(d): str(model[d]) for d in model.decls()
                }
                return SymbolicVerificationOutput(
                    result=VerificationResult.VERIFIED,
                    explanation="Constraints are satisfiable",
                    counterexample=satisfying_assignment  # Not really a counterexample, but useful info
                )
            else:
                model = s.model()
                return SymbolicVerificationOutput(
                    result=VerificationResult.REFUTED,
                    explanation="Constraints should be unsatisfiable but are satisfiable",
                    counterexample={str(d): str(model[d]) for d in model.decls()}
                )
        
        elif result == unsat:
            if not should_be_satisfiable:
                return SymbolicVerificationOutput(
                    result=VerificationResult.VERIFIED,
                    explanation="Correctly identified as unsatisfiable"
                )
            else:
                return SymbolicVerificationOutput(
                    result=VerificationResult.REFUTED,
                    explanation="Constraints are unsatisfiable but were claimed to be satisfiable"
                )
        
        else:  # unknown
            return SymbolicVerificationOutput(
                result=VerificationResult.UNKNOWN,
                explanation=f"Could not determine satisfiability within {self.timeout_ms}ms"
            )
    
    def verify_implication(
        self,
        premises: List[str],
        conclusion: str,
        variable_types: Dict[str, str]
    ) -> SymbolicVerificationOutput:
        """
        Verify that premises logically imply conclusion.
        
        Example:
            premises = ["x > 5", "y = x + 1"]
            conclusion = "y > 5"
            -> VERIFIED: conclusion follows from premises
        """
        s = Solver()
        s.set("timeout", self.timeout_ms)
        
        # Create variables
        z3_vars = {}
        for name, vtype in variable_types.items():
            if vtype == "int":
                z3_vars[name] = Int(name)
            elif vtype == "real":
                z3_vars[name] = Real(name)
            elif vtype == "bool":
                z3_vars[name] = Bool(name)
        
        # Add premises
        for premise in premises:
            s.add(self._parse_constraint(premise, z3_vars))
        
        # Add negation of conclusion - if unsatisfiable, implication holds
        s.add(Not(self._parse_constraint(conclusion, z3_vars)))
        
        result = s.check()
        
        if result == unsat:
            return SymbolicVerificationOutput(
                result=VerificationResult.VERIFIED,
                explanation=f"Conclusion '{conclusion}' follows from premises"
            )
        elif result == sat:
            model = s.model()
            return SymbolicVerificationOutput(
                result=VerificationResult.REFUTED,
                explanation=f"Conclusion does not follow from premises",
                counterexample={str(d): str(model[d]) for d in model.decls()}
            )
        else:
            return SymbolicVerificationOutput(
                result=VerificationResult.UNKNOWN,
                explanation="Could not verify implication"
            )
    
    def _parse_constraint(self, constraint: str, variables: Dict) -> Any:
        """Parse constraint string to Z3 expression."""
        # Safe evaluation with Z3 operations
        safe_dict = {
            "And": And, "Or": Or, "Not": Not,
            "Implies": Implies, "If": If,
            **variables
        }
        return eval(constraint, {"__builtins__": {}}, safe_dict)


class HybridVerifier:
    """Combines LLM judges with symbolic verification."""
    
    def __init__(self, llm_judge, symbolic_verifier: SymbolicVerifier):
        self.llm = llm_judge
        self.symbolic = symbolic_verifier
        self.claim_classifiers = self._init_classifiers()
    
    def _init_classifiers(self) -> Dict:
        """Initialize claim type classifiers."""
        return {
            "arithmetic": self._is_arithmetic_claim,
            "constraint": self._is_constraint_claim,
            "implication": self._is_implication_claim
        }
    
    async def verify(
        self,
        content: str,
        claims: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Verify content using appropriate method for each claim type.
        """
        results = []
        
        for claim in claims:
            claim_type = self._classify_claim(claim)
            
            if claim_type == "arithmetic":
                # Use symbolic verification
                sym_result = self._verify_arithmetic_claim(claim)
                if sym_result.result != VerificationResult.NOT_APPLICABLE:
                    results.append({
                        "claim": claim,
                        "method": "symbolic",
                        "result": sym_result
                    })
                    continue
            
            elif claim_type == "constraint":
                sym_result = self._verify_constraint_claim(claim)
                if sym_result.result != VerificationResult.NOT_APPLICABLE:
                    results.append({
                        "claim": claim,
                        "method": "symbolic",
                        "result": sym_result
                    })
                    continue
            
            # Fall back to LLM verification
            llm_result = await self.llm.evaluate(claim, context)
            results.append({
                "claim": claim,
                "method": "llm",
                "result": llm_result
            })
        
        return {
            "verified_claims": [r for r in results if r["result"].result == VerificationResult.VERIFIED],
            "refuted_claims": [r for r in results if r["result"].result == VerificationResult.REFUTED],
            "uncertain_claims": [r for r in results if r["result"].result in [VerificationResult.UNKNOWN, VerificationResult.NOT_APPLICABLE]],
            "symbolic_verification_count": sum(1 for r in results if r["method"] == "symbolic"),
            "llm_verification_count": sum(1 for r in results if r["method"] == "llm")
        }
```

#### Acceptance Criteria

1. SymbolicVerifier class implemented with arithmetic, constraint, and implication verification
2. Claim type classification for routing to appropriate verification method
3. HybridVerifier combining symbolic and LLM approaches
4. Graceful fallback when symbolic verification is not applicable
5. Performance acceptable for interactive use (<1s for typical claims)
6. Test suite covering common claim patterns
7. Documentation with usage examples

#### Subtasks

| Subtask ID | Description | Status | Dependencies |
|------------|-------------|--------|--------------|
| NESY-005-A | Implement arithmetic verification | Not Started | None |
| NESY-005-B | Implement constraint satisfiability verification | Not Started | None |
| NESY-005-C | Implement logical implication verification | Not Started | None |
| NESY-005-D | Create claim type classifier | Not Started | None |
| NESY-005-E | Implement HybridVerifier class | Not Started | NESY-005-A,B,C,D |
| NESY-005-F | Add constraint parsing utilities | Not Started | NESY-005-A,B,C |
| NESY-005-G | Integration with judge pipeline | Not Started | NESY-005-E |
| NESY-005-H | Test suite for verification patterns | Not Started | NESY-005-E |
| NESY-005-I | Documentation | Not Started | NESY-005-H |

---

### Enhancement 2.3: Explicit Progress Ledgers

**Task ID:** `NESY-006`  
**Category:** Orchestration  
**Priority:** Medium  
**Estimated Effort:** 24 hours

#### Objective

Implement explicit progress tracking structures that agents update during execution. This enables detection of stalled tasks, circular reasoning, and provides visibility into agent work that would otherwise be opaque.

#### Background and Rationale

The MAST framework identifies 14 distinct failure modes in multi-agent systems, with many stemming from loss of context across agent handoffs, step repetition, and premature termination. Explicit progress ledgers address these by maintaining structured state that persists across interactions.

Microsoft's Magentic-One architecture uses "Task Ledger" and "Progress Ledger" structures that agents update, enabling detection of lack of progress. This pattern should be adopted for robust orchestration.

#### Implementation Specification

Refer to the Progress Ledger Schema section at the beginning of this document for the core data structures. The following additions provide runtime tracking and integration.

```python
# File: src/ledger/runtime_tracker.py

from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
import asyncio
from .task_ledger import TaskLedger, ProgressEntry, TaskStatus, LedgerManager

@dataclass
class RuntimeMetrics:
    """Real-time execution metrics."""
    active_tasks: int
    completed_tasks_last_hour: int
    blocked_tasks: int
    average_completion_time: timedelta
    loop_detections: int
    human_escalations: int

class RuntimeLedgerTracker:
    """Real-time tracking and monitoring of ledger state."""
    
    def __init__(
        self,
        ledger: LedgerManager,
        stale_threshold: timedelta = timedelta(minutes=30),
        on_stale_detected: Optional[Callable] = None,
        on_loop_detected: Optional[Callable] = None
    ):
        self.ledger = ledger
        self.stale_threshold = stale_threshold
        self.on_stale_detected = on_stale_detected
        self.on_loop_detected = on_loop_detected
        self._monitoring = False
    
    async def start_monitoring(self, check_interval: int = 60):
        """Begin background monitoring for issues."""
        self._monitoring = True
        
        while self._monitoring:
            await self._check_for_issues()
            await asyncio.sleep(check_interval)
    
    def stop_monitoring(self):
        """Stop background monitoring."""
        self._monitoring = False
    
    async def _check_for_issues(self):
        """Check for stale tasks and other issues."""
        now = datetime.utcnow()
        
        for task_id, task in self.ledger.tasks.items():
            if task.status != TaskStatus.IN_PROGRESS:
                continue
            
            # Check for stale tasks
            if now - task.updated_at > self.stale_threshold:
                if self.on_stale_detected:
                    await self.on_stale_detected(task)
            
            # Check for loops (handled in add_progress, but verify)
            if task.status == TaskStatus.BLOCKED:
                if "Loop detected" in task.notes:
                    if self.on_loop_detected:
                        await self.on_loop_detected(task)
    
    def get_metrics(self) -> RuntimeMetrics:
        """Calculate current runtime metrics."""
        now = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)
        
        tasks = list(self.ledger.tasks.values())
        
        active = [t for t in tasks if t.status == TaskStatus.IN_PROGRESS]
        completed_recent = [
            t for t in tasks 
            if t.status == TaskStatus.COMPLETED and t.updated_at > one_hour_ago
        ]
        blocked = [t for t in tasks if t.status == TaskStatus.BLOCKED]
        
        # Calculate average completion time
        completed_with_time = [
            t for t in tasks 
            if t.status == TaskStatus.COMPLETED and t.created_at and t.updated_at
        ]
        if completed_with_time:
            avg_time = sum(
                (t.updated_at - t.created_at).total_seconds() 
                for t in completed_with_time
            ) / len(completed_with_time)
            avg_completion = timedelta(seconds=avg_time)
        else:
            avg_completion = timedelta(0)
        
        loop_detections = sum(
            1 for t in tasks if "Loop detected" in t.notes
        )
        
        escalations = sum(
            1 for t in tasks 
            if any("escalate" in e.action_taken.lower() for e in t.progress_history)
        )
        
        return RuntimeMetrics(
            active_tasks=len(active),
            completed_tasks_last_hour=len(completed_recent),
            blocked_tasks=len(blocked),
            average_completion_time=avg_completion,
            loop_detections=loop_detections,
            human_escalations=escalations
        )
    
    def generate_dashboard_data(self) -> Dict[str, Any]:
        """Generate data for dashboard display."""
        metrics = self.get_metrics()
        
        by_phase = {}
        for phase in ["immediate", "medium_term", "long_term"]:
            by_phase[phase] = self.ledger.get_phase_summary(phase)
        
        recent_activity = []
        all_entries = []
        for task in self.ledger.tasks.values():
            for entry in task.progress_history:
                all_entries.append((task.task_id, entry))
        
        all_entries.sort(key=lambda x: x[1].timestamp, reverse=True)
        recent_activity = [
            {
                "task_id": tid,
                "timestamp": entry.timestamp.isoformat(),
                "agent": entry.agent_id,
                "action": entry.action_taken,
                "outcome": entry.outcome
            }
            for tid, entry in all_entries[:20]
        ]
        
        return {
            "metrics": {
                "active": metrics.active_tasks,
                "completed_hour": metrics.completed_tasks_last_hour,
                "blocked": metrics.blocked_tasks,
                "avg_completion_sec": metrics.average_completion_time.total_seconds(),
                "loops_detected": metrics.loop_detections,
                "escalations": metrics.human_escalations
            },
            "by_phase": by_phase,
            "recent_activity": recent_activity,
            "generated_at": datetime.utcnow().isoformat()
        }
```

```python
# File: src/orchestration/ledger_aware_orchestrator.py

class LedgerAwareOrchestrator:
    """Orchestrator with integrated progress tracking."""
    
    def __init__(
        self,
        agents: Dict[str, Agent],
        ledger: LedgerManager,
        max_retries: int = 3
    ):
        self.agents = agents
        self.ledger = ledger
        self.max_retries = max_retries
    
    async def execute_task(self, task_id: str) -> Any:
        """Execute task with full ledger tracking."""
        
        task = self.ledger.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        task.status = TaskStatus.IN_PROGRESS
        agent = self.agents.get(task.assigned_agent)
        
        for attempt in range(self.max_retries):
            try:
                result = await agent.execute(task.objective)
                
                # Record success
                task.add_progress(ProgressEntry(
                    timestamp=datetime.utcnow(),
                    agent_id=agent.id,
                    action_taken=f"Attempt {attempt + 1}: Execute {task.objective[:50]}...",
                    outcome="success",
                    artifacts_produced=result.get("artifacts", []),
                    next_steps=[]
                ))
                
                task.status = TaskStatus.COMPLETED
                task.artifacts = result.get("artifacts", [])
                return result
                
            except Exception as e:
                # Record failure
                task.add_progress(ProgressEntry(
                    timestamp=datetime.utcnow(),
                    agent_id=agent.id,
                    action_taken=f"Attempt {attempt + 1}: Execute {task.objective[:50]}...",
                    outcome=f"failed: {str(e)}",
                    blockers_encountered=[str(e)],
                    next_steps=["retry" if attempt < self.max_retries - 1 else "escalate"]
                ))
                
                if task.status == TaskStatus.BLOCKED:
                    # Loop detected during add_progress
                    await self._handle_blocked_task(task)
                    return None
        
        # Max retries exhausted
        task.status = TaskStatus.BLOCKED
        task.notes += f"\n[{datetime.utcnow()}] Max retries ({self.max_retries}) exhausted"
        await self._handle_blocked_task(task)
        return None
    
    async def _handle_blocked_task(self, task: TaskLedger):
        """Handle a blocked task - escalate or try alternative approach."""
        # Log for human review
        print(f"BLOCKED: Task {task.task_id} - {task.objective[:50]}...")
        print(f"  Notes: {task.notes}")
        print(f"  History: {len(task.progress_history)} entries")
        
        # Could trigger notification, create ticket, etc.
```

#### Acceptance Criteria

1. Progress entry creation and storage functional
2. Loop detection triggering after 4 similar action-outcome pairs
3. Real-time metrics calculation accurate
4. Dashboard data generation for UI integration
5. Stale task detection with configurable thresholds
6. Integration with orchestrator for automatic tracking
7. Persistence across sessions

#### Subtasks

| Subtask ID | Description | Status | Dependencies |
|------------|-------------|--------|--------------|
| NESY-006-A | Implement ProgressEntry and TaskLedger classes | Not Started | None |
| NESY-006-B | Implement LedgerManager with persistence | Not Started | NESY-006-A |
| NESY-006-C | Add loop detection logic | Not Started | NESY-006-A |
| NESY-006-D | Implement RuntimeLedgerTracker | Not Started | NESY-006-B |
| NESY-006-E | Create dashboard data generation | Not Started | NESY-006-D |
| NESY-006-F | Implement LedgerAwareOrchestrator | Not Started | NESY-006-B |
| NESY-006-G | Add persistence layer (file or database) | Not Started | NESY-006-B |
| NESY-006-H | Integration testing | Not Started | NESY-006-F |
| NESY-006-I | Documentation | Not Started | NESY-006-H |

---

## Phase 3: Long-Term Evolution

**Timeline:** 4-8 weeks per enhancement  
**Architectural Impact:** Significant - new paradigms and infrastructure  
**Dependencies:** Phases 1-2 provide foundation

These enhancements position the system at the research frontier of neuro-symbolic AI for multi-agent orchestration.

---

### Enhancement 3.1: Formal Specification Language for Agent Behavior

**Task ID:** `NESY-007`  
**Category:** Specification  
**Priority:** Medium  
**Estimated Effort:** 60 hours

#### Objective

Develop a domain-specific language for specifying agent behavior constraints that can be both validated symbolically and used to guide generation. This separates the "what" (specifications) from the "how" (implementation), enabling formal reasoning about agent behavior.

#### Background and Rationale

Current agent constraints are expressed in natural language prompts, which LLMs interpret probabilistically. A formal specification language allows constraints to be verified symbolically (using Z3 or similar), enforced at runtime, and used to generate compliant outputs.

This approach follows the design philosophy of "design by contract" from software engineering, adapted for LLM agents.

#### Implementation Specification

**Specification Language Grammar:**

```ebnf
(* Agent Specification Grammar *)

specification     = "AGENT" identifier ":" agent_body ;

agent_body        = tier_decl tools_decl output_spec behavior_spec limits_spec ;

tier_decl         = "TIER:" tier_name ;
tier_name         = "opus" | "sonnet" | "haiku" ;

tools_decl        = "TOOLS:" "[" tool_list "]" ;
tool_list         = identifier { "," identifier } ;

output_spec       = "OUTPUT" "MUST" "SATISFY:" constraint_list ;
constraint_list   = constraint { constraint } ;

constraint        = quantified_constraint | simple_constraint ;

quantified_constraint = ("forall" | "exists") identifier "in" path ":" constraint ;

simple_constraint = path comparator value
                  | path "IS" type_check
                  | path "IN" "RANGE" "[" number "," number "]"
                  | path "IN" "[" value_list "]"
                  | "if" condition ":" constraint ;

behavior_spec     = "BEHAVIOR:" behavior_list ;
behavior_list     = behavior_rule { behavior_rule } ;
behavior_rule     = "PREFER" value "OVER" value
                  | "NEVER" action
                  | "ALWAYS" action
                  | "WHEN" condition action ;

limits_spec       = "LIMITS:" limit_list ;
limit_list        = limit_decl { limit_decl } ;
limit_decl        = identifier ":" number ;

path              = identifier { "." identifier } ;
comparator        = "==" | "!=" | "<" | ">" | "<=" | ">=" ;
```

**Example Specifications:**

```
# File: specs/research_agent.spec

AGENT ResearchAgent:
    TIER: haiku
    TOOLS: [WebSearch, WebFetch, Read, Grep]
    
    OUTPUT MUST SATISFY:
        forall claim in output.claims:
            exists source in claim.sources:
                source.url IS VALID_URL
                source.accessed_date <= TODAY
                source.publication_date >= TODAY - 180 DAYS
        
        output.confidence IN RANGE [0.0, 1.0]
        
        if count(claim.sources) == 1:
            claim.verification_status == "single_source"
        
        if any(source.publication_date < TODAY - 90 DAYS for source in claim.sources):
            "recency_warning" IN output.flags
    
    BEHAVIOR:
        PREFER primary_sources OVER secondary_sources
        NEVER include claims WHERE confidence < 0.3
        ALWAYS flag contradictions BETWEEN sources
        WHEN topic IS "medical": ALWAYS include disclaimer
    
    LIMITS:
        max_search_queries: 10
        max_fetch_requests: 20
        timeout_seconds: 300
```

```python
# File: src/specifications/compiler.py

from lark import Lark, Transformer, v_args
from typing import Dict, Any, List, Callable
from dataclasses import dataclass
from z3 import Solver, And, Or, Not, ForAll, Exists

@dataclass
class CompiledSpecification:
    """Compiled agent specification."""
    agent_name: str
    tier: str
    tools: List[str]
    output_validators: List[Callable]
    z3_constraints: List[Any]
    behavior_prompt_additions: str
    runtime_limits: Dict[str, int]

class SpecificationCompiler:
    """Compiles specification DSL to executable components."""
    
    def __init__(self):
        self.grammar = self._load_grammar()
        self.parser = Lark(self.grammar, start='specification')
    
    def compile(self, spec_text: str) -> CompiledSpecification:
        """Parse and compile specification."""
        tree = self.parser.parse(spec_text)
        return SpecificationTransformer().transform(tree)
    
    def _load_grammar(self) -> str:
        # Load EBNF grammar
        pass


class SpecificationEnforcedAgent:
    """Agent wrapper enforcing formal specifications."""
    
    def __init__(self, base_agent, spec: CompiledSpecification):
        self.agent = base_agent
        self.spec = spec
    
    async def execute(self, task: str) -> Dict[str, Any]:
        """Execute with specification enforcement."""
        
        # Add behavioral guidelines to prompt
        augmented_prompt = f"""
{self.spec.behavior_prompt_additions}

TASK:
{task}
"""
        
        # Apply runtime limits
        with self._enforce_limits():
            output = await self.agent.execute(augmented_prompt)
        
        # Validate output against specifications
        for validator in self.spec.output_validators:
            result = validator(output)
            if not result.valid:
                raise SpecificationViolation(
                    spec=self.spec.agent_name,
                    violation=result.errors
                )
        
        return output
```

#### Acceptance Criteria

1. Grammar definition complete and parseable
2. Compiler translates specs to validators and constraints
3. Z3 integration for formal constraint checking
4. Prompt generation from behavioral rules
5. Runtime limit enforcement
6. Specification violation reporting with specifics
7. Example specifications for all agent types
8. Documentation and usage guide

#### Subtasks

| Subtask ID | Description | Status | Dependencies |
|------------|-------------|--------|--------------|
| NESY-007-A | Design specification language grammar | Not Started | None |
| NESY-007-B | Implement parser using Lark | Not Started | NESY-007-A |
| NESY-007-C | Implement constraint compilation to validators | Not Started | NESY-007-B |
| NESY-007-D | Implement Z3 constraint generation | Not Started | NESY-007-B, NESY-005 |
| NESY-007-E | Implement behavior-to-prompt transformation | Not Started | NESY-007-B |
| NESY-007-F | Create SpecificationEnforcedAgent wrapper | Not Started | NESY-007-C,D,E |
| NESY-007-G | Write specifications for all agents | Not Started | NESY-007-F |
| NESY-007-H | Integration testing | Not Started | NESY-007-G |
| NESY-007-I | Documentation and examples | Not Started | NESY-007-H |

---

### Enhancement 3.2: Neurosymbolic Learning Cycle

**Task ID:** `NESY-008`  
**Category:** Learning  
**Priority:** Low  
**Estimated Effort:** 80 hours

#### Objective

Implement a learning system that extracts symbolic rules from successful agent executions, stores them as structured knowledge, and uses them to improve future performance. This creates a feedback loop where the system gets smarter over time without explicit retraining.

#### Background and Rationale

The neurosymbolic cycle is a training approach from the academic literature where symbolic knowledge is extracted from neural network outputs and then used to guide future behavior. For a multi-agent system, this means capturing successful patterns as reusable rules.

This is particularly valuable for domain-specific knowledge that isn't well-represented in base model training, enabling the system to accumulate expertise over time.

#### Implementation Specification

```python
# File: src/learning/rule_extraction.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from anthropic import Anthropic

@dataclass
class ExtractedRule:
    """Rule extracted from successful execution."""
    id: str
    condition: str  # When to apply
    recommendation: str  # What to do
    reasoning: str  # Why it works
    confidence: float
    success_count: int = 1
    failure_count: int = 0
    source_task: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None
    
    @property
    def effectiveness(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else self.confidence

@dataclass
class ExecutionOutcome:
    """Outcome of an agent execution."""
    task: str
    approach: str
    success: bool
    quality_score: float
    execution_time: float
    artifacts: List[str]
    feedback: Optional[str] = None

class RuleExtractor:
    """Extracts generalizable rules from successful executions."""
    
    def __init__(self, client: Anthropic, model: str = "claude-sonnet-4-20250514"):
        self.client = client
        self.model = model
    
    async def extract_rules(
        self,
        task: str,
        approach: str,
        outcome: ExecutionOutcome
    ) -> List[ExtractedRule]:
        """Extract rules from a successful execution."""
        
        if not outcome.success or outcome.quality_score < 0.7:
            return []  # Only learn from good outcomes
        
        extraction_prompt = f"""
Analyze this successful task execution and extract generalizable rules.

TASK: {task}

APPROACH TAKEN: {approach}

OUTCOME:
- Success: {outcome.success}
- Quality Score: {outcome.quality_score}
- Feedback: {outcome.feedback or 'None'}

Extract rules that would help with similar future tasks.
For each rule, provide:

1. CONDITION: When should this rule apply? Be specific about task characteristics.
2. RECOMMENDATION: What approach should be taken?
3. REASONING: Why does this work?

Only extract rules that are:
- Generalizable (not just for this specific task)
- Actionable (can be applied by an agent)
- Non-obvious (add value beyond basic instructions)

Format as JSON array:
[
    {{
        "condition": "When [specific conditions]...",
        "recommendation": "Do [specific action]...",
        "reasoning": "Because [explanation]..."
    }}
]
"""
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            messages=[{"role": "user", "content": extraction_prompt}]
        )
        
        return self._parse_rules(response.content[0].text, task)


class RuleStore:
    """Persistent storage for extracted rules."""
    
    def __init__(self, storage_path: str = "./rules_db"):
        self.storage_path = storage_path
        self.rules: Dict[str, ExtractedRule] = {}
        self._load()
    
    def add(self, rule: ExtractedRule) -> None:
        """Add or update rule."""
        # Check for similar existing rules
        similar = self._find_similar(rule)
        if similar:
            # Merge with existing rule
            similar.success_count += 1
            similar.confidence = min(1.0, similar.confidence * 1.1)
        else:
            self.rules[rule.id] = rule
        self._save()
    
    def search(self, query: str, limit: int = 5) -> List[ExtractedRule]:
        """Find rules relevant to a query."""
        # Simple keyword matching - could use embeddings for better matching
        scored = []
        query_lower = query.lower()
        
        for rule in self.rules.values():
            score = 0
            condition_lower = rule.condition.lower()
            
            # Keyword overlap scoring
            query_words = set(query_lower.split())
            condition_words = set(condition_lower.split())
            overlap = len(query_words & condition_words)
            score += overlap * 0.5
            
            # Effectiveness weighting
            score *= rule.effectiveness
            
            scored.append((rule, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return [r for r, s in scored[:limit] if s > 0.1]
    
    def update_effectiveness(self, rule_id: str, success: bool) -> None:
        """Update rule based on new outcome."""
        if rule_id not in self.rules:
            return
        
        rule = self.rules[rule_id]
        if success:
            rule.success_count += 1
        else:
            rule.failure_count += 1
        
        rule.last_used = datetime.utcnow()
        self._save()


class LearningOrchestrator:
    """Orchestrator with neurosymbolic learning."""
    
    def __init__(
        self,
        agents: Dict[str, Any],
        rule_extractor: RuleExtractor,
        rule_store: RuleStore
    ):
        self.agents = agents
        self.extractor = rule_extractor
        self.rules = rule_store
    
    async def execute_with_learning(
        self,
        task: str,
        agent_id: str
    ) -> Dict[str, Any]:
        """Execute task with rule application and learning."""
        
        # Retrieve applicable rules
        applicable_rules = self.rules.search(task, limit=3)
        
        # Build context from rules
        rule_context = ""
        if applicable_rules:
            rule_lines = []
            for rule in applicable_rules:
                rule_lines.append(
                    f"- When {rule.condition}: {rule.recommendation} "
                    f"(effectiveness: {rule.effectiveness:.0%})"
                )
            rule_context = f"""
LEARNED PATTERNS (from past successful executions):
{chr(10).join(rule_lines)}

Apply these patterns where relevant.
"""
        
        # Execute with augmented context
        agent = self.agents[agent_id]
        augmented_task = f"{rule_context}\n\nTASK:\n{task}"
        
        result = await agent.execute(augmented_task)
        
        # Evaluate outcome
        outcome = ExecutionOutcome(
            task=task,
            approach=result.get("approach", "unknown"),
            success=result.get("success", False),
            quality_score=result.get("quality_score", 0.5),
            execution_time=result.get("execution_time", 0),
            artifacts=result.get("artifacts", [])
        )
        
        # Update rule effectiveness
        for rule in applicable_rules:
            self.rules.update_effectiveness(rule.id, outcome.success)
        
        # Extract new rules from successful executions
        if outcome.success and outcome.quality_score >= 0.8:
            new_rules = await self.extractor.extract_rules(
                task=task,
                approach=outcome.approach,
                outcome=outcome
            )
            for rule in new_rules:
                self.rules.add(rule)
        
        return result
```

#### Acceptance Criteria

1. Rule extraction from successful executions functional
2. Rule storage with persistence across sessions
3. Semantic search for applicable rules
4. Effectiveness tracking with Bayesian updates
5. Rule pruning for low-effectiveness rules
6. Integration with orchestrator for automatic learning
7. Dashboard visibility into learned rules
8. Export/import capability for rule sharing

#### Subtasks

| Subtask ID | Description | Status | Dependencies |
|------------|-------------|--------|--------------|
| NESY-008-A | Design ExtractedRule data model | Not Started | None |
| NESY-008-B | Implement RuleExtractor with LLM | Not Started | NESY-008-A |
| NESY-008-C | Implement RuleStore with persistence | Not Started | NESY-008-A |
| NESY-008-D | Add semantic search for rule retrieval | Not Started | NESY-008-C |
| NESY-008-E | Implement effectiveness tracking | Not Started | NESY-008-C |
| NESY-008-F | Create LearningOrchestrator | Not Started | NESY-008-B,C,D,E |
| NESY-008-G | Add rule pruning mechanism | Not Started | NESY-008-E |
| NESY-008-H | Dashboard integration | Not Started | NESY-008-F |
| NESY-008-I | Export/import functionality | Not Started | NESY-008-C |
| NESY-008-J | Integration testing | Not Started | NESY-008-F |
| NESY-008-K | Documentation | Not Started | NESY-008-J |

---

### Enhancement 3.3: Enterprise Audit Trail Infrastructure

**Task ID:** `NESY-009`  
**Category:** Audit  
**Priority:** Medium  
**Estimated Effort:** 48 hours

#### Objective

Implement comprehensive audit trail infrastructure that records every decision with full context, provenance, and tamper-evident integrity. This meets enterprise compliance requirements and enables post-hoc analysis of system behavior.

#### Background and Rationale

For regulated industries (finance, healthcare, legal), audit trails are mandatory. Even for non-regulated domains, comprehensive logging enables debugging, accountability, and continuous improvement. The design follows patterns from financial services (14-field compliance schema) and healthcare (audit requirements for clinical AI).

#### Implementation Specification

```python
# File: src/audit/trail.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum
import hashlib
import json
import uuid

class DecisionType(Enum):
    TASK_ROUTING = "task_routing"
    AGENT_SELECTION = "agent_selection"
    TOOL_INVOCATION = "tool_invocation"
    OUTPUT_GENERATION = "output_generation"
    VERIFICATION = "verification"
    HUMAN_ESCALATION = "human_escalation"
    RULE_APPLICATION = "rule_application"
    ERROR_HANDLING = "error_handling"

@dataclass
class AuditEntry:
    """Complete audit record for a decision point."""
    
    # Identity
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    session_id: str = ""
    conversation_id: str = ""
    
    # Decision context
    decision_type: DecisionType = DecisionType.OUTPUT_GENERATION
    agent_id: str = ""
    model_name: str = ""
    model_version: str = ""
    
    # Inputs (hashed for privacy, summarized for readability)
    input_hash: str = ""
    input_summary: str = ""
    input_token_count: int = 0
    context_sources: List[str] = field(default_factory=list)
    
    # Decision process
    reasoning_summary: str = ""
    alternatives_considered: List[Dict[str, Any]] = field(default_factory=list)
    selected_action: str = ""
    confidence_score: float = 0.0
    rules_applied: List[str] = field(default_factory=list)
    
    # Outputs
    output_hash: str = ""
    output_summary: str = ""
    output_token_count: int = 0
    
    # Verification
    verification_status: str = "pending"
    verifier_ids: List[str] = field(default_factory=list)
    verification_scores: Dict[str, float] = field(default_factory=dict)
    
    # Provenance
    source_documents: List[str] = field(default_factory=list)
    parent_entry_id: Optional[str] = None
    child_entry_ids: List[str] = field(default_factory=list)
    
    # Chain integrity
    previous_entry_hash: str = ""
    entry_hash: str = ""
    
    def compute_hash(self) -> str:
        """Compute tamper-evident hash."""
        content = json.dumps({
            "entry_id": self.entry_id,
            "timestamp": self.timestamp.isoformat(),
            "decision_type": self.decision_type.value,
            "agent_id": self.agent_id,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "previous_entry_hash": self.previous_entry_hash
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()
    
    def finalize(self) -> None:
        """Compute and set entry hash."""
        self.entry_hash = self.compute_hash()


class AuditTrailManager:
    """Manages audit trail with integrity guarantees."""
    
    def __init__(self, storage_backend):
        self.storage = storage_backend
        self.current_chain_hash = self._get_latest_hash()
    
    def record(
        self,
        decision_type: DecisionType,
        agent_id: str,
        inputs: Dict[str, Any],
        outputs: Any,
        **kwargs
    ) -> AuditEntry:
        """Record a decision with full context."""
        
        entry = AuditEntry(
            session_id=kwargs.get("session_id", ""),
            conversation_id=kwargs.get("conversation_id", ""),
            decision_type=decision_type,
            agent_id=agent_id,
            model_name=kwargs.get("model_name", ""),
            model_version=kwargs.get("model_version", ""),
            input_hash=self._hash_content(inputs),
            input_summary=self._summarize(inputs, max_length=200),
            input_token_count=kwargs.get("input_tokens", 0),
            context_sources=kwargs.get("sources", []),
            reasoning_summary=kwargs.get("reasoning", ""),
            alternatives_considered=kwargs.get("alternatives", []),
            selected_action=kwargs.get("action", ""),
            confidence_score=kwargs.get("confidence", 0.0),
            rules_applied=kwargs.get("rules", []),
            output_hash=self._hash_content(outputs),
            output_summary=self._summarize(outputs, max_length=200),
            output_token_count=kwargs.get("output_tokens", 0),
            source_documents=kwargs.get("documents", []),
            parent_entry_id=kwargs.get("parent_id"),
            previous_entry_hash=self.current_chain_hash
        )
        
        entry.finalize()
        self.current_chain_hash = entry.entry_hash
        self.storage.store(entry)
        
        return entry
    
    def verify_integrity(self) -> Dict[str, Any]:
        """Verify chain integrity."""
        entries = self.storage.get_all_entries()
        
        issues = []
        for i, entry in enumerate(entries):
            # Verify self-hash
            computed = entry.compute_hash()
            if entry.entry_hash != computed:
                issues.append({
                    "entry_id": entry.entry_id,
                    "issue": "hash_mismatch",
                    "stored": entry.entry_hash,
                    "computed": computed
                })
            
            # Verify chain linkage
            if i > 0:
                if entry.previous_entry_hash != entries[i-1].entry_hash:
                    issues.append({
                        "entry_id": entry.entry_id,
                        "issue": "chain_break",
                        "expected_previous": entries[i-1].entry_hash,
                        "stored_previous": entry.previous_entry_hash
                    })
        
        return {
            "verified": len(issues) == 0,
            "entries_checked": len(entries),
            "issues": issues
        }
    
    def generate_compliance_report(
        self,
        start_date: datetime,
        end_date: datetime,
        format: str = "json"
    ) -> Dict[str, Any]:
        """Generate compliance report for period."""
        entries = self.storage.get_entries_in_range(start_date, end_date)
        
        # Aggregate statistics
        by_type = {}
        by_agent = {}
        verification_stats = {"verified": 0, "failed": 0, "pending": 0}
        
        for entry in entries:
            # Count by type
            type_name = entry.decision_type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1
            
            # Count by agent
            by_agent[entry.agent_id] = by_agent.get(entry.agent_id, 0) + 1
            
            # Verification status
            verification_stats[entry.verification_status] = \
                verification_stats.get(entry.verification_status, 0) + 1
        
        return {
            "report_id": str(uuid.uuid4()),
            "generated_at": datetime.utcnow().isoformat(),
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "summary": {
                "total_decisions": len(entries),
                "by_type": by_type,
                "by_agent": by_agent,
                "verification": verification_stats
            },
            "integrity": self.verify_integrity(),
            "sample_entries": [
                self._entry_to_dict(e) for e in entries[:10]
            ]
        }
    
    def _hash_content(self, content: Any) -> str:
        """Hash content without storing sensitive data."""
        serialized = json.dumps(content, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()
    
    def _summarize(self, content: Any, max_length: int = 200) -> str:
        """Create human-readable summary."""
        if isinstance(content, str):
            return content[:max_length] + "..." if len(content) > max_length else content
        elif isinstance(content, dict):
            return str(list(content.keys()))[:max_length]
        else:
            return str(type(content).__name__)
```

#### Acceptance Criteria

1. AuditEntry captures all required fields
2. Chain integrity verification functional
3. Tamper detection working correctly
4. Compliance report generation with period filtering
5. Storage backend abstraction for flexibility
6. Query interface for investigation
7. Export capability for regulatory submission
8. Performance acceptable for high-volume logging

#### Subtasks

| Subtask ID | Description | Status | Dependencies |
|------------|-------------|--------|--------------|
| NESY-009-A | Design AuditEntry schema | Not Started | None |
| NESY-009-B | Implement hash chain logic | Not Started | NESY-009-A |
| NESY-009-C | Create storage backend abstraction | Not Started | NESY-009-A |
| NESY-009-D | Implement file-based storage | Not Started | NESY-009-C |
| NESY-009-E | Implement database storage (optional) | Not Started | NESY-009-C |
| NESY-009-F | Create AuditTrailManager | Not Started | NESY-009-B,D |
| NESY-009-G | Implement integrity verification | Not Started | NESY-009-F |
| NESY-009-H | Create compliance report generator | Not Started | NESY-009-F |
| NESY-009-I | Add query interface | Not Started | NESY-009-F |
| NESY-009-J | Integration with orchestrator | Not Started | NESY-009-F |
| NESY-009-K | Performance testing | Not Started | NESY-009-J |
| NESY-009-L | Documentation | Not Started | NESY-009-K |

---

## Implementation Tracking

### Validation Analysis (2024-12-24)

**Analysis performed by:** Orchestrator agent with parallel research agents
**Sources consulted:** Microsoft Magentic-One, Amazon Automated Reasoning, TACL 2024, NeurIPS 2024, GraphRAG
**Overall Assessment:** STRONG with targeted improvements

#### Key Findings

1. **NESY-006 (Progress Ledgers) should be Phase 1** - Foundational for observability; directly implements Microsoft Magentic-One patterns
2. **NESY-005 (Z3) priority increased** - High value for verifiable claims; validated by Amazon Automated Reasoning (96% correctness)
3. **NESY-002 (Grammar-Constrained) priority decreased** - Claude's native `tool_use` already provides structural guarantees
4. **NESY-004 (Knowledge Graph) moved to Phase 3** - High complexity relative to initial value; Neo4j operational overhead

#### Recommended Additions

| Addition | Target Enhancement | Rationale |
|----------|-------------------|-----------|
| Retry budget management | NESY-001 | Prevent infinite validation loops |
| Entity resolution | NESY-004 | Critical for knowledge graph utility |
| Claim extraction pipeline | NESY-005 | Enable Z3 to process natural language claims |
| Saga pattern | NESY-006 | Compensation logic for multi-step failures |
| Confidence calibration | New | Platt scaling for reliable confidence scores |

#### Validated Patterns

| Pattern | Validation Source | Confidence |
|---------|-------------------|------------|
| Pydantic for LLM output validation | Industry standard | High |
| Heterogeneous judge panels | Kamoi et al. TACL 2024 | High |
| Progress ledgers | Microsoft Magentic-One | High |
| Z3 for formal verification | Amazon Automated Reasoning | High |
| Neo4j for knowledge graphs | Microsoft GraphRAG | Medium-High |

---

### Master Task Registry (Revised)

| Task ID | Title | Phase | Status | Priority | Est. Hours | Dependencies |
|---------|-------|-------|--------|----------|------------|--------------|
| NESY-006 | Progress Ledgers | **Immediate** | Not Started | **Critical** | 24 | None |
| NESY-001 | Pydantic Validators | Immediate | Not Started | Critical | 16 | None |
| NESY-003 | Heterogeneous Judge Configs | Immediate | Not Started | High | 20 | None |
| NESY-005 | Z3 Constraint Solver | Medium-Term | Not Started | **High** | 32 | None |
| NESY-002 | Grammar-Constrained Decoding | Medium-Term | Not Started | **Medium** | 24 | None |
| NESY-009 | Audit Trail Infrastructure | **Medium-Term** | Not Started | Medium | 48 | NESY-006 |
| NESY-004 | Knowledge Graph Layer | **Long-Term** | Not Started | **Medium** | 40 | NESY-001 |
| NESY-007 | Specification Language | Long-Term | Not Started | Low | 60 | NESY-001, NESY-005 |
| NESY-008 | Neurosymbolic Learning | Long-Term | Not Started | Low | 80 | NESY-006 |

### Phase Summary (Revised)

| Phase | Tasks | Total Hours | Dependencies | Rationale |
|-------|-------|-------------|--------------|-----------|
| Immediate | NESY-006, NESY-001, NESY-003 | 60 | None | Observability + validation + quality |
| Medium-Term | NESY-005, NESY-002, NESY-009 | 104 | Phase 1 recommended | Verification + compliance |
| Long-Term | NESY-004, NESY-007, NESY-008 | 180 | Phases 1-2 required | Advanced infrastructure |

---

## Getting Started

### Initial Setup

```bash
# Clone or update repository
cd agent-dashboard

# Create implementation tracking branch
git checkout -b feature/neurosymbolic-enhancements

# Initialize ledger storage
mkdir -p ./ledger_data ./rules_db ./audit_logs

# Install new dependencies
pip install pydantic z3-solver neo4j sentence-transformers lark
```

### First Task Execution

```bash
# Begin with NESY-006 (Progress Ledgers - foundational for observability)
# This enables tracking for all subsequent enhancements
# Note: The ledger code itself is bootstrapped as the first implementation

# Step 1: Create the ledger module structure
mkdir -p src/ledger

# Step 2: Implement TaskLedger and LedgerManager (from NESY-006 specification)
# See Enhancement 2.3 section for full implementation

# Step 3: Once ledger is functional, track subsequent work:
python -c "
from src.ledger.operations import LedgerManager
from src.ledger.task_ledger import TaskStatus, ProgressEntry
from datetime import datetime

ledger = LedgerManager('./ledger_data')
task = ledger.tasks.get('NESY-006')
task.status = TaskStatus.COMPLETED
task.add_progress(ProgressEntry(
    timestamp=datetime.utcnow(),
    agent_id='human',
    action_taken='Implemented Progress Ledger infrastructure',
    outcome='success',
    artifacts_produced=['src/ledger/task_ledger.py', 'src/ledger/operations.py'],
    next_steps=['Begin NESY-001: Pydantic Validators']
))

# Now start NESY-001
task = ledger.tasks.get('NESY-001')
task.status = TaskStatus.IN_PROGRESS
task.add_progress(ProgressEntry(
    timestamp=datetime.utcnow(),
    agent_id='human',
    action_taken='Started implementation of Pydantic validators',
    outcome='in_progress',
    next_steps=['Create base schema classes', 'Define research output schema']
))
"
```

### Progress Check Protocol

Before each work session:

1. Run `ledger.get_next_actionable()` to identify highest priority ready task
2. Review task's `progress_history` for context from previous sessions
3. Check for any `BLOCKED` status tasks that may be unblocked

After each work session:

1. Record `ProgressEntry` with action taken and outcome
2. Update `artifacts` list with any files created
3. If task complete, update status to `PENDING_REVIEW`

---

## References

### Research Sources

1. Kamoi et al. (2024). "When Can LLMs Actually Correct Their Own Mistakes?" TACL, MIT Press
2. Microsoft Research. "Magentic-One: A Generalist Multi-Agent System"
3. NVIDIA/CMU. "XGrammar: Grammar-Constrained Decoding"
4. arXiv:2508.13678. "Neuro-Symbolic AI: Improving Reasoning Abilities of LLMs"
5. Nature. "How good old-fashioned AI could spark the field's next revolution" (Nov 2025)

### Technical Documentation

1. Pydantic v2 Documentation: https://docs.pydantic.dev/
2. Z3 Python API: https://z3prover.github.io/api/html/namespacez3py.html
3. Neo4j Python Driver: https://neo4j.com/docs/python-manual/current/
4. Lark Parser: https://lark-parser.readthedocs.io/

---

*Document generated for Agent Dashboard framework implementation planning.*
*Last updated: 2025-12-22*