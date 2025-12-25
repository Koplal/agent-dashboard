"""
Grammar-Constrained Generation Module.

Provides structured output generation with schema enforcement
using Claude's tool_use feature and optional local model support.

Version: 2.6.0
"""

from .structured_generation import (
    StructuredGenerator,
    GenerationResult,
    GenerationError,
)
from .tool_schemas import (
    ToolSchema,
    get_tool_schema,
    list_tool_schemas,
    WEB_SEARCH_TOOL,
    FILE_OPERATION_TOOL,
    CODE_EXECUTION_TOOL,
    RESEARCH_QUERY_TOOL,
    JUDGE_VERDICT_TOOL,
)
from .schema_registry import (
    SchemaRegistry,
    get_default_registry,
    register_schema,
    get_schema,
)
from .grammar_constrained import (
    GrammarConstrainedGenerator,
    LocalGenerationResult,
    OUTLINES_AVAILABLE,
)

__all__ = [
    # Structured generation
    "StructuredGenerator",
    "GenerationResult",
    "GenerationError",
    # Tool schemas
    "ToolSchema",
    "get_tool_schema",
    "list_tool_schemas",
    "WEB_SEARCH_TOOL",
    "FILE_OPERATION_TOOL",
    "CODE_EXECUTION_TOOL",
    "RESEARCH_QUERY_TOOL",
    "JUDGE_VERDICT_TOOL",
    # Schema registry
    "SchemaRegistry",
    "get_default_registry",
    "register_schema",
    "get_schema",
    # Grammar-constrained (local models)
    "GrammarConstrainedGenerator",
    "LocalGenerationResult",
    "OUTLINES_AVAILABLE",
]
