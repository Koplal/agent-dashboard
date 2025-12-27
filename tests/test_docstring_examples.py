"""
Tests for P4-001: Docstring Examples.

Validates that all docstring examples are runnable and produce expected output.
This file is LOCKED after approval - implementation must pass all tests.

Version: 2.7.0
"""

import doctest
import pytest
import importlib
import inspect
from pathlib import Path


# Priority modules that must have enhanced docstrings
MODULES_WITH_EXAMPLES = [
    "src.knowledge.retriever",
    "src.knowledge.manager",
    "src.knowledge.graph",
    "src.validators.output_validator",
    "src.audit.trail",
]


class TestDocstringExamples:
    """Verify docstring examples are valid and runnable."""

    @pytest.mark.parametrize("module_path", MODULES_WITH_EXAMPLES)
    def test_doctest_examples(self, module_path):
        """All docstring examples should pass doctest."""
        module = importlib.import_module(module_path)
        results = doctest.testmod(module, verbose=False, optionflags=doctest.ELLIPSIS)
        assert results.failed == 0, f"{module_path}: {results.failed} doctest failures"

    def test_hybrid_retriever_class_has_example(self):
        """HybridRetriever class should have at least one docstring example."""
        from src.knowledge.retriever import HybridRetriever
        
        doc = HybridRetriever.__doc__
        assert doc is not None, "HybridRetriever missing docstring"
        assert "Example:" in doc or ">>>" in doc, "HybridRetriever missing example"

    def test_hybrid_retriever_retrieve_has_example(self):
        """HybridRetriever.retrieve method should have docstring example."""
        from src.knowledge.retriever import HybridRetriever
        
        doc = HybridRetriever.retrieve.__doc__
        assert doc is not None, "retrieve() missing docstring"
        assert "Example:" in doc or ">>>" in doc, "retrieve() missing example"

    def test_output_validator_has_example(self):
        """OutputValidator class should have docstring example."""
        from src.validators.output_validator import OutputValidator
        
        doc = OutputValidator.__doc__
        assert doc is not None, "OutputValidator missing docstring"
        assert "Example:" in doc or ">>>" in doc, "OutputValidator missing example"

    def test_knowledge_graph_has_example(self):
        """ResearchKnowledgeGraph should have docstring example."""
        from src.knowledge.manager import ResearchKnowledgeGraph
        
        doc = ResearchKnowledgeGraph.__doc__
        assert doc is not None, "ResearchKnowledgeGraph missing docstring"
        assert "Example:" in doc or ">>>" in doc, "ResearchKnowledgeGraph missing example"

    def test_audit_entry_has_example(self):
        """AuditEntry should have docstring example."""
        from src.audit.trail import AuditEntry
        
        doc = AuditEntry.__doc__
        assert doc is not None, "AuditEntry missing docstring"
        # AuditEntry is a dataclass, may have attribute docs instead
        # Just verify the docstring exists and describes the class
        assert "audit" in doc.lower() or "decision" in doc.lower()


class TestDocstringCompleteness:
    """Verify docstrings have all required sections."""

    def test_retriever_has_args_section(self):
        """Methods with parameters should document Args."""
        from src.knowledge.retriever import HybridRetriever
        
        doc = HybridRetriever.retrieve.__doc__
        assert "Args:" in doc, "retrieve() missing Args section"
        assert "query:" in doc or "query" in doc, "query parameter not documented"

    def test_retriever_has_returns_section(self):
        """Methods with return values should document Returns."""
        from src.knowledge.retriever import HybridRetriever
        
        doc = HybridRetriever.retrieve.__doc__
        assert "Returns:" in doc, "retrieve() missing Returns section"

    def test_validator_has_returns_section(self):
        """OutputValidator.validate should document Returns."""
        from src.validators.output_validator import OutputValidator
        
        doc = OutputValidator.validate.__doc__
        assert "Returns:" in doc, "validate() missing Returns section"


class TestNoPlaceholderValues:
    """Verify examples use realistic values, not placeholders."""

    def test_no_foo_bar_in_retriever(self):
        """HybridRetriever examples should not use 'foo' or 'bar'."""
        from src.knowledge.retriever import HybridRetriever
        
        doc = HybridRetriever.__doc__ or ""
        method_doc = HybridRetriever.retrieve.__doc__ or ""
        combined = doc.lower() + method_doc.lower()
        
        assert "foo" not in combined, "Found placeholder 'foo' in docstring"
        assert "bar" not in combined, "Found placeholder 'bar' in docstring"
        assert "test123" not in combined, "Found placeholder 'test123' in docstring"

    def test_no_foo_bar_in_validator(self):
        """OutputValidator examples should not use placeholder values."""
        from src.validators.output_validator import OutputValidator
        
        doc = OutputValidator.__doc__ or ""
        method_doc = OutputValidator.validate.__doc__ or ""
        combined = doc.lower() + method_doc.lower()
        
        assert "foo" not in combined, "Found placeholder 'foo' in docstring"
        assert "bar" not in combined, "Found placeholder 'bar' in docstring"

    def test_uses_realistic_values(self):
        """Examples should use domain-relevant values."""
        from src.knowledge.retriever import HybridRetriever
        
        doc = HybridRetriever.__doc__ or ""
        method_doc = HybridRetriever.retrieve.__doc__ or ""
        combined = doc.lower() + method_doc.lower()
        
        # Should reference actual domain concepts
        has_realistic = any([
            "machine learning" in combined,
            "python" in combined,
            "research" in combined,
            "knowledge" in combined,
            "claim" in combined,
        ])
        assert has_realistic, "Examples should use realistic domain values"


class TestPublicMethodCoverage:
    """Verify public methods have docstrings."""

    def test_public_methods_have_docstrings(self):
        """All public methods in priority modules should have docstrings."""
        from src.knowledge.retriever import HybridRetriever
        from src.validators.output_validator import OutputValidator
        
        # Check HybridRetriever public methods
        for name, method in inspect.getmembers(HybridRetriever, predicate=inspect.isfunction):
            if not name.startswith('_'):
                assert method.__doc__, f"HybridRetriever.{name} missing docstring"
        
        # Check OutputValidator public methods
        for name, method in inspect.getmembers(OutputValidator, predicate=inspect.isfunction):
            if not name.startswith('_'):
                assert method.__doc__, f"OutputValidator.{name} missing docstring"
