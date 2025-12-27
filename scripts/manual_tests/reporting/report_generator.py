#\!/usr/bin/env python3
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

class ReportGenerator:
    def __init__(self, title="Test Report"):
        self.title = title
        self.results = []
        self.metadata = {}
    
    def add_result(self, result):
        self.results.append(result)
    
    def add_results(self, results):
        self.results.extend(results)
    
    def get_summary(self):
        total = len(self.results)
        passed = sum(1 for r in self.results if r.get("status") == "PASS")
        failed = sum(1 for r in self.results if r.get("status") == "FAIL")
        return {"total": total, "passed": passed, "failed": failed, "pass_rate": (passed/total*100) if total else 0}
    
    def generate_markdown(self):
        s = self.get_summary()
        lines = [f"# {self.title}", f"**Generated:** {datetime.now().isoformat()}", "", "## Summary",
                 f"- Total: {s["total"]}", f"- Passed: {s["passed"]}", f"- Failed: {s["failed"]}", "",
                 "## Results", "| Test ID | Name | Status | Duration |", "|---------|------|--------|----------|"]
        for r in self.results:
            lines.append(f"| {r.get("test_id", "N/A")} | {r.get("name", "")} | {r.get("status", "")} | {r.get("duration_ms", 0):.0f}ms |")
        return chr(10).join(lines)
    
    def generate(self, output_path, format="md"):
        path = Path(output_path)
        if format in ("markdown", "md"):
            content = self.generate_markdown()
        else:
            content = json.dumps({"summary": self.get_summary(), "results": self.results}, indent=2)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"Generated report: {path}")

if __name__ == "__main__":
    gen = ReportGenerator("Demo Report")
    gen.add_result({"test_id": "ST-001", "name": "Test 1", "status": "PASS", "duration_ms": 150})
    print(gen.generate_markdown())
