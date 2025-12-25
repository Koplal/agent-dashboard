"""
Audit Trail Storage Backends.

Provides storage backend abstraction with file-based and SQLite
implementations for audit trail persistence.

Version: 2.6.0
"""

import json
import logging
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Iterator
from contextlib import contextmanager

from .trail import AuditEntry, DecisionType, VerificationStatus

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


class StorageBackend(ABC):
    """
    Abstract storage backend for audit entries.

    Provides interface for storing and retrieving audit entries
    with support for querying by various criteria.
    """

    @abstractmethod
    def store(self, entry: AuditEntry) -> None:
        """Store an audit entry."""
        pass

    @abstractmethod
    def get(self, entry_id: str) -> Optional[AuditEntry]:
        """Retrieve an entry by ID."""
        pass

    @abstractmethod
    def get_all_entries(self) -> List[AuditEntry]:
        """Get all entries in chronological order."""
        pass

    @abstractmethod
    def get_entries_in_range(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> List[AuditEntry]:
        """Get entries within a date range."""
        pass

    @abstractmethod
    def get_latest_hash(self) -> str:
        """Get the hash of the most recent entry."""
        pass

    @abstractmethod
    def get_entries_by_session(self, session_id: str) -> List[AuditEntry]:
        """Get entries for a specific session."""
        pass

    @abstractmethod
    def get_entries_by_agent(self, agent_id: str) -> List[AuditEntry]:
        """Get entries for a specific agent."""
        pass

    @abstractmethod
    def get_entries_by_type(self, decision_type: DecisionType) -> List[AuditEntry]:
        """Get entries of a specific decision type."""
        pass

    @abstractmethod
    def count(self) -> int:
        """Get total number of entries."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all entries (use with caution)."""
        pass


class FileStorageBackend(StorageBackend):
    """
    File-based storage backend using JSON Lines format.

    Stores each entry as a JSON object on a separate line,
    enabling efficient append operations and streaming reads.
    """

    def __init__(
        self,
        storage_path: str,
        max_file_size_mb: int = 100,
        rotate_files: bool = True,
    ):
        """
        Initialize file storage backend.

        Args:
            storage_path: Directory for audit files
            max_file_size_mb: Maximum file size before rotation
            rotate_files: Whether to rotate files when full
        """
        self.storage_path = Path(storage_path).expanduser()
        self.max_file_size = max_file_size_mb * 1024 * 1024
        self.rotate_files = rotate_files

        # Create storage directory
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Current active file
        self._current_file = self._get_or_create_current_file()

    def _get_or_create_current_file(self) -> Path:
        """Get current active file or create new one."""
        files = sorted(self.storage_path.glob("audit_*.jsonl"))

        if files:
            current = files[-1]
            if current.stat().st_size < self.max_file_size:
                return current

        # Create new file
        timestamp = utc_now().strftime("%Y%m%d_%H%M%S")
        return self.storage_path / f"audit_{timestamp}.jsonl"

    def _maybe_rotate(self) -> None:
        """Rotate to new file if current is too large."""
        if not self.rotate_files:
            return

        if self._current_file.exists():
            if self._current_file.stat().st_size >= self.max_file_size:
                self._current_file = self._get_or_create_current_file()

    def store(self, entry: AuditEntry) -> None:
        """Store an audit entry."""
        self._maybe_rotate()

        with open(self._current_file, "a", encoding="utf-8") as f:
            json.dump(entry.to_dict(), f, default=str)
            f.write("\n")

    def get(self, entry_id: str) -> Optional[AuditEntry]:
        """Retrieve an entry by ID."""
        for entry in self._iter_all_entries():
            if entry.entry_id == entry_id:
                return entry
        return None

    def get_all_entries(self) -> List[AuditEntry]:
        """Get all entries in chronological order."""
        return list(self._iter_all_entries())

    def _iter_all_entries(self) -> Iterator[AuditEntry]:
        """Iterate over all entries from all files."""
        files = sorted(self.storage_path.glob("audit_*.jsonl"))

        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                data = json.loads(line)
                                yield AuditEntry.from_dict(data)
                            except json.JSONDecodeError as e:
                                logger.warning(f"Invalid JSON in {file_path}: {e}")
            except IOError as e:
                logger.error(f"Error reading {file_path}: {e}")

    def get_entries_in_range(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> List[AuditEntry]:
        """Get entries within a date range."""
        entries = []
        for entry in self._iter_all_entries():
            if start_date <= entry.timestamp <= end_date:
                entries.append(entry)
        return entries

    def get_latest_hash(self) -> str:
        """Get the hash of the most recent entry."""
        files = sorted(self.storage_path.glob("audit_*.jsonl"), reverse=True)

        for file_path in files:
            try:
                with open(file_path, "rb") as f:
                    # Seek to end and find last line
                    f.seek(0, 2)
                    size = f.tell()
                    if size == 0:
                        continue

                    # Read backwards to find last line
                    f.seek(max(0, size - 4096))
                    lines = f.read().decode("utf-8").strip().split("\n")

                    if lines:
                        last_line = lines[-1].strip()
                        if last_line:
                            data = json.loads(last_line)
                            return data.get("entry_hash", "")
            except (IOError, json.JSONDecodeError) as e:
                logger.warning(f"Error reading last entry from {file_path}: {e}")

        return ""

    def get_entries_by_session(self, session_id: str) -> List[AuditEntry]:
        """Get entries for a specific session."""
        return [e for e in self._iter_all_entries() if e.session_id == session_id]

    def get_entries_by_agent(self, agent_id: str) -> List[AuditEntry]:
        """Get entries for a specific agent."""
        return [e for e in self._iter_all_entries() if e.agent_id == agent_id]

    def get_entries_by_type(self, decision_type: DecisionType) -> List[AuditEntry]:
        """Get entries of a specific decision type."""
        return [e for e in self._iter_all_entries() if e.decision_type == decision_type]

    def count(self) -> int:
        """Get total number of entries."""
        count = 0
        for _ in self._iter_all_entries():
            count += 1
        return count

    def clear(self) -> None:
        """Clear all entries (use with caution)."""
        for file_path in self.storage_path.glob("audit_*.jsonl"):
            file_path.unlink()
        self._current_file = self._get_or_create_current_file()


class SQLiteStorageBackend(StorageBackend):
    """
    SQLite-based storage backend for audit entries.

    Provides efficient querying and indexing for large audit trails.
    """

    def __init__(
        self,
        db_path: str,
        wal_mode: bool = True,
    ):
        """
        Initialize SQLite storage backend.

        Args:
            db_path: Path to SQLite database file
            wal_mode: Use WAL mode for better concurrency
        """
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.wal_mode = wal_mode

        self._init_db()

    @contextmanager
    def _get_connection(self):
        """Get a database connection with proper cleanup."""
        conn = sqlite3.connect(
            self.db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        )
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with self._get_connection() as conn:
            if self.wal_mode:
                conn.execute("PRAGMA journal_mode=WAL")

            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_entries (
                    entry_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    session_id TEXT,
                    conversation_id TEXT,
                    decision_type TEXT NOT NULL,
                    agent_id TEXT,
                    model_name TEXT,
                    model_version TEXT,
                    input_hash TEXT,
                    input_summary TEXT,
                    input_token_count INTEGER DEFAULT 0,
                    context_sources TEXT,
                    reasoning_summary TEXT,
                    alternatives_considered TEXT,
                    selected_action TEXT,
                    confidence_score REAL DEFAULT 0.0,
                    rules_applied TEXT,
                    output_hash TEXT,
                    output_summary TEXT,
                    output_token_count INTEGER DEFAULT 0,
                    verification_status TEXT DEFAULT 'pending',
                    verifier_ids TEXT,
                    verification_scores TEXT,
                    source_documents TEXT,
                    parent_entry_id TEXT,
                    child_entry_ids TEXT,
                    previous_entry_hash TEXT,
                    entry_hash TEXT,
                    metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for common queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON audit_entries(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_id
                ON audit_entries(session_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent_id
                ON audit_entries(agent_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_decision_type
                ON audit_entries(decision_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_verification_status
                ON audit_entries(verification_status)
            """)

    def _entry_to_row(self, entry: AuditEntry) -> Dict[str, Any]:
        """Convert entry to database row."""
        return {
            "entry_id": entry.entry_id,
            "timestamp": entry.timestamp.isoformat(),
            "session_id": entry.session_id,
            "conversation_id": entry.conversation_id,
            "decision_type": entry.decision_type.value,
            "agent_id": entry.agent_id,
            "model_name": entry.model_name,
            "model_version": entry.model_version,
            "input_hash": entry.input_hash,
            "input_summary": entry.input_summary,
            "input_token_count": entry.input_token_count,
            "context_sources": json.dumps(entry.context_sources),
            "reasoning_summary": entry.reasoning_summary,
            "alternatives_considered": json.dumps(entry.alternatives_considered),
            "selected_action": entry.selected_action,
            "confidence_score": entry.confidence_score,
            "rules_applied": json.dumps(entry.rules_applied),
            "output_hash": entry.output_hash,
            "output_summary": entry.output_summary,
            "output_token_count": entry.output_token_count,
            "verification_status": entry.verification_status.value,
            "verifier_ids": json.dumps(entry.verifier_ids),
            "verification_scores": json.dumps(entry.verification_scores),
            "source_documents": json.dumps(entry.source_documents),
            "parent_entry_id": entry.parent_entry_id,
            "child_entry_ids": json.dumps(entry.child_entry_ids),
            "previous_entry_hash": entry.previous_entry_hash,
            "entry_hash": entry.entry_hash,
            "metadata": json.dumps(entry.metadata),
        }

    def _row_to_entry(self, row: sqlite3.Row) -> AuditEntry:
        """Convert database row to entry."""
        data = dict(row)

        # Parse JSON fields
        for field in ["context_sources", "alternatives_considered", "rules_applied",
                      "verifier_ids", "verification_scores", "source_documents",
                      "child_entry_ids", "metadata"]:
            if data.get(field):
                try:
                    data[field] = json.loads(data[field])
                except json.JSONDecodeError:
                    data[field] = []

        return AuditEntry.from_dict(data)

    def store(self, entry: AuditEntry) -> None:
        """Store an audit entry."""
        row = self._entry_to_row(entry)

        with self._get_connection() as conn:
            placeholders = ", ".join(["?" for _ in row])
            columns = ", ".join(row.keys())
            values = list(row.values())

            conn.execute(
                f"INSERT OR REPLACE INTO audit_entries ({columns}) VALUES ({placeholders})",
                values,
            )

    def get(self, entry_id: str) -> Optional[AuditEntry]:
        """Retrieve an entry by ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM audit_entries WHERE entry_id = ?",
                (entry_id,),
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_entry(row)
        return None

    def get_all_entries(self) -> List[AuditEntry]:
        """Get all entries in chronological order."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM audit_entries ORDER BY timestamp ASC"
            )
            return [self._row_to_entry(row) for row in cursor.fetchall()]

    def get_entries_in_range(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> List[AuditEntry]:
        """Get entries within a date range."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """SELECT * FROM audit_entries
                   WHERE timestamp >= ? AND timestamp <= ?
                   ORDER BY timestamp ASC""",
                (start_date.isoformat(), end_date.isoformat()),
            )
            return [self._row_to_entry(row) for row in cursor.fetchall()]

    def get_latest_hash(self) -> str:
        """Get the hash of the most recent entry."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT entry_hash FROM audit_entries ORDER BY timestamp DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if row:
                return row["entry_hash"] or ""
        return ""

    def get_entries_by_session(self, session_id: str) -> List[AuditEntry]:
        """Get entries for a specific session."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM audit_entries WHERE session_id = ? ORDER BY timestamp ASC",
                (session_id,),
            )
            return [self._row_to_entry(row) for row in cursor.fetchall()]

    def get_entries_by_agent(self, agent_id: str) -> List[AuditEntry]:
        """Get entries for a specific agent."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM audit_entries WHERE agent_id = ? ORDER BY timestamp ASC",
                (agent_id,),
            )
            return [self._row_to_entry(row) for row in cursor.fetchall()]

    def get_entries_by_type(self, decision_type: DecisionType) -> List[AuditEntry]:
        """Get entries of a specific decision type."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM audit_entries WHERE decision_type = ? ORDER BY timestamp ASC",
                (decision_type.value,),
            )
            return [self._row_to_entry(row) for row in cursor.fetchall()]

    def get_entries_by_verification_status(
        self,
        status: VerificationStatus,
    ) -> List[AuditEntry]:
        """Get entries with specific verification status."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM audit_entries WHERE verification_status = ? ORDER BY timestamp ASC",
                (status.value,),
            )
            return [self._row_to_entry(row) for row in cursor.fetchall()]

    def count(self) -> int:
        """Get total number of entries."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) as count FROM audit_entries")
            return cursor.fetchone()["count"]

    def clear(self) -> None:
        """Clear all entries (use with caution)."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM audit_entries")


class MemoryStorageBackend(StorageBackend):
    """
    In-memory storage backend for testing.

    Stores entries in memory without persistence.
    """

    def __init__(self):
        """Initialize in-memory storage."""
        self._entries: List[AuditEntry] = []
        self._index: Dict[str, int] = {}

    def store(self, entry: AuditEntry) -> None:
        """Store an audit entry."""
        self._index[entry.entry_id] = len(self._entries)
        self._entries.append(entry)

    def get(self, entry_id: str) -> Optional[AuditEntry]:
        """Retrieve an entry by ID."""
        idx = self._index.get(entry_id)
        if idx is not None:
            return self._entries[idx]
        return None

    def get_all_entries(self) -> List[AuditEntry]:
        """Get all entries in chronological order."""
        return sorted(self._entries, key=lambda e: e.timestamp)

    def get_entries_in_range(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> List[AuditEntry]:
        """Get entries within a date range."""
        return [
            e for e in self._entries
            if start_date <= e.timestamp <= end_date
        ]

    def get_latest_hash(self) -> str:
        """Get the hash of the most recent entry."""
        if not self._entries:
            return ""
        entries = sorted(self._entries, key=lambda e: e.timestamp)
        return entries[-1].entry_hash

    def get_entries_by_session(self, session_id: str) -> List[AuditEntry]:
        """Get entries for a specific session."""
        return [e for e in self._entries if e.session_id == session_id]

    def get_entries_by_agent(self, agent_id: str) -> List[AuditEntry]:
        """Get entries for a specific agent."""
        return [e for e in self._entries if e.agent_id == agent_id]

    def get_entries_by_type(self, decision_type: DecisionType) -> List[AuditEntry]:
        """Get entries of a specific decision type."""
        return [e for e in self._entries if e.decision_type == decision_type]

    def count(self) -> int:
        """Get total number of entries."""
        return len(self._entries)

    def clear(self) -> None:
        """Clear all entries."""
        self._entries.clear()
        self._index.clear()
