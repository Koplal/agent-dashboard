"""
Knowledge Graph Storage Backends.

Provides storage implementations for the knowledge graph,
including in-memory (testing) and SQLite (lightweight production).

Supports both synchronous and asynchronous operations for flexibility.
Use sync methods for simple scripts, async for high-concurrency services.

Version: 2.7.0
"""

import json
import math
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple

# Optional async imports
try:
    import aiosqlite
    ASYNC_AVAILABLE = True
except ImportError:
    aiosqlite = None
    ASYNC_AVAILABLE = False

from .graph import (
    GraphStorageBackend,
    KGClaim,
    Source,
    Entity,
    EntityType,
    RelationType,
    utc_now,
)


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


class MemoryGraphBackend(GraphStorageBackend):
    """
    In-memory knowledge graph storage for testing.

    Stores all data in dictionaries, supports all graph operations
    but does not persist across restarts.
    """

    def __init__(self):
        """Initialize empty storage."""
        self.claims: Dict[str, KGClaim] = {}
        self.sources: Dict[str, Source] = {}
        self.entities: Dict[Tuple[str, EntityType], Entity] = {}
        self.topics: Set[str] = set()
        self.sessions: Set[str] = set()

        # Relationships: (from_id, to_id, type) -> metadata
        self.relationships: Dict[Tuple[str, str, RelationType], Dict[str, Any]] = {}

        # Indexes
        self.claims_by_source: Dict[str, List[str]] = defaultdict(list)
        self.claims_by_entity: Dict[Tuple[str, EntityType], List[str]] = defaultdict(list)
        self.claims_by_topic: Dict[str, List[str]] = defaultdict(list)
        self.claims_by_session: Dict[str, List[str]] = defaultdict(list)

    def store_claim(self, claim: KGClaim) -> str:
        """Store a claim with its relationships."""
        self.claims[claim.claim_id] = claim

        # Index by source
        self.claims_by_source[claim.source_url].append(claim.claim_id)

        # Store source if new
        if claim.source_url not in self.sources:
            source = Source(
                url=claim.source_url,
                title=claim.source_title,
                publication_date=claim.publication_date,
            )
            self.store_source(source)

        # Create source relationship
        self.add_relationship(
            claim.claim_id,
            claim.source_url,
            RelationType.SOURCED_FROM,
            {"extraction_date": utc_now().isoformat(), "agent_id": claim.agent_id},
        )

        # Store and index entities
        for entity in claim.entities:
            key = (entity.name, entity.entity_type)
            self.entities[key] = entity
            self.claims_by_entity[key].append(claim.claim_id)
            self.add_relationship(claim.claim_id, f"entity:{entity.name}", RelationType.MENTIONS)

        # Store and index topics
        for topic in claim.topics:
            self.topics.add(topic)
            self.claims_by_topic[topic].append(claim.claim_id)
            self.add_relationship(claim.claim_id, f"topic:{topic}", RelationType.ABOUT)

        # Store session
        if claim.session_id:
            self.sessions.add(claim.session_id)
            self.claims_by_session[claim.session_id].append(claim.claim_id)
            self.add_relationship(claim.claim_id, f"session:{claim.session_id}", RelationType.GENERATED_IN)

        return claim.claim_id

    def get_claim(self, claim_id: str) -> Optional[KGClaim]:
        """Get a claim by ID."""
        return self.claims.get(claim_id)

    def store_source(self, source: Source) -> str:
        """Store or update a source."""
        self.sources[source.url] = source
        return source.url

    def get_source(self, url: str) -> Optional[Source]:
        """Get a source by URL."""
        return self.sources.get(url)

    def add_relationship(
        self,
        from_id: str,
        to_id: str,
        relation_type: RelationType,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Add a relationship between nodes."""
        key = (from_id, to_id, relation_type)
        self.relationships[key] = metadata or {}
        return True

    def find_claims_by_embedding(
        self,
        embedding: List[float],
        limit: int = 10,
        min_similarity: float = 0.5,
    ) -> List[Tuple[KGClaim, float]]:
        """Find claims by embedding similarity."""
        results = []

        for claim in self.claims.values():
            if claim.embedding:
                similarity = cosine_similarity(embedding, claim.embedding)
                if similarity >= min_similarity:
                    results.append((claim, similarity))

        # Sort by similarity descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def find_claims_by_entity(
        self,
        entity_name: str,
        entity_type: Optional[EntityType] = None,
    ) -> List[KGClaim]:
        """Find claims mentioning an entity."""
        if entity_type:
            key = (entity_name, entity_type)
            claim_ids = self.claims_by_entity.get(key, [])
        else:
            # Search across all entity types
            claim_ids = []
            for (name, _), ids in self.claims_by_entity.items():
                if name.lower() == entity_name.lower():
                    claim_ids.extend(ids)

        return [self.claims[cid] for cid in claim_ids if cid in self.claims]

    def find_claims_by_topic(self, topic: str) -> List[KGClaim]:
        """Find claims about a topic."""
        claim_ids = self.claims_by_topic.get(topic, [])
        return [self.claims[cid] for cid in claim_ids if cid in self.claims]

    def find_claims_by_session(self, session_id: str) -> List[KGClaim]:
        """Find claims from a session."""
        claim_ids = self.claims_by_session.get(session_id, [])
        return [self.claims[cid] for cid in claim_ids if cid in self.claims]

    def get_provenance_chain(self, claim_id: str, max_depth: int = 5) -> List[Dict[str, Any]]:
        """Trace claim back to its sources."""
        chain = []
        visited = set()

        def traverse(node_id: str, depth: int):
            if depth > max_depth or node_id in visited:
                return
            visited.add(node_id)

            # Check if it's a claim
            if node_id in self.claims:
                claim = self.claims[node_id]
                chain.append({
                    "type": "claim",
                    "id": node_id,
                    "text": claim.text,
                    "confidence": claim.confidence,
                })

            # Check if it's a source
            elif node_id in self.sources:
                source = self.sources[node_id]
                chain.append({
                    "type": "source",
                    "url": source.url,
                    "title": source.title,
                })

            # Follow SOURCED_FROM and DERIVED_FROM relationships
            for (from_id, to_id, rel_type), _ in self.relationships.items():
                if from_id == node_id and rel_type in (RelationType.SOURCED_FROM, RelationType.DERIVED_FROM):
                    traverse(to_id, depth + 1)

        traverse(claim_id, 0)
        return chain

    def get_related_claims(
        self,
        claim_id: str,
        max_hops: int = 2,
    ) -> List[Tuple[KGClaim, int]]:
        """Get claims related through shared entities."""
        claim = self.claims.get(claim_id)
        if not claim:
            return []

        related = {}  # claim_id -> min_hops

        # Get claims sharing entities
        for entity in claim.entities:
            key = (entity.name, entity.entity_type)
            for other_id in self.claims_by_entity.get(key, []):
                if other_id != claim_id:
                    if other_id not in related or related[other_id] > 1:
                        related[other_id] = 1

        # Get claims sharing topics
        for topic in claim.topics:
            for other_id in self.claims_by_topic.get(topic, []):
                if other_id != claim_id:
                    if other_id not in related or related[other_id] > 1:
                        related[other_id] = 1

        # For max_hops > 1, expand to claims related to related claims
        if max_hops > 1:
            for other_id, hops in list(related.items()):
                if hops < max_hops:
                    other_claim = self.claims.get(other_id)
                    if other_claim:
                        for entity in other_claim.entities:
                            key = (entity.name, entity.entity_type)
                            for third_id in self.claims_by_entity.get(key, []):
                                if third_id != claim_id and third_id not in related:
                                    related[third_id] = hops + 1

        return [
            (self.claims[cid], hops)
            for cid, hops in related.items()
            if cid in self.claims
        ]

    def count_claims(self) -> int:
        """Count total claims."""
        return len(self.claims)

    def count_sources(self) -> int:
        """Count total sources."""
        return len(self.sources)

    def count_entities(self) -> int:
        """Count unique entities."""
        return len(self.entities)


class SQLiteGraphBackend(GraphStorageBackend):
    """
    SQLite-based knowledge graph storage.

    Provides persistent storage with efficient querying using
    relational tables to simulate graph operations.
    """

    def __init__(self, db_path: str):
        """
        Initialize SQLite storage.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                -- Claims table
                CREATE TABLE IF NOT EXISTS claims (
                    claim_id TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    confidence REAL DEFAULT 0.0,
                    source_url TEXT NOT NULL,
                    source_title TEXT,
                    publication_date TEXT,
                    agent_id TEXT,
                    session_id TEXT,
                    embedding TEXT,
                    created_at TEXT NOT NULL,
                    metadata TEXT
                );

                -- Sources table
                CREATE TABLE IF NOT EXISTS sources (
                    url TEXT PRIMARY KEY,
                    title TEXT,
                    publication_date TEXT,
                    author TEXT,
                    domain TEXT,
                    last_accessed TEXT,
                    metadata TEXT
                );

                -- Entities table (KG-002: added temporal fields)
                CREATE TABLE IF NOT EXISTS entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    metadata TEXT,
                    valid_from TEXT,
                    valid_to TEXT,
                    source_location TEXT,
                    UNIQUE(name, entity_type)
                );

                -- Topics table
                CREATE TABLE IF NOT EXISTS topics (
                    name TEXT PRIMARY KEY
                );

                -- Claim-Entity relationships
                CREATE TABLE IF NOT EXISTS claim_entities (
                    claim_id TEXT NOT NULL,
                    entity_id INTEGER NOT NULL,
                    FOREIGN KEY (claim_id) REFERENCES claims(claim_id),
                    FOREIGN KEY (entity_id) REFERENCES entities(id),
                    PRIMARY KEY (claim_id, entity_id)
                );

                -- Claim-Topic relationships
                CREATE TABLE IF NOT EXISTS claim_topics (
                    claim_id TEXT NOT NULL,
                    topic_name TEXT NOT NULL,
                    FOREIGN KEY (claim_id) REFERENCES claims(claim_id),
                    FOREIGN KEY (topic_name) REFERENCES topics(name),
                    PRIMARY KEY (claim_id, topic_name)
                );

                -- General relationships table
                CREATE TABLE IF NOT EXISTS relationships (
                    from_id TEXT NOT NULL,
                    to_id TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (from_id, to_id, relation_type)
                );

                -- Indexes
                CREATE INDEX IF NOT EXISTS idx_claims_source ON claims(source_url);
                CREATE INDEX IF NOT EXISTS idx_claims_session ON claims(session_id);
                CREATE INDEX IF NOT EXISTS idx_claims_created ON claims(created_at);
                CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
                CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
                CREATE INDEX IF NOT EXISTS idx_relationships_from ON relationships(from_id);
                CREATE INDEX IF NOT EXISTS idx_relationships_to ON relationships(to_id);
            """)

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def store_claim(self, claim: KGClaim) -> str:
        """Store a claim with its relationships."""
        with self._get_connection() as conn:
            # Insert claim
            conn.execute("""
                INSERT OR REPLACE INTO claims
                (claim_id, text, confidence, source_url, source_title,
                 publication_date, agent_id, session_id, embedding, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                claim.claim_id,
                claim.text,
                claim.confidence,
                claim.source_url,
                claim.source_title,
                claim.publication_date.isoformat() if claim.publication_date else None,
                claim.agent_id,
                claim.session_id,
                json.dumps(claim.embedding) if claim.embedding else None,
                claim.created_at.isoformat(),
                json.dumps(claim.metadata),
            ))

            # Store source if new
            conn.execute("""
                INSERT OR IGNORE INTO sources (url, title, publication_date, last_accessed, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (
                claim.source_url,
                claim.source_title,
                claim.publication_date.isoformat() if claim.publication_date else None,
                utc_now().isoformat(),
                "{}",
            ))

            # Store and link entities (KG-002: include temporal fields)
            for entity in claim.entities:
                conn.execute("""
                    INSERT OR IGNORE INTO entities
                    (name, entity_type, metadata, valid_from, valid_to, source_location)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    entity.name,
                    entity.entity_type.value,
                    json.dumps(entity.metadata),
                    entity.valid_from.isoformat() if entity.valid_from else None,
                    entity.valid_to.isoformat() if entity.valid_to else None,
                    entity.source_location,
                ))

                cursor = conn.execute(
                    "SELECT id FROM entities WHERE name = ? AND entity_type = ?",
                    (entity.name, entity.entity_type.value)
                )
                entity_id = cursor.fetchone()[0]

                conn.execute("""
                    INSERT OR IGNORE INTO claim_entities (claim_id, entity_id)
                    VALUES (?, ?)
                """, (claim.claim_id, entity_id))

            # Store and link topics
            for topic in claim.topics:
                conn.execute("INSERT OR IGNORE INTO topics (name) VALUES (?)", (topic,))
                conn.execute("""
                    INSERT OR IGNORE INTO claim_topics (claim_id, topic_name)
                    VALUES (?, ?)
                """, (claim.claim_id, topic))

            # Store source relationship
            conn.execute("""
                INSERT OR REPLACE INTO relationships
                (from_id, to_id, relation_type, metadata, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                claim.claim_id,
                claim.source_url,
                RelationType.SOURCED_FROM.value,
                json.dumps({"agent_id": claim.agent_id}),
                utc_now().isoformat(),
            ))

        return claim.claim_id

    def get_claim(self, claim_id: str) -> Optional[KGClaim]:
        """Get a claim by ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM claims WHERE claim_id = ?",
                (claim_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None

            # Get entities (KG-002: include temporal fields)
            entity_cursor = conn.execute("""
                SELECT e.name, e.entity_type, e.metadata,
                       e.valid_from, e.valid_to, e.source_location
                FROM entities e
                JOIN claim_entities ce ON e.id = ce.entity_id
                WHERE ce.claim_id = ?
            """, (claim_id,))
            entities = [
                Entity(
                    name=r["name"],
                    entity_type=EntityType(r["entity_type"]),
                    metadata=json.loads(r["metadata"]) if r["metadata"] else {},
                    valid_from=datetime.fromisoformat(r["valid_from"]) if r["valid_from"] else None,
                    valid_to=datetime.fromisoformat(r["valid_to"]) if r["valid_to"] else None,
                    source_location=r["source_location"],
                )
                for r in entity_cursor
            ]

            # Get topics
            topic_cursor = conn.execute(
                "SELECT topic_name FROM claim_topics WHERE claim_id = ?",
                (claim_id,)
            )
            topics = [r["topic_name"] for r in topic_cursor]

            return KGClaim(
                claim_id=row["claim_id"],
                text=row["text"],
                confidence=row["confidence"],
                source_url=row["source_url"],
                source_title=row["source_title"] or "",
                publication_date=datetime.fromisoformat(row["publication_date"]) if row["publication_date"] else None,
                agent_id=row["agent_id"] or "",
                session_id=row["session_id"] or "",
                embedding=json.loads(row["embedding"]) if row["embedding"] else None,
                created_at=datetime.fromisoformat(row["created_at"]),
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                entities=entities,
                topics=topics,
            )

    def store_source(self, source: Source) -> str:
        """Store or update a source."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO sources
                (url, title, publication_date, author, domain, last_accessed, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                source.url,
                source.title,
                source.publication_date.isoformat() if source.publication_date else None,
                source.author,
                source.domain,
                source.last_accessed.isoformat(),
                json.dumps(source.metadata),
            ))
        return source.url

    def get_source(self, url: str) -> Optional[Source]:
        """Get a source by URL."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM sources WHERE url = ?", (url,))
            row = cursor.fetchone()
            if not row:
                return None

            return Source(
                url=row["url"],
                title=row["title"] or "",
                publication_date=datetime.fromisoformat(row["publication_date"]) if row["publication_date"] else None,
                author=row["author"] or "",
                domain=row["domain"] or "",
                last_accessed=datetime.fromisoformat(row["last_accessed"]) if row["last_accessed"] else utc_now(),
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            )

    def add_relationship(
        self,
        from_id: str,
        to_id: str,
        relation_type: RelationType,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Add a relationship between nodes."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO relationships
                (from_id, to_id, relation_type, metadata, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                from_id,
                to_id,
                relation_type.value,
                json.dumps(metadata or {}),
                utc_now().isoformat(),
            ))
        return True

    def find_claims_by_embedding(
        self,
        embedding: List[float],
        limit: int = 10,
        min_similarity: float = 0.5,
    ) -> List[Tuple[KGClaim, float]]:
        """Find claims by embedding similarity."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT claim_id, embedding FROM claims WHERE embedding IS NOT NULL")
            results = []

            for row in cursor:
                stored_embedding = json.loads(row["embedding"])
                similarity = cosine_similarity(embedding, stored_embedding)
                if similarity >= min_similarity:
                    claim = self.get_claim(row["claim_id"])
                    if claim:
                        results.append((claim, similarity))

            results.sort(key=lambda x: x[1], reverse=True)
            return results[:limit]

    def find_claims_by_entity(
        self,
        entity_name: str,
        entity_type: Optional[EntityType] = None,
    ) -> List[KGClaim]:
        """Find claims mentioning an entity."""
        with self._get_connection() as conn:
            if entity_type:
                cursor = conn.execute("""
                    SELECT DISTINCT ce.claim_id
                    FROM claim_entities ce
                    JOIN entities e ON ce.entity_id = e.id
                    WHERE e.name = ? AND e.entity_type = ?
                """, (entity_name, entity_type.value))
            else:
                cursor = conn.execute("""
                    SELECT DISTINCT ce.claim_id
                    FROM claim_entities ce
                    JOIN entities e ON ce.entity_id = e.id
                    WHERE LOWER(e.name) = LOWER(?)
                """, (entity_name,))

            return [self.get_claim(row["claim_id"]) for row in cursor if self.get_claim(row["claim_id"])]

    def find_claims_by_topic(self, topic: str) -> List[KGClaim]:
        """Find claims about a topic."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT claim_id FROM claim_topics WHERE topic_name = ?",
                (topic,)
            )
            return [self.get_claim(row["claim_id"]) for row in cursor if self.get_claim(row["claim_id"])]

    def find_claims_by_session(self, session_id: str) -> List[KGClaim]:
        """Find claims from a session."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT claim_id FROM claims WHERE session_id = ?",
                (session_id,)
            )
            return [self.get_claim(row["claim_id"]) for row in cursor if self.get_claim(row["claim_id"])]

    def get_provenance_chain(self, claim_id: str, max_depth: int = 5) -> List[Dict[str, Any]]:
        """Trace claim back to its sources."""
        chain = []
        visited = set()

        def traverse(node_id: str, depth: int):
            if depth > max_depth or node_id in visited:
                return
            visited.add(node_id)

            with self._get_connection() as conn:
                # Check if it's a claim
                cursor = conn.execute(
                    "SELECT claim_id, text, confidence FROM claims WHERE claim_id = ?",
                    (node_id,)
                )
                row = cursor.fetchone()
                if row:
                    chain.append({
                        "type": "claim",
                        "id": row["claim_id"],
                        "text": row["text"],
                        "confidence": row["confidence"],
                    })
                else:
                    # Check if it's a source
                    cursor = conn.execute(
                        "SELECT url, title FROM sources WHERE url = ?",
                        (node_id,)
                    )
                    row = cursor.fetchone()
                    if row:
                        chain.append({
                            "type": "source",
                            "url": row["url"],
                            "title": row["title"],
                        })

                # Follow relationships
                cursor = conn.execute("""
                    SELECT to_id FROM relationships
                    WHERE from_id = ? AND relation_type IN (?, ?)
                """, (node_id, RelationType.SOURCED_FROM.value, RelationType.DERIVED_FROM.value))

                for row in cursor:
                    traverse(row["to_id"], depth + 1)

        traverse(claim_id, 0)
        return chain

    def get_related_claims(
        self,
        claim_id: str,
        max_hops: int = 2,
    ) -> List[Tuple[KGClaim, int]]:
        """Get claims related through shared entities."""
        with self._get_connection() as conn:
            # Get claims sharing entities (1 hop)
            cursor = conn.execute("""
                SELECT DISTINCT ce2.claim_id, 1 as hops
                FROM claim_entities ce1
                JOIN claim_entities ce2 ON ce1.entity_id = ce2.entity_id
                WHERE ce1.claim_id = ? AND ce2.claim_id != ?
            """, (claim_id, claim_id))

            related = {row["claim_id"]: row["hops"] for row in cursor}

            # Get claims sharing topics
            cursor = conn.execute("""
                SELECT DISTINCT ct2.claim_id, 1 as hops
                FROM claim_topics ct1
                JOIN claim_topics ct2 ON ct1.topic_name = ct2.topic_name
                WHERE ct1.claim_id = ? AND ct2.claim_id != ?
            """, (claim_id, claim_id))

            for row in cursor:
                if row["claim_id"] not in related:
                    related[row["claim_id"]] = row["hops"]

            return [
                (self.get_claim(cid), hops)
                for cid, hops in related.items()
                if self.get_claim(cid)
            ]

    def count_claims(self) -> int:
        """Count total claims."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM claims")
            return cursor.fetchone()[0]

    def count_sources(self) -> int:
        """Count total sources."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM sources")
            return cursor.fetchone()[0]

    def count_entities(self) -> int:
        """Count unique entities."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM entities")
            return cursor.fetchone()[0]


    # ==================== ASYNC METHODS (P4-003) ====================

    _async_conn = None  # Class-level attribute for async connection

    def _check_async_available(self) -> None:
        """Check if async dependencies are available."""
        if not ASYNC_AVAILABLE:
            raise ImportError(
                "aiosqlite is required for async operations. "
                "Install with: pip install aiosqlite"
            )

    async def _get_async_connection(self):
        """Get async database connection."""
        self._check_async_available()
        if self._async_conn is None:
            self._async_conn = await aiosqlite.connect(str(self.db_path))
            self._async_conn.row_factory = aiosqlite.Row
        return self._async_conn

    async def store_claim_async(self, claim: KGClaim) -> str:
        """Store a claim asynchronously."""
        conn = await self._get_async_connection()
        await conn.execute(
            "INSERT OR REPLACE INTO claims "
            "(claim_id, text, confidence, source_url, source_title, "
            "publication_date, agent_id, session_id, embedding, created_at, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (claim.claim_id, claim.text, claim.confidence, claim.source_url,
             claim.source_title,
             claim.publication_date.isoformat() if claim.publication_date else None,
             claim.agent_id, claim.session_id,
             json.dumps(claim.embedding) if claim.embedding else None,
             claim.created_at.isoformat(), json.dumps(claim.metadata)))

        await conn.execute(
            "INSERT OR IGNORE INTO sources (url, title, publication_date, last_accessed, metadata) "
            "VALUES (?, ?, ?, ?, ?)",
            (claim.source_url, claim.source_title,
             claim.publication_date.isoformat() if claim.publication_date else None,
             utc_now().isoformat(), "{}"))

        for entity in claim.entities:
            await conn.execute(
                "INSERT OR IGNORE INTO entities "
                "(name, entity_type, metadata, valid_from, valid_to, source_location) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (entity.name, entity.entity_type.value, json.dumps(entity.metadata),
                 entity.valid_from.isoformat() if entity.valid_from else None,
                 entity.valid_to.isoformat() if entity.valid_to else None,
                 entity.source_location))
            cursor = await conn.execute(
                "SELECT id FROM entities WHERE name = ? AND entity_type = ?",
                (entity.name, entity.entity_type.value))
            row = await cursor.fetchone()
            await conn.execute(
                "INSERT OR IGNORE INTO claim_entities (claim_id, entity_id) VALUES (?, ?)",
                (claim.claim_id, row[0]))

        for topic in claim.topics:
            await conn.execute("INSERT OR IGNORE INTO topics (name) VALUES (?)", (topic,))
            await conn.execute(
                "INSERT OR IGNORE INTO claim_topics (claim_id, topic_name) VALUES (?, ?)",
                (claim.claim_id, topic))

        await conn.execute(
            "INSERT OR REPLACE INTO relationships "
            "(from_id, to_id, relation_type, metadata, created_at) VALUES (?, ?, ?, ?, ?)",
            (claim.claim_id, claim.source_url, RelationType.SOURCED_FROM.value,
             json.dumps({"agent_id": claim.agent_id}), utc_now().isoformat()))

        await conn.commit()
        return claim.claim_id

    async def get_claim_async(self, claim_id: str) -> Optional[KGClaim]:
        """Get a claim asynchronously."""
        conn = await self._get_async_connection()
        cursor = await conn.execute("SELECT * FROM claims WHERE claim_id = ?", (claim_id,))
        row = await cursor.fetchone()
        if not row:
            return None

        entity_cursor = await conn.execute(
            "SELECT e.name, e.entity_type, e.metadata, e.valid_from, e.valid_to, e.source_location "
            "FROM entities e JOIN claim_entities ce ON e.id = ce.entity_id WHERE ce.claim_id = ?",
            (claim_id,))
        entity_rows = await entity_cursor.fetchall()
        entities = [
            Entity(name=r["name"], entity_type=EntityType(r["entity_type"]),
                   metadata=json.loads(r["metadata"]) if r["metadata"] else {},
                   valid_from=datetime.fromisoformat(r["valid_from"]) if r["valid_from"] else None,
                   valid_to=datetime.fromisoformat(r["valid_to"]) if r["valid_to"] else None,
                   source_location=r["source_location"])
            for r in entity_rows]

        topic_cursor = await conn.execute(
            "SELECT topic_name FROM claim_topics WHERE claim_id = ?", (claim_id,))
        topic_rows = await topic_cursor.fetchall()
        topics = [r["topic_name"] for r in topic_rows]

        return KGClaim(
            claim_id=row["claim_id"], text=row["text"], confidence=row["confidence"],
            source_url=row["source_url"], source_title=row["source_title"] or "",
            publication_date=datetime.fromisoformat(row["publication_date"]) if row["publication_date"] else None,
            agent_id=row["agent_id"] or "", session_id=row["session_id"] or "",
            embedding=json.loads(row["embedding"]) if row["embedding"] else None,
            created_at=datetime.fromisoformat(row["created_at"]),
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            entities=entities, topics=topics)

    async def find_claims_by_embedding_async(
        self, embedding: List[float], limit: int = 10, min_similarity: float = 0.5
    ) -> List[Tuple[KGClaim, float]]:
        """Find claims by embedding similarity asynchronously."""
        conn = await self._get_async_connection()
        cursor = await conn.execute(
            "SELECT claim_id, embedding FROM claims WHERE embedding IS NOT NULL")
        rows = await cursor.fetchall()
        results = []
        for row in rows:
            stored_embedding = json.loads(row["embedding"])
            similarity = cosine_similarity(embedding, stored_embedding)
            if similarity >= min_similarity:
                claim = await self.get_claim_async(row["claim_id"])
                if claim:
                    results.append((claim, similarity))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    async def close_async(self) -> None:
        """Close async connection."""
        if self._async_conn is not None:
            await self._async_conn.close()
            self._async_conn = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close_async()

    def close(self) -> None:
        """Close any open connections."""
        pass  # SQLite connections are closed after each operation
