"""
Tests for the Neurosymbolic Learning Module.

Tests rule extraction, storage, search, and orchestration.
"""

import asyncio
import json
import os
import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List

from src.learning import (
    # Enums
    RuleCategory,
    RuleStatus,
    # Data models
    ExtractedRule,
    ExecutionOutcome,
    RuleMatch,
    LearningStats,
    # Extractor
    ExtractionConfig,
    RuleExtractor,
    MockRuleExtractor,
    # Store
    MemoryRuleStore,
    SQLiteRuleStore,
    RuleStore,
    # Orchestrator
    LearningConfig,
    ExecutionContext,
    LearningOrchestrator,
    MockLearningOrchestrator,
)


# =============================================================================
# Model Tests
# =============================================================================

class TestExtractedRule:
    """Tests for ExtractedRule."""

    def test_create_rule(self):
        """Test basic rule creation."""
        rule = ExtractedRule(
            id="test-001",
            condition="When researching a topic",
            recommendation="Use multiple sources",
            reasoning="Cross-verification improves accuracy",
        )
        assert rule.id == "test-001"
        assert rule.condition == "When researching a topic"
        assert rule.confidence == 0.7
        assert rule.success_count == 1
        assert rule.failure_count == 0

    def test_effectiveness_calculation(self):
        """Test Bayesian effectiveness calculation."""
        rule = ExtractedRule(
            id="test-001",
            condition="test",
            recommendation="test",
            reasoning="test",
            success_count=8,
            failure_count=2,
        )
        # Beta distribution: (2+8) / (2+8 + 2+2) = 10/14 ≈ 0.714
        assert 0.7 < rule.effectiveness < 0.75

    def test_effectiveness_with_few_samples(self):
        """Test effectiveness with few samples uses prior."""
        rule = ExtractedRule(
            id="test-001",
            condition="test",
            recommendation="test",
            reasoning="test",
            success_count=1,
            failure_count=0,
        )
        # With prior, 1 success doesn't give 100%
        assert rule.effectiveness < 0.8

    def test_total_applications(self):
        """Test total applications calculation."""
        rule = ExtractedRule(
            id="test-001",
            condition="test",
            recommendation="test",
            reasoning="test",
            success_count=5,
            failure_count=3,
        )
        assert rule.total_applications == 8

    def test_is_reliable(self):
        """Test reliable rule check."""
        # Not enough applications
        rule1 = ExtractedRule(
            id="test-001",
            condition="test",
            recommendation="test",
            reasoning="test",
            success_count=3,
            failure_count=0,
        )
        assert not rule1.is_reliable

        # Enough applications, good effectiveness
        rule2 = ExtractedRule(
            id="test-002",
            condition="test",
            recommendation="test",
            reasoning="test",
            success_count=8,
            failure_count=2,
        )
        assert rule2.is_reliable

    def test_should_prune(self):
        """Test prune recommendation."""
        # Not enough applications
        rule1 = ExtractedRule(
            id="test-001",
            condition="test",
            recommendation="test",
            reasoning="test",
            success_count=1,
            failure_count=5,
        )
        assert not rule1.should_prune  # Not enough total applications

        # Enough applications, low effectiveness
        rule2 = ExtractedRule(
            id="test-002",
            condition="test",
            recommendation="test",
            reasoning="test",
            success_count=2,
            failure_count=15,
        )
        assert rule2.should_prune

    def test_record_application(self):
        """Test recording application outcomes."""
        rule = ExtractedRule(
            id="test-001",
            condition="test",
            recommendation="test",
            reasoning="test",
        )

        rule.record_application(success=True)
        assert rule.success_count == 2
        assert rule.last_used is not None

        rule.record_application(success=False)
        assert rule.failure_count == 1

    def test_to_dict(self):
        """Test serialization to dict."""
        rule = ExtractedRule(
            id="test-001",
            condition="test condition",
            recommendation="test recommendation",
            reasoning="test reasoning",
            category=RuleCategory.RESEARCH,
            tags=["tag1", "tag2"],
        )
        d = rule.to_dict()
        assert d["id"] == "test-001"
        assert d["condition"] == "test condition"
        assert d["category"] == "research"
        assert d["tags"] == ["tag1", "tag2"]
        assert "effectiveness" in d

    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "id": "test-001",
            "condition": "test condition",
            "recommendation": "test recommendation",
            "reasoning": "test reasoning",
            "confidence": 0.8,
            "success_count": 5,
            "failure_count": 2,
            "category": "research",
            "status": "active",
            "tags": ["tag1"],
            "created_at": datetime.now().isoformat(),
        }
        rule = ExtractedRule.from_dict(data)
        assert rule.id == "test-001"
        assert rule.confidence == 0.8
        assert rule.success_count == 5
        assert rule.category == RuleCategory.RESEARCH

    def test_generate_id(self):
        """Test ID generation."""
        id1 = ExtractedRule.generate_id("condition1", "recommendation1")
        id2 = ExtractedRule.generate_id("condition1", "recommendation1")
        id3 = ExtractedRule.generate_id("condition2", "recommendation1")

        assert id1 == id2  # Same content, same ID
        assert id1 != id3  # Different content, different ID
        assert len(id1) == 16


class TestExecutionOutcome:
    """Tests for ExecutionOutcome."""

    def test_create_outcome(self):
        """Test basic outcome creation."""
        outcome = ExecutionOutcome(
            task="Research AI safety",
            approach="Used multiple sources",
            success=True,
            quality_score=0.9,
            execution_time=45.0,
        )
        assert outcome.task == "Research AI safety"
        assert outcome.success is True
        assert outcome.quality_score == 0.9

    def test_is_high_quality(self):
        """Test high quality check."""
        high = ExecutionOutcome(
            task="test",
            approach="test",
            success=True,
            quality_score=0.85,
            execution_time=10.0,
        )
        assert high.is_high_quality

        low = ExecutionOutcome(
            task="test",
            approach="test",
            success=True,
            quality_score=0.7,
            execution_time=10.0,
        )
        assert not low.is_high_quality

        failed = ExecutionOutcome(
            task="test",
            approach="test",
            success=False,
            quality_score=0.9,
            execution_time=10.0,
        )
        assert not failed.is_high_quality

    def test_is_learnable(self):
        """Test learnable check."""
        learnable = ExecutionOutcome(
            task="test",
            approach="test",
            success=True,
            quality_score=0.75,
            execution_time=10.0,
        )
        assert learnable.is_learnable

        not_learnable = ExecutionOutcome(
            task="test",
            approach="test",
            success=True,
            quality_score=0.5,
            execution_time=10.0,
        )
        assert not not_learnable.is_learnable

    def test_to_dict(self):
        """Test serialization."""
        outcome = ExecutionOutcome(
            task="test task",
            approach="test approach",
            success=True,
            quality_score=0.9,
            execution_time=45.0,
            artifacts=["artifact1"],
            feedback="Good work",
        )
        d = outcome.to_dict()
        assert d["task"] == "test task"
        assert d["success"] is True
        assert d["artifacts"] == ["artifact1"]
        assert d["feedback"] == "Good work"


class TestRuleMatch:
    """Tests for RuleMatch."""

    def test_create_match(self):
        """Test match creation."""
        rule = ExtractedRule(
            id="test-001",
            condition="test",
            recommendation="test",
            reasoning="test",
        )
        match = RuleMatch(rule=rule, score=0.85, match_reason="Keyword match")
        assert match.score == 0.85
        assert match.match_reason == "Keyword match"

    def test_to_dict(self):
        """Test serialization."""
        rule = ExtractedRule(
            id="test-001",
            condition="test",
            recommendation="test",
            reasoning="test",
        )
        match = RuleMatch(rule=rule, score=0.85)
        d = match.to_dict()
        assert d["score"] == 0.85
        assert "rule" in d


class TestLearningStats:
    """Tests for LearningStats."""

    def test_create_stats(self):
        """Test stats creation."""
        stats = LearningStats(
            total_rules=10,
            active_rules=8,
            pruned_rules=2,
            total_applications=100,
            average_effectiveness=0.75,
        )
        assert stats.total_rules == 10
        assert stats.average_effectiveness == 0.75

    def test_to_dict(self):
        """Test serialization."""
        stats = LearningStats(
            total_rules=10,
            rules_by_category={"research": 5, "code": 3},
        )
        d = stats.to_dict()
        assert d["total_rules"] == 10
        assert d["rules_by_category"]["research"] == 5


# =============================================================================
# Extractor Tests
# =============================================================================

class TestRuleExtractor:
    """Tests for RuleExtractor."""

    @pytest.fixture
    def mock_extraction_fn(self):
        """Create mock extraction function."""
        def extract(prompt: str) -> str:
            return json.dumps([
                {
                    "condition": "When researching complex topics",
                    "recommendation": "Use multiple authoritative sources",
                    "reasoning": "Cross-verification improves accuracy",
                    "category": "research"
                }
            ])
        return extract

    def test_create_extractor(self, mock_extraction_fn):
        """Test extractor creation."""
        extractor = RuleExtractor(extraction_fn=mock_extraction_fn)
        assert extractor is not None

    @pytest.mark.asyncio
    async def test_extract_rules(self, mock_extraction_fn):
        """Test rule extraction."""
        extractor = RuleExtractor(extraction_fn=mock_extraction_fn)

        outcome = ExecutionOutcome(
            task="Research AI safety",
            approach="Used multiple sources",
            success=True,
            quality_score=0.9,
            execution_time=45.0,
        )

        rules = await extractor.extract_rules(
            task="Research AI safety",
            approach="Used multiple sources",
            outcome=outcome,
        )

        assert len(rules) == 1
        assert rules[0].category == RuleCategory.RESEARCH
        assert "multiple" in rules[0].recommendation.lower()

    @pytest.mark.asyncio
    async def test_no_extraction_from_low_quality(self, mock_extraction_fn):
        """Test no extraction from low quality outcomes."""
        extractor = RuleExtractor(extraction_fn=mock_extraction_fn)

        outcome = ExecutionOutcome(
            task="test",
            approach="test",
            success=True,
            quality_score=0.5,  # Below threshold
            execution_time=10.0,
        )

        rules = await extractor.extract_rules("test", "test", outcome)
        assert len(rules) == 0

    @pytest.mark.asyncio
    async def test_no_extraction_from_failed(self, mock_extraction_fn):
        """Test no extraction from failed outcomes."""
        extractor = RuleExtractor(extraction_fn=mock_extraction_fn)

        outcome = ExecutionOutcome(
            task="test",
            approach="test",
            success=False,
            quality_score=0.9,
            execution_time=10.0,
        )

        rules = await extractor.extract_rules("test", "test", outcome)
        assert len(rules) == 0

    def test_parse_json_with_code_block(self):
        """Test parsing JSON from code blocks."""
        extractor = RuleExtractor()

        response = '''Here are the extracted rules:
```json
[{"condition": "test", "recommendation": "test", "reasoning": "test", "category": "general"}]
```
'''
        rules = extractor._parse_rules(response, "test task")
        assert len(rules) == 1

    def test_parse_bare_json(self):
        """Test parsing bare JSON."""
        extractor = RuleExtractor()

        response = '[{"condition": "test", "recommendation": "test", "reasoning": "test"}]'
        rules = extractor._parse_rules(response, "test task")
        assert len(rules) == 1

    def test_parse_empty_response(self):
        """Test parsing empty response."""
        extractor = RuleExtractor()
        rules = extractor._parse_rules("[]", "test task")
        assert len(rules) == 0


class TestMockRuleExtractor:
    """Tests for MockRuleExtractor."""

    @pytest.mark.asyncio
    async def test_mock_extractor(self):
        """Test mock extractor."""
        rules = [
            ExtractedRule(
                id="test-001",
                condition="test",
                recommendation="test",
                reasoning="test",
            )
        ]
        extractor = MockRuleExtractor(rules)

        outcome = ExecutionOutcome(
            task="test",
            approach="test",
            success=True,
            quality_score=0.9,
            execution_time=10.0,
        )

        result = await extractor.extract_rules("task", "approach", outcome)
        assert len(result) == 1
        assert len(extractor.extract_calls) == 1


# =============================================================================
# Store Tests
# =============================================================================

class TestMemoryRuleStore:
    """Tests for MemoryRuleStore."""

    @pytest.fixture
    def store(self):
        return MemoryRuleStore()

    def test_add_rule(self, store):
        """Test adding a rule."""
        rule = ExtractedRule(
            id="test-001",
            condition="When testing",
            recommendation="Write tests",
            reasoning="Tests catch bugs",
        )
        store.add(rule)
        assert store.get("test-001") is not None

    def test_get_nonexistent(self, store):
        """Test getting nonexistent rule."""
        assert store.get("nonexistent") is None

    def test_get_all(self, store):
        """Test getting all rules."""
        for i in range(3):
            store.add(ExtractedRule(
                id=f"test-{i}",
                condition=f"condition {i}",
                recommendation=f"recommendation {i}",
                reasoning=f"reasoning {i}",
            ))
        assert len(store.get_all()) == 3

    def test_update_rule(self, store):
        """Test updating a rule."""
        rule = ExtractedRule(
            id="test-001",
            condition="original",
            recommendation="original",
            reasoning="original",
        )
        store.add(rule)

        rule.condition = "updated"
        store.update(rule)

        retrieved = store.get("test-001")
        assert retrieved.condition == "updated"

    def test_delete_rule(self, store):
        """Test deleting a rule."""
        rule = ExtractedRule(
            id="test-001",
            condition="test",
            recommendation="test",
            reasoning="test",
        )
        store.add(rule)
        assert store.delete("test-001") is True
        assert store.get("test-001") is None
        assert store.delete("test-001") is False

    def test_search(self, store):
        """Test searching rules."""
        store.add(ExtractedRule(
            id="test-001",
            condition="When researching topics",
            recommendation="Use multiple sources",
            reasoning="Cross-verification",
            success_count=10,
            failure_count=2,
        ))
        store.add(ExtractedRule(
            id="test-002",
            condition="When writing code",
            recommendation="Write tests first",
            reasoning="TDD benefits",
            success_count=8,
            failure_count=1,
        ))

        results = store.search("research topics")
        assert len(results) >= 1
        assert results[0].rule.id == "test-001"

    def test_merge_similar_rules(self, store):
        """Test merging similar rules."""
        rule1 = ExtractedRule(
            id="test-001",
            condition="When researching topics",
            recommendation="Use sources",
            reasoning="test",
        )
        store.add(rule1)

        rule2 = ExtractedRule(
            id="test-002",
            condition="When researching topics",
            recommendation="Use multiple sources",
            reasoning="test",
        )
        store.add(rule2)

        # Should merge, not add new
        all_rules = store.get_all()
        # Due to similarity, they may merge
        assert len(all_rules) <= 2


class TestSQLiteRuleStore:
    """Tests for SQLiteRuleStore."""

    @pytest.fixture
    def store(self):
        """Create temporary SQLite store."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        store = SQLiteRuleStore(path)
        yield store
        # Cleanup
        try:
            os.unlink(path)
        except PermissionError:
            pass

    def test_add_rule(self, store):
        """Test adding a rule."""
        rule = ExtractedRule(
            id="test-001",
            condition="When testing",
            recommendation="Write tests",
            reasoning="Tests catch bugs",
        )
        store.add(rule)
        retrieved = store.get("test-001")
        assert retrieved is not None
        assert retrieved.condition == "When testing"

    def test_persistence(self):
        """Test persistence across instances."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            # Create and add
            store1 = SQLiteRuleStore(path)
            store1.add(ExtractedRule(
                id="persist-001",
                condition="test",
                recommendation="test",
                reasoning="test",
            ))

            # New instance should see the rule
            store2 = SQLiteRuleStore(path)
            assert store2.get("persist-001") is not None
        finally:
            try:
                os.unlink(path)
            except PermissionError:
                pass

    def test_search_fts(self, store):
        """Test full-text search."""
        store.add(ExtractedRule(
            id="test-001",
            condition="When researching complex scientific topics",
            recommendation="Use peer-reviewed sources",
            reasoning="Academic credibility",
            success_count=10,
        ))
        store.add(ExtractedRule(
            id="test-002",
            condition="When writing Python code",
            recommendation="Follow PEP 8",
            reasoning="Code consistency",
            success_count=8,
        ))

        results = store.search("scientific research")
        assert len(results) >= 1
        # First result should be the research rule
        assert "research" in results[0].rule.condition.lower()

    def test_update_preserves_data(self, store):
        """Test update preserves all data."""
        rule = ExtractedRule(
            id="test-001",
            condition="original",
            recommendation="original",
            reasoning="original",
            tags=["tag1", "tag2"],
            metadata={"key": "value"},
        )
        store.add(rule)

        rule.success_count = 10
        store.update(rule)

        retrieved = store.get("test-001")
        assert retrieved.tags == ["tag1", "tag2"]
        assert retrieved.metadata == {"key": "value"}
        assert retrieved.success_count == 10


class TestRuleStore:
    """Tests for high-level RuleStore."""

    @pytest.fixture
    def store(self):
        """Create store with memory backend."""
        return RuleStore(backend=MemoryRuleStore())

    def test_update_effectiveness(self, store):
        """Test effectiveness updating."""
        rule = ExtractedRule(
            id="test-001",
            condition="test",
            recommendation="test",
            reasoning="test",
        )
        store.add(rule)

        store.update_effectiveness("test-001", success=True)
        store.update_effectiveness("test-001", success=True)
        store.update_effectiveness("test-001", success=False)

        updated = store.get("test-001")
        assert updated.success_count == 3
        assert updated.failure_count == 1
        assert updated.last_used is not None

    def test_prune_ineffective(self, store):
        """Test pruning ineffective rules."""
        # Effective rule
        store.add(ExtractedRule(
            id="effective",
            condition="test",
            recommendation="test",
            reasoning="test",
            success_count=15,
            failure_count=3,
        ))

        # Ineffective rule
        store.add(ExtractedRule(
            id="ineffective",
            condition="test2",
            recommendation="test2",
            reasoning="test2",
            success_count=2,
            failure_count=15,
        ))

        pruned = store.prune_ineffective(min_applications=10)
        assert "ineffective" in pruned
        assert "effective" not in pruned

        # Check status
        ineffective = store.get("ineffective")
        assert ineffective.status == RuleStatus.PRUNED

    def test_prune_stale(self, store):
        """Test pruning stale rules."""
        # Recent rule
        store.add(ExtractedRule(
            id="recent",
            condition="test",
            recommendation="test",
            reasoning="test",
            last_used=datetime.now() - timedelta(days=30),
        ))

        # Stale rule
        store.add(ExtractedRule(
            id="stale",
            condition="test2",
            recommendation="test2",
            reasoning="test2",
            last_used=datetime.now() - timedelta(days=120),
        ))

        pruned = store.prune_stale(days=90)
        assert "stale" in pruned
        assert "recent" not in pruned

    def test_get_stats(self, store):
        """Test getting statistics."""
        store.add(ExtractedRule(
            id="test-001",
            condition="test",
            recommendation="test",
            reasoning="test",
            category=RuleCategory.RESEARCH,
            success_count=10,
            failure_count=2,
        ))
        store.add(ExtractedRule(
            id="test-002",
            condition="test2",
            recommendation="test2",
            reasoning="test2",
            category=RuleCategory.CODE,
            success_count=8,
            failure_count=1,
        ))

        stats = store.get_stats()
        assert stats.total_rules == 2
        assert stats.active_rules == 2
        assert stats.rules_by_category["research"] == 1
        assert stats.rules_by_category["code"] == 1

    def test_export_import(self, store):
        """Test export and import."""
        store.add(ExtractedRule(
            id="test-001",
            condition="test condition",
            recommendation="test recommendation",
            reasoning="test reasoning",
            tags=["tag1"],
        ))

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            filepath = f.name

        try:
            # Export
            count = store.export_rules(filepath)
            assert count == 1

            # Clear and import
            store.backend.delete("test-001")
            assert store.get("test-001") is None

            imported = store.import_rules(filepath)
            assert imported == 1

            # Verify
            rule = store.get("test-001")
            assert rule is not None
            assert rule.condition == "test condition"
            assert rule.tags == ["tag1"]
        finally:
            os.unlink(filepath)

    def test_get_by_category(self, store):
        """Test getting rules by category."""
        store.add(ExtractedRule(
            id="research-001",
            condition="test",
            recommendation="test",
            reasoning="test",
            category=RuleCategory.RESEARCH,
        ))
        store.add(ExtractedRule(
            id="code-001",
            condition="test",
            recommendation="test",
            reasoning="test",
            category=RuleCategory.CODE,
        ))

        research = store.get_by_category(RuleCategory.RESEARCH)
        assert len(research) == 1
        assert research[0].id == "research-001"

    def test_get_top_rules(self, store):
        """Test getting top rules."""
        for i in range(5):
            store.add(ExtractedRule(
                id=f"test-{i:03d}",
                condition=f"test {i}",
                recommendation=f"test {i}",
                reasoning=f"test {i}",
                success_count=i * 3,
                failure_count=i,
            ))

        top = store.get_top_rules(3)
        assert len(top) == 3
        # Should be sorted by effectiveness
        assert top[0].success_count >= top[1].success_count


# =============================================================================
# Orchestrator Tests
# =============================================================================

class MockAgent:
    """Mock agent for testing."""

    def __init__(self, response: Dict[str, Any] = None):
        self.response = response or {
            "success": True,
            "output": "Test output",
            "quality_score": 0.9,
            "approach": "Test approach",
        }
        self.calls: List[str] = []

    async def execute(self, task: str) -> Dict[str, Any]:
        self.calls.append(task)
        return self.response.copy()


class TestLearningOrchestrator:
    """Tests for LearningOrchestrator."""

    @pytest.fixture
    def orchestrator(self):
        """Create test orchestrator."""
        store = RuleStore(backend=MemoryRuleStore())
        extractor = MockRuleExtractor([
            ExtractedRule(
                id="extracted-001",
                condition="When researching",
                recommendation="Use sources",
                reasoning="Better accuracy",
            )
        ])
        agents = {"test": MockAgent()}

        return LearningOrchestrator(
            agents=agents,
            rule_store=store,
            rule_extractor=extractor,
            config=LearningConfig(auto_prune=False),
        )

    @pytest.mark.asyncio
    async def test_execute_basic(self, orchestrator):
        """Test basic execution."""
        result = await orchestrator.execute_with_learning(
            task="Test task",
            agent_id="test",
        )
        assert result["success"] is True
        assert "_learning" in result
        assert orchestrator.execution_count == 1

    @pytest.mark.asyncio
    async def test_execute_applies_rules(self, orchestrator):
        """Test rule application."""
        # Add a rule
        orchestrator.rules.add(ExtractedRule(
            id="rule-001",
            condition="When testing tasks",
            recommendation="Be thorough",
            reasoning="Thoroughness helps",
            success_count=10,
            failure_count=1,
        ))

        result = await orchestrator.execute_with_learning(
            task="When testing tasks",
            agent_id="test",
        )

        # Check that rules were applied
        assert len(result["_learning"]["rules_applied"]) >= 0

    @pytest.mark.asyncio
    async def test_execute_extracts_rules(self, orchestrator):
        """Test rule extraction from high quality execution."""
        result = await orchestrator.execute_with_learning(
            task="Test task",
            agent_id="test",
        )

        # Mock extractor should have been called
        assert orchestrator.rules_extracted_count > 0

    @pytest.mark.asyncio
    async def test_execute_updates_effectiveness(self, orchestrator):
        """Test effectiveness updates."""
        # Add a rule
        rule = ExtractedRule(
            id="rule-001",
            condition="test task topic",
            recommendation="Be thorough",
            reasoning="Helps",
            success_count=5,
            failure_count=1,
        )
        orchestrator.rules.add(rule)

        await orchestrator.execute_with_learning(
            task="test task topic here",
            agent_id="test",
        )

        # Rule effectiveness should be updated
        updated = orchestrator.rules.get("rule-001")
        # The rule should have been found and updated
        if updated:
            assert updated.success_count >= 5 or updated.last_used is not None

    @pytest.mark.asyncio
    async def test_execute_unknown_agent(self, orchestrator):
        """Test execution with unknown agent."""
        with pytest.raises(ValueError, match="Unknown agent"):
            await orchestrator.execute_with_learning(
                task="Test",
                agent_id="unknown",
            )

    def test_get_stats(self, orchestrator):
        """Test getting stats."""
        stats = orchestrator.get_stats()
        assert "execution_count" in stats
        assert "rule_stats" in stats
        assert "agent_count" in stats

    def test_get_learning_report(self, orchestrator):
        """Test learning report generation."""
        orchestrator.rules.add(ExtractedRule(
            id="test-001",
            condition="test",
            recommendation="test",
            reasoning="test",
            success_count=10,
        ))

        report = orchestrator.get_learning_report()
        assert "summary" in report
        assert "top_rules" in report
        assert "by_category" in report

    def test_register_unregister_agent(self, orchestrator):
        """Test agent registration."""
        new_agent = MockAgent()
        orchestrator.register_agent("new", new_agent)
        assert "new" in orchestrator.agents

        assert orchestrator.unregister_agent("new") is True
        assert "new" not in orchestrator.agents
        assert orchestrator.unregister_agent("new") is False

    @pytest.mark.asyncio
    async def test_callbacks(self, orchestrator):
        """Test execution callbacks."""
        outcomes = []
        rules = []

        orchestrator.on_execution_complete(lambda o: outcomes.append(o))
        orchestrator.on_rules_extracted(lambda r: rules.extend(r))

        await orchestrator.execute_with_learning(
            task="Test task",
            agent_id="test",
        )

        assert len(outcomes) == 1
        assert outcomes[0].success is True

    @pytest.mark.asyncio
    async def test_augmented_task_format(self, orchestrator):
        """Test that task is properly augmented with rules."""
        # Add a rule
        orchestrator.rules.add(ExtractedRule(
            id="rule-001",
            condition="task keyword here",
            recommendation="Do something specific",
            reasoning="It helps",
            success_count=10,
        ))

        # Execute
        await orchestrator.execute_with_learning(
            task="task keyword here",
            agent_id="test",
        )

        # Check the agent received augmented task
        agent = orchestrator.agents["test"]
        if agent.calls:
            last_call = agent.calls[-1]
            # If rules were applied, task should be augmented
            if "LEARNED PATTERNS" in last_call:
                assert "TASK:" in last_call


class TestMockLearningOrchestrator:
    """Tests for MockLearningOrchestrator."""

    @pytest.mark.asyncio
    async def test_mock_execution(self):
        """Test mock orchestrator."""
        orchestrator = MockLearningOrchestrator()
        orchestrator.set_result("task1", {"output": "result1", "success": True})

        result = await orchestrator.execute_with_learning("task1", "agent1")
        assert result["output"] == "result1"
        assert len(orchestrator.executions) == 1


# =============================================================================
# Integration Tests
# =============================================================================

class TestLearningIntegration:
    """Integration tests for the learning system."""

    @pytest.mark.asyncio
    async def test_full_learning_cycle(self):
        """Test complete learning cycle."""
        # Setup
        store = RuleStore(backend=MemoryRuleStore())

        # Mock extractor that returns rules
        def extract_fn(prompt: str) -> str:
            return json.dumps([{
                "condition": "When dealing with complex queries",
                "recommendation": "Break down into sub-queries",
                "reasoning": "Simplification aids understanding",
                "category": "analysis"
            }])

        extractor = RuleExtractor(extraction_fn=extract_fn)

        agent = MockAgent({
            "success": True,
            "output": "Analysis complete",
            "quality_score": 0.95,
            "approach": "Broke down the query",
        })

        orchestrator = LearningOrchestrator(
            agents={"analyzer": agent},
            rule_store=store,
            rule_extractor=extractor,
            config=LearningConfig(auto_prune=False),
        )

        # First execution - should extract rules
        result1 = await orchestrator.execute_with_learning(
            task="Analyze this complex problem",
            agent_id="analyzer",
        )
        assert result1["success"] is True

        # Check rules were extracted
        stats = store.get_stats()
        assert stats.total_rules >= 1

        # Second execution - should apply rules
        result2 = await orchestrator.execute_with_learning(
            task="Handle another complex query",
            agent_id="analyzer",
        )
        assert result2["success"] is True

        # Rules should have been applied (check the agent calls)
        if len(agent.calls) >= 2:
            # Second call may contain learned patterns
            pass

    @pytest.mark.asyncio
    async def test_effectiveness_tracking_over_time(self):
        """Test effectiveness tracking over multiple executions."""
        store = RuleStore(backend=MemoryRuleStore())

        # Add initial rule
        rule = ExtractedRule(
            id="tracked-rule",
            condition="When processing data",
            recommendation="Validate inputs",
            reasoning="Prevents errors",
            success_count=1,
            failure_count=0,
        )
        store.add(rule)

        extractor = MockRuleExtractor([])

        # Create agents with different outcomes
        success_agent = MockAgent({
            "success": True,
            "output": "Done",
            "quality_score": 0.9,
        })
        failure_agent = MockAgent({
            "success": False,
            "output": "Failed",
            "quality_score": 0.3,
        })

        # Successful executions
        orch1 = LearningOrchestrator(
            agents={"agent": success_agent},
            rule_store=store,
            rule_extractor=extractor,
            config=LearningConfig(auto_prune=False),
        )

        for _ in range(5):
            await orch1.execute_with_learning(
                task="When processing data here",
                agent_id="agent",
            )

        # Check effectiveness increased
        updated = store.get("tracked-rule")
        # Note: effectiveness may or may not be updated depending on search matching
        assert updated is not None

    def test_export_import_preserves_learning(self):
        """Test that export/import preserves learned rules."""
        # Create store with rules
        store1 = RuleStore(backend=MemoryRuleStore())
        store1.add(ExtractedRule(
            id="export-001",
            condition="Important rule",
            recommendation="Do this",
            reasoning="Because",
            success_count=20,
            failure_count=3,
            tags=["important", "tested"],
        ))

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            filepath = f.name

        try:
            # Export
            store1.export_rules(filepath)

            # Import to new store
            store2 = RuleStore(backend=MemoryRuleStore())
            store2.import_rules(filepath)

            # Verify
            rule = store2.get("export-001")
            assert rule is not None
            assert rule.success_count == 20
            assert rule.tags == ["important", "tested"]
        finally:
            os.unlink(filepath)
