"""
Rule Store.

Provides persistent storage for extracted rules with search capabilities.

Version: 2.6.0
"""

import json
import logging
import math
import re
import sqlite3
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .models import (
    ExtractedRule,
    LearningStats,
    RuleCategory,
    RuleMatch,
    RuleStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class SearchConfig:
    """Configuration for rule search."""
    use_semantic: bool = True
    keyword_weight: float = 0.4
    effectiveness_weight: float = 0.3
    recency_weight: float = 0.2
    category_weight: float = 0.1
    min_score: float = 0.1


class RuleStoreBackend(ABC):
    """Abstract base class for rule storage backends."""

    @abstractmethod
    def add(self, rule: ExtractedRule) -> None:
        """Add or update a rule."""
        ...

    @abstractmethod
    def get(self, rule_id: str) -> Optional[ExtractedRule]:
        """Get a rule by ID."""
        ...

    @abstractmethod
    def get_all(self) -> List[ExtractedRule]:
        """Get all rules."""
        ...

    @abstractmethod
    def update(self, rule: ExtractedRule) -> None:
        """Update an existing rule."""
        ...

    @abstractmethod
    def delete(self, rule_id: str) -> bool:
        """Delete a rule."""
        ...

    @abstractmethod
    def search(self, query: str, limit: int = 5) -> List[RuleMatch]:
        """Search for rules matching a query."""
        ...


class MemoryRuleStore(RuleStoreBackend):
    """In-memory rule storage for testing."""

    def __init__(self):
        """Initialize in-memory store."""
        self.rules: Dict[str, ExtractedRule] = {}

    def add(self, rule: ExtractedRule) -> None:
        """Add or update a rule."""
        # Check for similar existing rules
        similar = self._find_similar(rule)
        if similar:
            # Merge with existing rule
            similar.success_count += 1
            similar.confidence = min(1.0, similar.confidence * 1.1)
            self.rules[similar.id] = similar
        else:
            self.rules[rule.id] = rule

    def get(self, rule_id: str) -> Optional[ExtractedRule]:
        """Get a rule by ID."""
        return self.rules.get(rule_id)

    def get_all(self) -> List[ExtractedRule]:
        """Get all rules."""
        return list(self.rules.values())

    def update(self, rule: ExtractedRule) -> None:
        """Update an existing rule."""
        if rule.id in self.rules:
            self.rules[rule.id] = rule

    def delete(self, rule_id: str) -> bool:
        """Delete a rule."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            return True
        return False

    def search(self, query: str, limit: int = 5) -> List[RuleMatch]:
        """Search for rules matching a query."""
        matches = []
        query_lower = query.lower()
        query_words = set(query_lower.split())

        for rule in self.rules.values():
            if rule.status != RuleStatus.ACTIVE:
                continue

            score = self._calculate_score(rule, query_words)
            if score > 0.1:
                matches.append(RuleMatch(
                    rule=rule,
                    score=score,
                    match_reason=f"Keyword match with effectiveness {rule.effectiveness:.0%}",
                ))

        matches.sort(key=lambda m: m.score, reverse=True)
        return matches[:limit]

    def _calculate_score(self, rule: ExtractedRule, query_words: Set[str]) -> float:
        """Calculate relevance score for a rule."""
        condition_words = set(rule.condition.lower().split())
        recommendation_words = set(rule.recommendation.lower().split())
        all_rule_words = condition_words | recommendation_words

        # Keyword overlap
        overlap = len(query_words & all_rule_words)
        keyword_score = overlap / max(len(query_words), 1)

        # Effectiveness weighting
        effectiveness_score = rule.effectiveness

        # Combined score
        return (keyword_score * 0.5 + effectiveness_score * 0.5)

    def _find_similar(self, rule: ExtractedRule) -> Optional[ExtractedRule]:
        """Find a similar existing rule."""
        for existing in self.rules.values():
            if self._is_similar(existing, rule):
                return existing
        return None

    def _is_similar(self, rule1: ExtractedRule, rule2: ExtractedRule) -> bool:
        """Check if two rules are similar enough to merge."""
        # Simple similarity check based on word overlap
        words1 = set(rule1.condition.lower().split())
        words2 = set(rule2.condition.lower().split())

        if not words1 or not words2:
            return False

        overlap = len(words1 & words2)
        similarity = overlap / max(len(words1), len(words2))
        return similarity > 0.7


class SQLiteRuleStore(RuleStoreBackend):
    """SQLite-backed rule storage with semantic search."""

    def __init__(self, db_path: str = "./rules.db"):
        """
        Initialize SQLite store.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rules (
                    id TEXT PRIMARY KEY,
                    condition TEXT NOT NULL,
                    recommendation TEXT NOT NULL,
                    reasoning TEXT,
                    confidence REAL DEFAULT 0.7,
                    success_count INTEGER DEFAULT 1,
                    failure_count INTEGER DEFAULT 0,
                    source_task TEXT,
                    source_agent TEXT,
                    category TEXT DEFAULT 'general',
                    status TEXT DEFAULT 'active',
                    tags TEXT DEFAULT '[]',
                    created_at TEXT,
                    last_used TEXT,
                    metadata TEXT DEFAULT '{}'
                )
            """)

            # Create indexes for efficient search
            conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON rules(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON rules(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_created ON rules(created_at)")

            # Full-text search table
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS rules_fts USING fts5(
                    id,
                    condition,
                    recommendation,
                    reasoning,
                    tags,
                    content=rules,
                    content_rowid=rowid
                )
            """)

            # Triggers to keep FTS in sync
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS rules_ai AFTER INSERT ON rules BEGIN
                    INSERT INTO rules_fts(rowid, id, condition, recommendation, reasoning, tags)
                    VALUES (new.rowid, new.id, new.condition, new.recommendation, new.reasoning, new.tags);
                END
            """)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS rules_ad AFTER DELETE ON rules BEGIN
                    INSERT INTO rules_fts(rules_fts, rowid, id, condition, recommendation, reasoning, tags)
                    VALUES ('delete', old.rowid, old.id, old.condition, old.recommendation, old.reasoning, old.tags);
                END
            """)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS rules_au AFTER UPDATE ON rules BEGIN
                    INSERT INTO rules_fts(rules_fts, rowid, id, condition, recommendation, reasoning, tags)
                    VALUES ('delete', old.rowid, old.id, old.condition, old.recommendation, old.reasoning, old.tags);
                    INSERT INTO rules_fts(rowid, id, condition, recommendation, reasoning, tags)
                    VALUES (new.rowid, new.id, new.condition, new.recommendation, new.reasoning, new.tags);
                END
            """)

            conn.commit()

    def add(self, rule: ExtractedRule) -> None:
        """Add or update a rule."""
        # Check for similar existing rule
        similar = self._find_similar(rule)
        if similar:
            # Merge with existing rule
            similar.success_count += 1
            similar.confidence = min(1.0, similar.confidence * 1.1)
            self.update(similar)
            return

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO rules
                (id, condition, recommendation, reasoning, confidence,
                 success_count, failure_count, source_task, source_agent,
                 category, status, tags, created_at, last_used, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rule.id,
                rule.condition,
                rule.recommendation,
                rule.reasoning,
                rule.confidence,
                rule.success_count,
                rule.failure_count,
                rule.source_task,
                rule.source_agent,
                rule.category.value,
                rule.status.value,
                json.dumps(rule.tags),
                rule.created_at.isoformat(),
                rule.last_used.isoformat() if rule.last_used else None,
                json.dumps(rule.metadata),
            ))
            conn.commit()

    def get(self, rule_id: str) -> Optional[ExtractedRule]:
        """Get a rule by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM rules WHERE id = ?", (rule_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_rule(row)
        return None

    def get_all(self) -> List[ExtractedRule]:
        """Get all rules."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM rules ORDER BY created_at DESC")
            return [self._row_to_rule(row) for row in cursor.fetchall()]

    def update(self, rule: ExtractedRule) -> None:
        """Update an existing rule."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE rules SET
                    condition = ?,
                    recommendation = ?,
                    reasoning = ?,
                    confidence = ?,
                    success_count = ?,
                    failure_count = ?,
                    source_task = ?,
                    source_agent = ?,
                    category = ?,
                    status = ?,
                    tags = ?,
                    last_used = ?,
                    metadata = ?
                WHERE id = ?
            """, (
                rule.condition,
                rule.recommendation,
                rule.reasoning,
                rule.confidence,
                rule.success_count,
                rule.failure_count,
                rule.source_task,
                rule.source_agent,
                rule.category.value,
                rule.status.value,
                json.dumps(rule.tags),
                rule.last_used.isoformat() if rule.last_used else None,
                json.dumps(rule.metadata),
                rule.id,
            ))
            conn.commit()

    def delete(self, rule_id: str) -> bool:
        """Delete a rule."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
            conn.commit()
            return cursor.rowcount > 0

    def search(self, query: str, limit: int = 5) -> List[RuleMatch]:
        """
        Search for rules matching a query using FTS and scoring.

        Combines full-text search with effectiveness weighting.
        """
        matches = []

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Use FTS for initial matching
            fts_query = self._prepare_fts_query(query)

            try:
                cursor = conn.execute("""
                    SELECT r.*, bm25(rules_fts) as fts_score
                    FROM rules_fts
                    JOIN rules r ON rules_fts.id = r.id
                    WHERE rules_fts MATCH ? AND r.status = 'active'
                    ORDER BY bm25(rules_fts)
                    LIMIT ?
                """, (fts_query, limit * 2))  # Get extra for filtering

                for row in cursor.fetchall():
                    rule = self._row_to_rule(row)
                    fts_score = -row["fts_score"]  # BM25 returns negative

                    # Combine FTS score with effectiveness
                    score = self._calculate_final_score(rule, fts_score, query)

                    if score > 0.1:
                        matches.append(RuleMatch(
                            rule=rule,
                            score=score,
                            match_reason=self._generate_match_reason(rule, query),
                        ))
            except sqlite3.OperationalError:
                # FTS might fail, fall back to simple search
                matches = self._simple_search(query, limit)

        matches.sort(key=lambda m: m.score, reverse=True)
        return matches[:limit]

    def _prepare_fts_query(self, query: str) -> str:
        """Prepare query for FTS5."""
        # Escape special characters and add wildcards
        words = query.split()
        terms = []
        for word in words:
            # Escape special characters
            escaped = re.sub(r'[^\w\s]', '', word)
            if escaped:
                terms.append(f"{escaped}*")
        return " OR ".join(terms) if terms else "*"

    def _calculate_final_score(
        self,
        rule: ExtractedRule,
        fts_score: float,
        query: str,
    ) -> float:
        """Calculate final relevance score."""
        # Normalize FTS score (typically 0-10 range)
        normalized_fts = min(fts_score / 10.0, 1.0)

        # Effectiveness (already 0-1)
        effectiveness = rule.effectiveness

        # Recency score
        if rule.last_used:
            days_since_use = (datetime.now() - rule.last_used).days
            recency = max(0, 1 - (days_since_use / 90))  # Decay over 90 days
        else:
            recency = 0.5

        # Combine scores
        score = (
            normalized_fts * 0.4 +
            effectiveness * 0.4 +
            recency * 0.2
        )

        return score

    def _generate_match_reason(self, rule: ExtractedRule, query: str) -> str:
        """Generate a human-readable match reason."""
        parts = []

        if rule.is_reliable:
            parts.append(f"Reliable ({rule.total_applications} uses)")

        parts.append(f"{rule.effectiveness:.0%} effective")

        if rule.last_used:
            days_ago = (datetime.now() - rule.last_used).days
            if days_ago < 7:
                parts.append("recently used")

        return ", ".join(parts)

    def _simple_search(self, query: str, limit: int) -> List[RuleMatch]:
        """Fallback simple search without FTS."""
        matches = []
        query_words = set(query.lower().split())

        for rule in self.get_all():
            if rule.status != RuleStatus.ACTIVE:
                continue

            rule_words = set(
                rule.condition.lower().split() +
                rule.recommendation.lower().split()
            )

            overlap = len(query_words & rule_words)
            if overlap > 0:
                score = (overlap / len(query_words)) * rule.effectiveness
                matches.append(RuleMatch(
                    rule=rule,
                    score=score,
                    match_reason=f"Keyword match ({overlap} words)",
                ))

        return matches

    def _find_similar(self, rule: ExtractedRule) -> Optional[ExtractedRule]:
        """Find a similar existing rule."""
        # Use semantic similarity based on condition
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM rules WHERE status = 'active'"
            )

            for row in cursor.fetchall():
                existing = self._row_to_rule(row)
                if self._is_similar(existing, rule):
                    return existing

        return None

    def _is_similar(self, rule1: ExtractedRule, rule2: ExtractedRule) -> bool:
        """Check if two rules are similar enough to merge."""
        words1 = set(rule1.condition.lower().split())
        words2 = set(rule2.condition.lower().split())

        if not words1 or not words2:
            return False

        # Jaccard similarity
        overlap = len(words1 & words2)
        union = len(words1 | words2)
        similarity = overlap / union if union > 0 else 0

        return similarity > 0.6

    def _row_to_rule(self, row: sqlite3.Row) -> ExtractedRule:
        """Convert database row to ExtractedRule."""
        return ExtractedRule(
            id=row["id"],
            condition=row["condition"],
            recommendation=row["recommendation"],
            reasoning=row["reasoning"] or "",
            confidence=row["confidence"],
            success_count=row["success_count"],
            failure_count=row["failure_count"],
            source_task=row["source_task"] or "",
            source_agent=row["source_agent"] or "",
            category=RuleCategory(row["category"]),
            status=RuleStatus(row["status"]),
            tags=json.loads(row["tags"]) if row["tags"] else [],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
            last_used=datetime.fromisoformat(row["last_used"]) if row["last_used"] else None,
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )


class RuleStore:
    """
    High-level rule store with additional functionality.

    Wraps a storage backend and provides additional features like
    pruning, statistics, and export/import.
    """

    def __init__(
        self,
        backend: Optional[RuleStoreBackend] = None,
        db_path: str = "./rules.db",
    ):
        """
        Initialize the rule store.

        Args:
            backend: Storage backend (defaults to SQLite)
            db_path: Path to database file (if using SQLite)
        """
        self.backend = backend or SQLiteRuleStore(db_path)

    def add(self, rule: ExtractedRule) -> None:
        """Add or update a rule."""
        self.backend.add(rule)

    def get(self, rule_id: str) -> Optional[ExtractedRule]:
        """Get a rule by ID."""
        return self.backend.get(rule_id)

    def get_all(self) -> List[ExtractedRule]:
        """Get all rules."""
        return self.backend.get_all()

    def search(self, query: str, limit: int = 5) -> List[RuleMatch]:
        """Search for rules matching a query."""
        return self.backend.search(query, limit)

    def update_effectiveness(self, rule_id: str, success: bool) -> None:
        """Update rule based on new outcome."""
        rule = self.backend.get(rule_id)
        if rule:
            rule.record_application(success)
            self.backend.update(rule)

    def prune_ineffective(self, min_applications: int = 10, min_effectiveness: float = 0.4) -> List[str]:
        """
        Prune rules with poor effectiveness.

        Args:
            min_applications: Minimum applications before pruning
            min_effectiveness: Minimum effectiveness to keep

        Returns:
            List of pruned rule IDs
        """
        pruned = []
        for rule in self.backend.get_all():
            if rule.total_applications >= min_applications and rule.effectiveness < min_effectiveness:
                rule.status = RuleStatus.PRUNED
                self.backend.update(rule)
                pruned.append(rule.id)
                logger.info(f"Pruned rule {rule.id} (effectiveness: {rule.effectiveness:.0%})")
        return pruned

    def prune_stale(self, days: int = 90) -> List[str]:
        """
        Prune rules that haven't been used recently.

        Args:
            days: Days since last use to consider stale

        Returns:
            List of pruned rule IDs
        """
        pruned = []
        cutoff = datetime.now() - timedelta(days=days)

        for rule in self.backend.get_all():
            if rule.status == RuleStatus.ACTIVE:
                if rule.last_used and rule.last_used < cutoff:
                    rule.status = RuleStatus.DEPRECATED
                    self.backend.update(rule)
                    pruned.append(rule.id)
                    logger.info(f"Deprecated stale rule {rule.id}")
                elif not rule.last_used and rule.created_at < cutoff:
                    rule.status = RuleStatus.DEPRECATED
                    self.backend.update(rule)
                    pruned.append(rule.id)
                    logger.info(f"Deprecated unused rule {rule.id}")

        return pruned

    def get_stats(self) -> LearningStats:
        """Get learning statistics."""
        rules = self.backend.get_all()

        active_rules = [r for r in rules if r.status == RuleStatus.ACTIVE]
        pruned_rules = [r for r in rules if r.status == RuleStatus.PRUNED]

        total_applications = sum(r.total_applications for r in rules)
        avg_effectiveness = (
            sum(r.effectiveness for r in active_rules) / len(active_rules)
            if active_rules else 0.0
        )

        # Rules by category
        by_category = Counter(r.category.value for r in active_rules)

        # Recent extractions (last 7 days)
        week_ago = datetime.now() - timedelta(days=7)
        recent = sum(1 for r in rules if r.created_at >= week_ago)

        return LearningStats(
            total_rules=len(rules),
            active_rules=len(active_rules),
            pruned_rules=len(pruned_rules),
            total_applications=total_applications,
            average_effectiveness=avg_effectiveness,
            rules_by_category=dict(by_category),
            recent_extractions=recent,
        )

    def export_rules(self, filepath: str, only_active: bool = True) -> int:
        """
        Export rules to a JSON file.

        Args:
            filepath: Path to export file
            only_active: Only export active rules

        Returns:
            Number of rules exported
        """
        rules = self.backend.get_all()
        if only_active:
            rules = [r for r in rules if r.status == RuleStatus.ACTIVE]

        export_data = {
            "version": "2.6.0",
            "exported_at": datetime.now().isoformat(),
            "rule_count": len(rules),
            "rules": [r.to_dict() for r in rules],
        }

        with open(filepath, "w") as f:
            json.dump(export_data, f, indent=2)

        return len(rules)

    def import_rules(self, filepath: str, merge: bool = True) -> int:
        """
        Import rules from a JSON file.

        Args:
            filepath: Path to import file
            merge: If True, merge with existing; if False, replace

        Returns:
            Number of rules imported
        """
        with open(filepath, "r") as f:
            data = json.load(f)

        rules_data = data.get("rules", [])
        imported = 0

        for rule_data in rules_data:
            try:
                rule = ExtractedRule.from_dict(rule_data)
                if merge:
                    existing = self.backend.get(rule.id)
                    if existing:
                        # Keep the more successful version
                        if rule.effectiveness > existing.effectiveness:
                            self.backend.update(rule)
                            imported += 1
                    else:
                        self.backend.add(rule)
                        imported += 1
                else:
                    self.backend.add(rule)
                    imported += 1
            except Exception as e:
                logger.warning(f"Failed to import rule: {e}")

        return imported

    def get_by_category(self, category: RuleCategory) -> List[ExtractedRule]:
        """Get all rules in a category."""
        return [
            r for r in self.backend.get_all()
            if r.category == category and r.status == RuleStatus.ACTIVE
        ]

    def get_top_rules(self, limit: int = 10) -> List[ExtractedRule]:
        """Get top rules by effectiveness."""
        rules = [r for r in self.backend.get_all() if r.status == RuleStatus.ACTIVE]
        rules.sort(key=lambda r: (r.effectiveness, r.total_applications), reverse=True)
        return rules[:limit]
