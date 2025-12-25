"""
Tool Schema Definitions for Structured Generation.

Provides JSON Schema definitions for agent tools, ensuring
all tool calls conform to valid structure.

Version: 2.6.0
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum


class ToolCategory(str, Enum):
    """Categories for tool organization."""
    SEARCH = "search"
    FILE = "file"
    CODE = "code"
    RESEARCH = "research"
    VERIFICATION = "verification"
    ORCHESTRATION = "orchestration"


@dataclass
class ToolSchema:
    """
    Schema definition for a tool.

    Attributes:
        name: Tool identifier
        description: Human-readable description
        input_schema: JSON Schema for input validation
        category: Tool category for organization
        required_permissions: Permissions needed to use this tool
        examples: Example valid inputs
    """
    name: str
    description: str
    input_schema: Dict[str, Any]
    category: ToolCategory = ToolCategory.ORCHESTRATION
    required_permissions: List[str] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)

    def to_claude_tool(self) -> Dict[str, Any]:
        """Convert to Claude API tool format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }

    def validate_input(self, input_data: Dict[str, Any]) -> List[str]:
        """
        Validate input data against schema.

        Returns list of validation errors (empty if valid).
        """
        errors = []
        schema = self.input_schema

        # Check required fields
        required = schema.get("required", [])
        for req_field in required:
            if req_field not in input_data:
                errors.append(f"Missing required field: {req_field}")

        # Check property types
        properties = schema.get("properties", {})
        for field_name, value in input_data.items():
            if field_name not in properties:
                continue

            prop_schema = properties[field_name]
            field_type = prop_schema.get("type")

            # Type validation
            if field_type == "string" and not isinstance(value, str):
                errors.append(f"Field '{field_name}' must be a string")
            elif field_type == "integer" and not isinstance(value, int):
                errors.append(f"Field '{field_name}' must be an integer")
            elif field_type == "number" and not isinstance(value, (int, float)):
                errors.append(f"Field '{field_name}' must be a number")
            elif field_type == "boolean" and not isinstance(value, bool):
                errors.append(f"Field '{field_name}' must be a boolean")
            elif field_type == "array" and not isinstance(value, list):
                errors.append(f"Field '{field_name}' must be an array")
            elif field_type == "object" and not isinstance(value, dict):
                errors.append(f"Field '{field_name}' must be an object")

            # String constraints
            if field_type == "string" and isinstance(value, str):
                min_len = prop_schema.get("minLength")
                max_len = prop_schema.get("maxLength")
                pattern = prop_schema.get("pattern")
                enum_values = prop_schema.get("enum")

                if min_len is not None and len(value) < min_len:
                    errors.append(
                        f"Field '{field_name}' must be at least {min_len} characters"
                    )
                if max_len is not None and len(value) > max_len:
                    errors.append(
                        f"Field '{field_name}' must be at most {max_len} characters"
                    )
                if enum_values is not None and value not in enum_values:
                    errors.append(
                        f"Field '{field_name}' must be one of: {enum_values}"
                    )
                if pattern is not None:
                    import re
                    if not re.match(pattern, value):
                        errors.append(
                            f"Field '{field_name}' does not match pattern: {pattern}"
                        )

            # Numeric constraints
            if field_type in ("integer", "number") and isinstance(value, (int, float)):
                minimum = prop_schema.get("minimum")
                maximum = prop_schema.get("maximum")

                if minimum is not None and value < minimum:
                    errors.append(
                        f"Field '{field_name}' must be at least {minimum}"
                    )
                if maximum is not None and value > maximum:
                    errors.append(
                        f"Field '{field_name}' must be at most {maximum}"
                    )

        return errors


# Core Tool Schemas

WEB_SEARCH_TOOL = ToolSchema(
    name="web_search",
    description="Search the web for information on a topic",
    category=ToolCategory.SEARCH,
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query string",
                "minLength": 3,
                "maxLength": 200,
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return",
                "minimum": 1,
                "maximum": 20,
                "default": 10,
            },
            "recency_filter": {
                "type": "string",
                "description": "Filter results by recency",
                "enum": ["day", "week", "month", "year", "any"],
                "default": "any",
            },
            "domain_filter": {
                "type": "array",
                "description": "Limit search to specific domains",
                "items": {"type": "string"},
            },
        },
        "required": ["query"],
    },
    examples=[
        {"query": "Python async programming best practices"},
        {"query": "Claude API documentation", "max_results": 5, "recency_filter": "month"},
    ],
)


FILE_OPERATION_TOOL = ToolSchema(
    name="file_operation",
    description="Perform file system operations (read, write, list)",
    category=ToolCategory.FILE,
    required_permissions=["file_access"],
    input_schema={
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "description": "Type of file operation",
                "enum": ["read", "write", "append", "delete", "list", "exists"],
            },
            "path": {
                "type": "string",
                "description": "File or directory path",
                "pattern": r"^[a-zA-Z0-9_./-]+$",
                "minLength": 1,
                "maxLength": 500,
            },
            "content": {
                "type": "string",
                "description": "Content to write (for write/append operations)",
            },
            "encoding": {
                "type": "string",
                "description": "File encoding",
                "enum": ["utf-8", "ascii", "latin-1"],
                "default": "utf-8",
            },
        },
        "required": ["operation", "path"],
    },
    examples=[
        {"operation": "read", "path": "config.json"},
        {"operation": "write", "path": "output.txt", "content": "Hello, World!"},
    ],
)


CODE_EXECUTION_TOOL = ToolSchema(
    name="execute_code",
    description="Execute code in a sandboxed environment",
    category=ToolCategory.CODE,
    required_permissions=["code_execution"],
    input_schema={
        "type": "object",
        "properties": {
            "language": {
                "type": "string",
                "description": "Programming language",
                "enum": ["python", "javascript", "bash", "sql"],
            },
            "code": {
                "type": "string",
                "description": "Code to execute",
                "minLength": 1,
                "maxLength": 50000,
            },
            "timeout_seconds": {
                "type": "integer",
                "description": "Maximum execution time",
                "minimum": 1,
                "maximum": 300,
                "default": 30,
            },
            "environment": {
                "type": "object",
                "description": "Environment variables to set",
                "additionalProperties": {"type": "string"},
            },
        },
        "required": ["language", "code"],
    },
    examples=[
        {"language": "python", "code": "print('Hello, World!')"},
        {"language": "bash", "code": "ls -la", "timeout_seconds": 10},
    ],
)


RESEARCH_QUERY_TOOL = ToolSchema(
    name="research_query",
    description="Execute a structured research query with source requirements",
    category=ToolCategory.RESEARCH,
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Research question or topic",
                "minLength": 10,
                "maxLength": 1000,
            },
            "depth": {
                "type": "string",
                "description": "Research depth level",
                "enum": ["quick", "standard", "comprehensive"],
                "default": "standard",
            },
            "source_types": {
                "type": "array",
                "description": "Types of sources to include",
                "items": {
                    "type": "string",
                    "enum": ["academic", "news", "blog", "official", "any"],
                },
                "default": ["any"],
            },
            "min_sources": {
                "type": "integer",
                "description": "Minimum number of sources required",
                "minimum": 1,
                "maximum": 20,
                "default": 3,
            },
            "require_citations": {
                "type": "boolean",
                "description": "Whether to require citations for claims",
                "default": True,
            },
        },
        "required": ["query"],
    },
    examples=[
        {"query": "What are the latest developments in quantum computing?"},
        {
            "query": "Impact of microplastics on marine ecosystems",
            "depth": "comprehensive",
            "source_types": ["academic", "official"],
            "min_sources": 5,
        },
    ],
)


JUDGE_VERDICT_TOOL = ToolSchema(
    name="judge_verdict",
    description="Submit a structured judgment verdict for content evaluation",
    category=ToolCategory.VERIFICATION,
    input_schema={
        "type": "object",
        "properties": {
            "verdict": {
                "type": "string",
                "description": "Overall verdict",
                "enum": ["pass", "fail", "needs_revision", "abstain"],
            },
            "confidence": {
                "type": "number",
                "description": "Confidence in verdict (0.0-1.0)",
                "minimum": 0.0,
                "maximum": 1.0,
            },
            "score": {
                "type": "number",
                "description": "Numeric score if applicable",
                "minimum": 0.0,
                "maximum": 10.0,
            },
            "reasoning": {
                "type": "string",
                "description": "Detailed reasoning for verdict",
                "minLength": 50,
                "maxLength": 5000,
            },
            "issues_found": {
                "type": "array",
                "description": "List of specific issues identified",
                "items": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "enum": [
                                "accuracy",
                                "completeness",
                                "clarity",
                                "relevance",
                                "format",
                            ],
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["critical", "major", "minor", "suggestion"],
                        },
                        "description": {"type": "string"},
                        "location": {"type": "string"},
                    },
                    "required": ["category", "severity", "description"],
                },
            },
            "suggestions": {
                "type": "array",
                "description": "Improvement suggestions",
                "items": {"type": "string"},
            },
        },
        "required": ["verdict", "confidence", "reasoning"],
    },
    examples=[
        {
            "verdict": "pass",
            "confidence": 0.9,
            "score": 8.5,
            "reasoning": "The response accurately addresses all key points with proper citations.",
            "issues_found": [],
            "suggestions": ["Consider adding more examples for clarity."],
        },
    ],
)


# Tool registry
_TOOL_REGISTRY: Dict[str, ToolSchema] = {
    "web_search": WEB_SEARCH_TOOL,
    "file_operation": FILE_OPERATION_TOOL,
    "execute_code": CODE_EXECUTION_TOOL,
    "research_query": RESEARCH_QUERY_TOOL,
    "judge_verdict": JUDGE_VERDICT_TOOL,
}


def get_tool_schema(name: str) -> Optional[ToolSchema]:
    """Get a tool schema by name."""
    return _TOOL_REGISTRY.get(name)


def list_tool_schemas(category: Optional[ToolCategory] = None) -> List[ToolSchema]:
    """List all registered tool schemas, optionally filtered by category."""
    schemas = list(_TOOL_REGISTRY.values())
    if category is not None:
        schemas = [s for s in schemas if s.category == category]
    return schemas


def register_tool_schema(schema: ToolSchema) -> None:
    """Register a new tool schema."""
    _TOOL_REGISTRY[schema.name] = schema


def get_tools_for_claude(
    tool_names: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Get tool definitions formatted for Claude API.

    Args:
        tool_names: Specific tools to include (all if None)

    Returns:
        List of tool definitions for Claude API
    """
    if tool_names is None:
        schemas = list(_TOOL_REGISTRY.values())
    else:
        schemas = [
            _TOOL_REGISTRY[name]
            for name in tool_names
            if name in _TOOL_REGISTRY
        ]
    return [s.to_claude_tool() for s in schemas]
