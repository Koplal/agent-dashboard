"""
Entity-Aware Provenance Tracking (AUDIT-001).

Provides entity provenance tracking for audit trail entries,
enabling tracing of entity involvement across decision chains.

Version: 2.6.0
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .manager import AuditTrailManager
    from ..knowledge.graph import Entity, EntityType


def utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


class EntityRole(str, Enum):
    """Role of an entity within an audit entry.

    Attributes:
        INPUT: Entity was an input to the decision
        OUTPUT: Entity was produced as output
        CONTEXT: Entity provided context for the decision
        SUBJECT: Entity was the subject of the decision
    """
    INPUT = "input"
    OUTPUT = "output"
    CONTEXT = "context"
    SUBJECT = "subject"


@dataclass(frozen=True)
class EntityProvenance:
    """Immutable snapshot of entity state at a point in time.

    Captures the entity's identity, role, and temporal validity
    at the moment it was involved in an audit entry.

    Attributes:
        entity_name: Name of the entity
        entity_type: Type classification of the entity
        role: Role the entity played in the entry
        entry_id: ID of the audit entry
        provenance_id: Unique identifier for this provenance record
        recorded_at: When this provenance was recorded
        valid_from: Start of entity's temporal validity (snapshot)
        valid_to: End of entity's temporal validity (snapshot)
        source_location: Code location if applicable
        metadata: Additional entity metadata
    """
    entity_name: str
    entity_type: "EntityType"
    role: EntityRole
    entry_id: str
    provenance_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    recorded_at: datetime = field(default_factory=utc_now)
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    source_location: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "provenance_id": self.provenance_id,
            "entity_name": self.entity_name,
            "entity_type": self.entity_type.value,
            "role": self.role.value,
            "entry_id": self.entry_id,
            "recorded_at": self.recorded_at.isoformat(),
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "source_location": self.source_location,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EntityProvenance":
        """Create EntityProvenance from dictionary."""
        from knowledge.graph import EntityType

        recorded_at = data.get("recorded_at")
        if isinstance(recorded_at, str):
            recorded_at = datetime.fromisoformat(recorded_at)
        elif recorded_at is None:
            recorded_at = utc_now()

        valid_from = data.get("valid_from")
        if isinstance(valid_from, str):
            valid_from = datetime.fromisoformat(valid_from)

        valid_to = data.get("valid_to")
        if isinstance(valid_to, str):
            valid_to = datetime.fromisoformat(valid_to)

        return cls(
            provenance_id=data.get("provenance_id", str(uuid.uuid4())),
            entity_name=data["entity_name"],
            entity_type=EntityType(data["entity_type"]),
            role=EntityRole(data["role"]),
            entry_id=data["entry_id"],
            recorded_at=recorded_at,
            valid_from=valid_from,
            valid_to=valid_to,
            source_location=data.get("source_location"),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_entity(
        cls,
        entity: "Entity",
        role: EntityRole,
        entry_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "EntityProvenance":
        """Create EntityProvenance from an Entity.

        Args:
            entity: The Entity to create provenance from
            role: Role the entity plays in this entry
            entry_id: ID of the audit entry
            metadata: Optional additional metadata

        Returns:
            New EntityProvenance with entity fields copied
        """
        return cls(
            entity_name=entity.name,
            entity_type=entity.entity_type,
            role=role,
            entry_id=entry_id,
            valid_from=entity.valid_from,
            valid_to=entity.valid_to,
            source_location=entity.source_location,
            metadata=metadata or entity.metadata.copy(),
        )


class EntityProvenanceTracker:
    """Tracks entity provenance across audit entries.

    Provides:
    - Recording entity involvement in decisions
    - Querying entities by entry, role, type, name
    - Timeline views of entity appearances
    - Tracing entities back through decision chains

    Example:
        tracker = EntityProvenanceTracker(manager=audit_manager)

        # Record entity involvement
        prov = tracker.record(
            entity=my_entity,
            role=EntityRole.INPUT,
            entry_id=entry.entry_id,
        )

        # Query entities
        inputs = tracker.get_entities_by_role(EntityRole.INPUT)
        timeline = tracker.get_entity_timeline("MyEntity")
    """

    def __init__(self, manager: Optional["AuditTrailManager"] = None):
        """Initialize the provenance tracker.

        Args:
            manager: Optional AuditTrailManager for trace operations
        """
        self.manager = manager
        self._records: List[EntityProvenance] = []

    def record(
        self,
        entity: "Entity",
        role: EntityRole,
        entry_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EntityProvenance:
        """Record entity provenance for an audit entry.

        Args:
            entity: The Entity involved in the entry
            role: Role the entity plays
            entry_id: ID of the audit entry
            metadata: Optional additional metadata

        Returns:
            The created EntityProvenance record

        Raises:
            ValueError: If entity name is empty
            TypeError: If entity is None
        """
        if entity is None:
            raise TypeError("entity cannot be None")
        if not entity.name or not entity.name.strip():
            raise ValueError("entity name cannot be empty")
        if not entry_id or not entry_id.strip():
            raise ValueError("entry_id cannot be empty")

        prov = EntityProvenance.from_entity(
            entity=entity,
            role=role,
            entry_id=entry_id,
            metadata=metadata,
        )
        self._records.append(prov)
        return prov

    def get_entities_by_entry(self, entry_id: str) -> List[EntityProvenance]:
        """Get all entities for a specific audit entry.

        Args:
            entry_id: The audit entry ID

        Returns:
            List of EntityProvenance records for the entry
        """
        return [r for r in self._records if r.entry_id == entry_id]

    def get_entities_by_role(self, role: EntityRole) -> List[EntityProvenance]:
        """Get all entities with a specific role.

        Args:
            role: The EntityRole to filter by

        Returns:
            List of EntityProvenance records with matching role
        """
        return [r for r in self._records if r.role == role]

    def get_entities_by_name(self, entity_name: str) -> List[EntityProvenance]:
        """Get all records for a named entity.

        Args:
            entity_name: Name of the entity

        Returns:
            List of EntityProvenance records with matching name
        """
        return [r for r in self._records if r.entity_name == entity_name]

    def get_entities_by_type(self, entity_type: "EntityType") -> List[EntityProvenance]:
        """Get all entities of a specific type.

        Args:
            entity_type: The EntityType to filter by

        Returns:
            List of EntityProvenance records with matching type
        """
        return [r for r in self._records if r.entity_type == entity_type]

    def get_entities(
        self,
        entry_id: Optional[str] = None,
        role: Optional[EntityRole] = None,
        entity_type: Optional["EntityType"] = None,
        entity_name: Optional[str] = None,
    ) -> List[EntityProvenance]:
        """Get entities matching multiple criteria (AND logic).

        Args:
            entry_id: Filter by entry ID
            role: Filter by role
            entity_type: Filter by entity type
            entity_name: Filter by entity name

        Returns:
            List of EntityProvenance records matching all criteria
        """
        results = self._records

        if entry_id is not None:
            results = [r for r in results if r.entry_id == entry_id]
        if role is not None:
            results = [r for r in results if r.role == role]
        if entity_type is not None:
            results = [r for r in results if r.entity_type == entity_type]
        if entity_name is not None:
            results = [r for r in results if r.entity_name == entity_name]

        return results

    def get_entity_timeline(
        self,
        entity_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[EntityProvenance]:
        """Get chronological timeline of entity appearances.

        Args:
            entity_name: Name of the entity
            start_date: Optional start of date range
            end_date: Optional end of date range

        Returns:
            List of EntityProvenance records ordered by recorded_at
        """
        results = self.get_entities_by_name(entity_name)

        if start_date is not None:
            results = [r for r in results if r.recorded_at >= start_date]
        if end_date is not None:
            results = [r for r in results if r.recorded_at <= end_date]

        return sorted(results, key=lambda r: r.recorded_at)

    def trace_entity_to_source(
        self,
        entity_name: str,
        entry_id: str,
        max_depth: int = 10,
    ) -> List[EntityProvenance]:
        """Trace entity back through decision chain.

        Args:
            entity_name: Name of the entity to trace
            entry_id: Starting entry ID
            max_depth: Maximum depth to trace

        Returns:
            List of EntityProvenance records in trace order
        """
        if self.manager is None:
            # Without manager, just return records for this entity
            return self.get_entities_by_name(entity_name)

        results = []
        visited = set()
        current_entry_id = entry_id
        depth = 0

        while current_entry_id and depth <= max_depth:
            if current_entry_id in visited:
                break
            visited.add(current_entry_id)

            # Get entity provenance for this entry
            entry_provs = [
                r for r in self._records
                if r.entry_id == current_entry_id and r.entity_name == entity_name
            ]
            results.extend(entry_provs)

            # Get parent entry
            entry = self.manager.get_entry(current_entry_id)
            if entry and entry.parent_entry_id:
                current_entry_id = entry.parent_entry_id
            else:
                break

            depth += 1

        return results

    def get_statistics(self) -> Dict[str, Any]:
        """Get provenance tracking statistics.

        Returns:
            Dictionary with statistics
        """
        entity_names = {r.entity_name for r in self._records}

        by_role = {}
        for role in EntityRole:
            by_role[role.value] = len([r for r in self._records if r.role == role])

        return {
            "total_provenance_records": len(self._records),
            "unique_entities": len(entity_names),
            "by_role": by_role,
        }

    def verify_integrity(self) -> bool:
        """Verify provenance records are valid.

        Returns:
            True if all records are valid
        """
        # For now, just verify all records have required fields
        for record in self._records:
            if not record.entity_name:
                return False
            if not record.entry_id:
                return False
        return True
