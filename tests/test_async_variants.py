"""
Tests for P4-003: Async Variants.

Validates async methods work correctly and maintain parity with sync versions.
Tests are skipped if aiosqlite is not available.

Version: 2.7.0
"""

import pytest
import asyncio
from pathlib import Path
from typing import List


# Check if async dependencies are available
try:
    import aiosqlite
    import aiofiles
    ASYNC_DEPS_AVAILABLE = True
except ImportError:
    ASYNC_DEPS_AVAILABLE = False


class TestAsyncModuleAvailability:
    """Test that async functionality is properly exposed."""

    def test_async_available_flag_exists(self):
        """Storage module should have ASYNC_AVAILABLE flag."""
        from src.knowledge import storage
        assert hasattr(storage, "ASYNC_AVAILABLE"), "storage.ASYNC_AVAILABLE flag missing"

    def test_async_flag_reflects_imports(self):
        """ASYNC_AVAILABLE should reflect whether aiosqlite is importable."""
        from src.knowledge.storage import ASYNC_AVAILABLE
        assert ASYNC_AVAILABLE == ASYNC_DEPS_AVAILABLE

    def test_sqlite_backend_has_async_methods(self):
        """SQLiteGraphBackend should have async method variants."""
        from src.knowledge.storage import SQLiteGraphBackend
        
        # These methods should exist
        assert hasattr(SQLiteGraphBackend, "store_claim_async")
        assert hasattr(SQLiteGraphBackend, "get_claim_async")
        assert hasattr(SQLiteGraphBackend, "find_claims_by_embedding_async")
        assert hasattr(SQLiteGraphBackend, "close_async")


@pytest.mark.skipif(not ASYNC_DEPS_AVAILABLE, reason="aiosqlite not installed")
class TestAsyncStorage:
    """Test async storage operations."""

    @pytest.fixture
    def db_path(self, tmp_path):
        """Create temporary database path."""
        return str(tmp_path / "test_async.db")

    @pytest.fixture
    def sample_claim(self):
        """Create a sample claim for testing."""
        from src.knowledge.graph import KGClaim, Entity, EntityType
        from src.knowledge.manager import default_embedding_function
        
        return KGClaim(
            claim_id="async-test-claim-1",
            text="Python is used for machine learning applications",
            confidence=0.9,
            source_url="https://example.com/test",
            entities=[
                Entity(name="Python", entity_type=EntityType.TECHNOLOGY),
            ],
            topics=["artificial intelligence"],
            embedding=default_embedding_function("Python is used for machine learning"),
        )

    @pytest.mark.asyncio
    async def test_store_claim_async(self, db_path, sample_claim):
        """Async store works like sync store."""
        from src.knowledge.storage import SQLiteGraphBackend
        
        backend = SQLiteGraphBackend(db_path)
        try:
            claim_id = await backend.store_claim_async(sample_claim)
            assert claim_id == sample_claim.claim_id
        finally:
            await backend.close_async()

    @pytest.mark.asyncio
    async def test_get_claim_async(self, db_path, sample_claim):
        """Async get retrieves stored claims."""
        from src.knowledge.storage import SQLiteGraphBackend
        
        backend = SQLiteGraphBackend(db_path)
        try:
            await backend.store_claim_async(sample_claim)
            retrieved = await backend.get_claim_async(sample_claim.claim_id)
            
            assert retrieved is not None
            assert retrieved.text == sample_claim.text
            assert retrieved.claim_id == sample_claim.claim_id
        finally:
            await backend.close_async()

    @pytest.mark.asyncio
    async def test_get_nonexistent_claim_async(self, db_path):
        """Async get returns None for nonexistent claims."""
        from src.knowledge.storage import SQLiteGraphBackend
        
        backend = SQLiteGraphBackend(db_path)
        try:
            result = await backend.get_claim_async("nonexistent-id")
            assert result is None
        finally:
            await backend.close_async()


@pytest.mark.skipif(not ASYNC_DEPS_AVAILABLE, reason="aiosqlite not installed")
class TestAsyncSyncParity:
    """Verify async and sync methods produce same results."""

    @pytest.fixture
    def db_path(self, tmp_path):
        """Create temporary database path."""
        return str(tmp_path / "test_parity.db")

    @pytest.fixture
    def sample_claim(self):
        """Create a sample claim for testing."""
        from src.knowledge.graph import KGClaim, Entity, EntityType
        from src.knowledge.manager import default_embedding_function
        
        return KGClaim(
            claim_id="parity-test-claim",
            text="TensorFlow is a deep learning framework",
            confidence=0.85,
            source_url="https://example.com/test",
            entities=[
                Entity(name="TensorFlow", entity_type=EntityType.TECHNOLOGY),
            ],
            embedding=default_embedding_function("TensorFlow deep learning"),
        )

    @pytest.mark.asyncio
    async def test_store_retrieve_parity(self, db_path, sample_claim):
        """Sync store and async retrieve produce consistent results."""
        from src.knowledge.storage import SQLiteGraphBackend
        
        backend = SQLiteGraphBackend(db_path)
        try:
            sync_id = backend.store_claim(sample_claim)
            async_claim = await backend.get_claim_async(sync_id)
            
            assert async_claim is not None
            assert async_claim.text == sample_claim.text
            assert async_claim.claim_id == sync_id
        finally:
            await backend.close_async()


@pytest.mark.skipif(not ASYNC_DEPS_AVAILABLE, reason="aiosqlite not installed")
class TestAsyncContextManager:
    """Test async context manager support."""

    @pytest.fixture
    def db_path(self, tmp_path):
        """Create temporary database path."""
        return str(tmp_path / "test_context.db")

    @pytest.mark.asyncio
    async def test_context_manager_cleanup(self, db_path):
        """Context manager closes connection on exit."""
        from src.knowledge.storage import SQLiteGraphBackend
        from src.knowledge.graph import KGClaim
        
        claim = KGClaim(
            claim_id="context-test",
            text="Test claim",
            confidence=0.9,
            source_url="https://example.com",
        )
        
        async with SQLiteGraphBackend(db_path) as backend:
            await backend.store_claim_async(claim)
            result = await backend.get_claim_async("context-test")
            assert result is not None
        
        assert backend._async_conn is None
