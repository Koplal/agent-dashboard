#\!/usr/bin/env python3
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    test_id: str
    name: str = ""
    status: str = "PENDING"
    duration_ms: float = 0.0
    category: str = "general"
    error_message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self):
        return asdict(self)

@dataclass
class TestSuite:
    name: str
    results: List[TestResult] = field(default_factory=list)
    
    @property
    def total(self): return len(self.results)
    @property
    def passed(self): return sum(1 for r in self.results if r.status == "PASS")

class TestReporter:
    def __init__(self, title="Test Report"):
        self.title = title
        self.results = []
        self.suites = {}
        self.start_time = datetime.now()
    
    def add_result(self, result):
        self.results.append(result)
        cat = result.category
        if cat not in self.suites:
            self.suites[cat] = TestSuite(name=cat)
        self.suites[cat].results.append(result)
    
    def get_summary(self):
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == "PASS")
        failed = sum(1 for r in self.results if r.status == "FAIL")
        return {"total": total, "passed": passed, "failed": failed, "pass_rate": (passed/total*100) if total else 0}
    
    def generate_markdown(self):
        s = self.get_summary()
        lines = [f"# {self.title}", f"**Generated:** {datetime.now().isoformat()}", "",
                 "## Summary", f"- Total: {s["total"]}", f"- Passed: {s["passed"]}", f"- Failed: {s["failed"]}", ""]
        for name, suite in self.suites.items():
            lines.extend([f"### {name}", "| Test | Status | Duration |", "|------|--------|----------|"])
            for r in suite.results:
                lines.append(f"| {r.test_id} | {r.status} | {r.duration_ms:.0f}ms |")
        return chr(10).join(lines)
    
    def generate_report(self, output_path, format="md"):
        path = Path(output_path)
        content = self.generate_markdown() if format in ("md", "markdown") else json.dumps({"summary": self.get_summary(), "results": [r.to_dict() for r in self.results]}, indent=2)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    
    def print_summary(self):
        s = self.get_summary()
        print(f"Results: {s["passed"]}/{s["total"]} passed ({s["pass_rate"]:.1f}%)")

if __name__ == "__main__":
    reporter = TestReporter()
    reporter.add_result(TestResult("ST-001", "Test 1", "PASS", 150.0, "smoke"))
    reporter.print_summary()
