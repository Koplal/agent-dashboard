"""
Audit Trail Infrastructure Module.

Provides comprehensive audit trail capabilities for enterprise compliance,
with tamper-evident hash chaining, multiple storage backends, and
compliance report generation.

Version: 2.6.0
"""

from .trail import (
    AuditEntry,
    DecisionType,
    VerificationStatus,
    hash_content,
    summarize_content,
)
from .storage import (
    StorageBackend,
    FileStorageBackend,
    SQLiteStorageBackend,
    MemoryStorageBackend,
)
from .manager import (
    AuditTrailManager,
    IntegrityReport,
    get_default_manager,
    record_decision,
)
from .query import (
    AuditQueryEngine,
    QueryFilter,
    QueryResult,
    SortField,
    SortOrder,
)
from .compliance import (
    ComplianceReport,
    ComplianceReportGenerator,
)

__all__ = [
    # Trail
    "AuditEntry",
    "DecisionType",
    "VerificationStatus",
    "hash_content",
    "summarize_content",
    # Storage
    "StorageBackend",
    "FileStorageBackend",
    "SQLiteStorageBackend",
    "MemoryStorageBackend",
    # Manager
    "AuditTrailManager",
    "IntegrityReport",
    "get_default_manager",
    "record_decision",
    # Query
    "AuditQueryEngine",
    "QueryFilter",
    "QueryResult",
    "SortField",
    "SortOrder",
    # Compliance
    "ComplianceReport",
    "ComplianceReportGenerator",
]
