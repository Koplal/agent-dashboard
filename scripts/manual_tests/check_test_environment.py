#!/usr/bin/env python3
import argparse
import json
import logging
import os
import platform
import shutil
import socket
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

@dataclass
class CheckResult:
    name: str
    status: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

class EnvironmentChecker:
    def __init__(self):
        self.results = []
        self.project_root = Path(__file__).parent.parent.parent
    
    def run_all_checks(self):
        checks = [
            ("Python Version", self.check_python),
            ("Core Dependencies", self.check_deps),
            ("Test Fixtures", self.check_fixtures),
            ("Disk Space", self.check_disk),
            ("Dashboard Server", self.check_server),
        ]
        all_passed = True
        for name, func in checks:
            try:
                result = func()
                self.results.append(result)
                icon = {"PASS": "+", "FAIL": "X", "WARN": "!"}[result.status]
                logger.info(f"[{icon}] {name}: {result.message}")
                if result.status == "FAIL":
                    all_passed = False
            except Exception as e:
                self.results.append(CheckResult(name, "FAIL", str(e)))
                all_passed = False
        return all_passed
    
    def check_python(self):
        v = sys.version_info
        vs = f"{v.major}.{v.minor}.{v.micro}"
        if v >= (3, 10):
            return CheckResult("Python", "PASS", f"Python {vs}")
        return CheckResult("Python", "FAIL", f"Python {vs} (3.10+ required)")
    
    def check_deps(self):
        required = ["aiohttp"]
        missing = []
        for pkg in required:
            try:
                __import__(pkg)
            except ImportError:
                missing.append(pkg)
        if missing:
            return CheckResult("Dependencies", "FAIL", f"Missing: {missing}")
        return CheckResult("Dependencies", "PASS", "All installed")
    
    def check_fixtures(self):
        fixtures_dir = self.project_root / "tests" / "fixtures"
        if not fixtures_dir.exists():
            return CheckResult("Fixtures", "FAIL", "Directory not found")
        required = ["minimal_kg.json", "test_queries.json"]
        missing = [f for f in required if not (fixtures_dir / f).exists()]
        if missing:
            return CheckResult("Fixtures", "FAIL", f"Missing: {missing}")
        return CheckResult("Fixtures", "PASS", "All present")
    
    def check_disk(self):
        total, used, free = shutil.disk_usage(self.project_root)
        free_gb = free / (1024**3)
        if free_gb >= 1.0:
            return CheckResult("Disk", "PASS", f"{free_gb:.1f} GB free")
        return CheckResult("Disk", "WARN", f"{free_gb:.1f} GB free (low)")
    
    def check_server(self):
        try:
            import urllib.request
            with urllib.request.urlopen("http://localhost:4200", timeout=5) as r:
                if r.status == 200:
                    return CheckResult("Server", "PASS", "Running")
        except:
            return CheckResult("Server", "WARN", "Not running")
    
    def print_summary(self):
        passed = sum(1 for r in self.results if r.status == "PASS")
        failed = sum(1 for r in self.results if r.status == "FAIL")
        ready = "Yes" if failed == 0 else "No"
        print(f"Summary: {passed} passed, {failed} failed")
        print(f"Ready: {ready}")

def main():
    parser = argparse.ArgumentParser(description="Check test environment")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--quiet", "-q", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    
    if args.quiet: logger.setLevel(logging.ERROR)
    elif args.verbose: logger.setLevel(logging.DEBUG)
    
    print("Environment Check - Agent Dashboard")
    print("=" * 50)
    
    checker = EnvironmentChecker()
    passed = checker.run_all_checks()
    
    if args.json:
        print(json.dumps([{"name": r.name, "status": r.status, "message": r.message} for r in checker.results], indent=2))
    else:
        checker.print_summary()
    
    return 0 if passed else 1

if __name__ == "__main__":
    sys.exit(main())
