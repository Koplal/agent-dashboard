"""
Neurosymbolic Learning Module.

Implements a learning system that extracts symbolic rules from successful
agent executions, stores them as structured knowledge, and uses them to
improve future performance.

Version: 2.6.0

Example Usage:
    from src.learning import (
        LearningOrchestrator,
        RuleStore,
        RuleExtractor,
    )

    # Initialize components
    rule_store = RuleStore(db_path="./learning.db")
    rule_extractor = RuleExtractor(client=anthropic_client)

    # Create orchestrator
    orchestrator = LearningOrchestrator(
        agents={"researcher": my_agent},
        rule_store=rule_store,
        rule_extractor=rule_extractor,
    )

    # Execute with learning
    result = await orchestrator.execute_with_learning(
        task="Research AI safety",
        agent_id="researcher"
    )

    # Check learning stats
    stats = orchestrator.get_stats()
    print(f"Rules extracted: {stats['rules_extracted']}")
"""

from .models import (
    # Enums
    RuleCategory,
    RuleStatus,
    # Data classes
    ExtractedRule,
    ExecutionOutcome,
    RuleMatch,
    LearningStats,
)

from .extractor import (
    LLMClient,
    ExtractionConfig,
    RuleExtractor,
    MockRuleExtractor,
)

from .store import (
    SearchConfig,
    RuleStoreBackend,
    MemoryRuleStore,
    SQLiteRuleStore,
    RuleStore,
)

from .orchestrator import (
    ExecutableAgent,
    LearningConfig,
    ExecutionContext,
    LearningOrchestrator,
    MockLearningOrchestrator,
)

__all__ = [
    # Enums
    "RuleCategory",
    "RuleStatus",
    # Data models
    "ExtractedRule",
    "ExecutionOutcome",
    "RuleMatch",
    "LearningStats",
    # Extractor
    "LLMClient",
    "ExtractionConfig",
    "RuleExtractor",
    "MockRuleExtractor",
    # Store
    "SearchConfig",
    "RuleStoreBackend",
    "MemoryRuleStore",
    "SQLiteRuleStore",
    "RuleStore",
    # Orchestrator
    "ExecutableAgent",
    "LearningConfig",
    "ExecutionContext",
    "LearningOrchestrator",
    "MockLearningOrchestrator",
]

__version__ = "2.6.0"
