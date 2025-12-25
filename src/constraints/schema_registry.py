"""
Schema Registry for Dynamic Schema Lookup.

Provides centralized registration and retrieval of Pydantic schemas
for structured generation, enabling runtime schema discovery.

Version: 2.6.0
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Type, Optional, List, TypeVar, Callable

from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


@dataclass
class SchemaMetadata:
    """
    Metadata about a registered schema.

    Attributes:
        name: Schema identifier
        schema_class: The Pydantic model class
        description: Human-readable description
        category: Category for organization
        version: Schema version
        deprecated: Whether schema is deprecated
        replacement: Replacement schema if deprecated
        registered_at: When the schema was registered
    """
    name: str
    schema_class: Type[BaseModel]
    description: str = ""
    category: str = "general"
    version: str = "1.0.0"
    deprecated: bool = False
    replacement: Optional[str] = None
    registered_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (without schema_class)."""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "version": self.version,
            "deprecated": self.deprecated,
            "replacement": self.replacement,
            "registered_at": self.registered_at.isoformat(),
            "json_schema": self.schema_class.model_json_schema(),
        }


class SchemaRegistry:
    """
    Central registry for Pydantic schemas.

    Enables runtime schema discovery and validation, supporting
    dynamic tool generation and output validation.

    Example:
        from pydantic import BaseModel

        class MyOutput(BaseModel):
            result: str
            score: float

        registry = SchemaRegistry()
        registry.register(MyOutput, description="Custom output format")

        # Later retrieve by name
        schema = registry.get("MyOutput")
        instance = schema.model_validate({"result": "test", "score": 0.9})
    """

    def __init__(self):
        """Initialize the schema registry."""
        self._schemas: Dict[str, SchemaMetadata] = {}
        self._category_index: Dict[str, List[str]] = {}
        self._validators: List[Callable[[Type[BaseModel]], Optional[str]]] = []

    def register(
        self,
        schema_class: Type[T],
        name: Optional[str] = None,
        description: str = "",
        category: str = "general",
        version: str = "1.0.0",
        deprecated: bool = False,
        replacement: Optional[str] = None,
    ) -> SchemaMetadata:
        """
        Register a schema in the registry.

        Args:
            schema_class: Pydantic model class to register
            name: Optional custom name (defaults to class name)
            description: Human-readable description
            category: Category for organization
            version: Schema version
            deprecated: Whether schema is deprecated
            replacement: Replacement schema if deprecated

        Returns:
            SchemaMetadata for the registered schema

        Raises:
            ValueError: If schema validation fails
        """
        name = name or schema_class.__name__

        # Run validators
        for validator in self._validators:
            error = validator(schema_class)
            if error:
                raise ValueError(f"Schema validation failed: {error}")

        metadata = SchemaMetadata(
            name=name,
            schema_class=schema_class,
            description=description or schema_class.__doc__ or "",
            category=category,
            version=version,
            deprecated=deprecated,
            replacement=replacement,
        )

        self._schemas[name] = metadata

        # Update category index
        if category not in self._category_index:
            self._category_index[category] = []
        if name not in self._category_index[category]:
            self._category_index[category].append(name)

        logger.debug(f"Registered schema: {name} (category: {category})")
        return metadata

    def get(self, name: str) -> Optional[Type[BaseModel]]:
        """
        Get a schema class by name.

        Args:
            name: Schema name

        Returns:
            Pydantic model class or None if not found
        """
        metadata = self._schemas.get(name)
        if metadata is None:
            return None

        if metadata.deprecated:
            logger.warning(
                f"Schema '{name}' is deprecated. "
                f"Use '{metadata.replacement}' instead."
            )

        return metadata.schema_class

    def get_metadata(self, name: str) -> Optional[SchemaMetadata]:
        """Get schema metadata by name."""
        return self._schemas.get(name)

    def list_schemas(
        self,
        category: Optional[str] = None,
        include_deprecated: bool = False,
    ) -> List[SchemaMetadata]:
        """
        List registered schemas.

        Args:
            category: Filter by category
            include_deprecated: Whether to include deprecated schemas

        Returns:
            List of SchemaMetadata
        """
        if category is not None:
            names = self._category_index.get(category, [])
            schemas = [self._schemas[n] for n in names if n in self._schemas]
        else:
            schemas = list(self._schemas.values())

        if not include_deprecated:
            schemas = [s for s in schemas if not s.deprecated]

        return schemas

    def list_categories(self) -> List[str]:
        """List all registered categories."""
        return list(self._category_index.keys())

    def unregister(self, name: str) -> bool:
        """
        Unregister a schema.

        Args:
            name: Schema name to unregister

        Returns:
            True if schema was removed, False if not found
        """
        if name not in self._schemas:
            return False

        metadata = self._schemas.pop(name)

        # Update category index
        category = metadata.category
        if category in self._category_index:
            self._category_index[category] = [
                n for n in self._category_index[category] if n != name
            ]
            if not self._category_index[category]:
                del self._category_index[category]

        logger.debug(f"Unregistered schema: {name}")
        return True

    def add_validator(
        self,
        validator: Callable[[Type[BaseModel]], Optional[str]],
    ) -> None:
        """
        Add a schema validator.

        Validators are called during registration and should return
        an error message if validation fails, or None if valid.

        Args:
            validator: Function that takes a schema class and returns error or None
        """
        self._validators.append(validator)

    def get_json_schema(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get JSON Schema for a registered schema.

        Args:
            name: Schema name

        Returns:
            JSON Schema dictionary or None if not found
        """
        schema_class = self.get(name)
        if schema_class is None:
            return None
        return schema_class.model_json_schema()

    def validate_data(
        self,
        name: str,
        data: Dict[str, Any],
    ) -> tuple[bool, Optional[BaseModel], Optional[str]]:
        """
        Validate data against a registered schema.

        Args:
            name: Schema name
            data: Data to validate

        Returns:
            Tuple of (success, validated_model, error_message)
        """
        schema_class = self.get(name)
        if schema_class is None:
            return False, None, f"Schema '{name}' not found"

        try:
            validated = schema_class.model_validate(data)
            return True, validated, None
        except Exception as e:
            return False, None, str(e)

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        total = len(self._schemas)
        deprecated = sum(1 for s in self._schemas.values() if s.deprecated)

        return {
            "total_schemas": total,
            "active_schemas": total - deprecated,
            "deprecated_schemas": deprecated,
            "categories": len(self._category_index),
            "category_counts": {
                cat: len(names)
                for cat, names in self._category_index.items()
            },
        }


# Default registry instance
_default_registry: Optional[SchemaRegistry] = None


def get_default_registry() -> SchemaRegistry:
    """Get or create the default schema registry."""
    global _default_registry
    if _default_registry is None:
        _default_registry = SchemaRegistry()
        _register_builtin_schemas(_default_registry)
    return _default_registry


def _register_builtin_schemas(registry: SchemaRegistry) -> None:
    """Register built-in schemas from the schemas module."""
    try:
        from ..schemas import (
            ResearchOutput,
            CodeAnalysisOutput,
            OrchestrationPlan,
            JudgeVerdict,
        )

        registry.register(
            ResearchOutput,
            description="Output from research agents",
            category="research",
        )
        registry.register(
            CodeAnalysisOutput,
            description="Output from code analysis agents",
            category="code",
        )
        registry.register(
            OrchestrationPlan,
            description="Orchestration plan for multi-agent workflows",
            category="orchestration",
        )
        registry.register(
            JudgeVerdict,
            description="Verdict from judge agents",
            category="verification",
        )
        logger.debug("Registered built-in schemas")
    except ImportError as e:
        logger.debug(f"Could not import built-in schemas: {e}")


def register_schema(
    schema_class: Type[T],
    name: Optional[str] = None,
    description: str = "",
    category: str = "general",
) -> SchemaMetadata:
    """
    Register a schema in the default registry.

    Convenience function for simple schema registration.

    Args:
        schema_class: Pydantic model class
        name: Optional custom name
        description: Human-readable description
        category: Category for organization

    Returns:
        SchemaMetadata for the registered schema
    """
    return get_default_registry().register(
        schema_class,
        name=name,
        description=description,
        category=category,
    )


def get_schema(name: str) -> Optional[Type[BaseModel]]:
    """
    Get a schema from the default registry.

    Args:
        name: Schema name

    Returns:
        Pydantic model class or None
    """
    return get_default_registry().get(name)


def list_schemas(category: Optional[str] = None) -> List[SchemaMetadata]:
    """
    List schemas from the default registry.

    Args:
        category: Optional category filter

    Returns:
        List of SchemaMetadata
    """
    return get_default_registry().list_schemas(category=category)


# Schema decorator for easy registration
def registered_schema(
    name: Optional[str] = None,
    description: str = "",
    category: str = "general",
    version: str = "1.0.0",
):
    """
    Decorator to register a schema class.

    Example:
        @registered_schema(category="custom", description="My custom output")
        class MyOutput(BaseModel):
            result: str
    """
    def decorator(cls: Type[T]) -> Type[T]:
        get_default_registry().register(
            cls,
            name=name,
            description=description,
            category=category,
            version=version,
        )
        return cls
    return decorator
