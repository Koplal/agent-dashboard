#!/usr/bin/env python3
"""
validate_test_data.py - Validate test fixture integrity.

Usage:
    python validate_test_data.py tests/fixtures/minimal_kg.json
    python validate_test_data.py --all
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

def validate_claim(claim: Dict[str, Any], idx: int) -> List[str]:
    errors = []
    required = ["id", "subject", "predicate", "object", "confidence"]
    for field in required:
        if field not in claim:
            errors.append(f"Claim {idx}: missing required field '{field}'")
    if "confidence" in claim:
        conf = claim["confidence"]
        if not isinstance(conf, (int, float)) or not 0 <= conf <= 1:
            errors.append(f"Claim {idx}: confidence must be 0-1, got {conf}")
    return errors

def validate_fixture(filepath: Path) -> Tuple[bool, List[str]]:
    errors = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"]
    except FileNotFoundError:
        return False, [f"File not found: {filepath}"]
    
    if "metadata" not in data:
        errors.append("Missing 'metadata' section")
    if "claims" not in data:
        errors.append("Missing 'claims' section")
    else:
        for i, claim in enumerate(data["claims"]):
            errors.extend(validate_claim(claim, i))
    
    return len(errors) == 0, errors

def main():
    parser = argparse.ArgumentParser(description="Validate test fixtures")
    parser.add_argument("file", nargs="?", help="Fixture file to validate")
    parser.add_argument("--all", action="store_true", help="Validate all fixtures")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()
    
    fixtures_dir = Path(__file__).parent.parent.parent / "tests" / "fixtures"
    
    if args.all:
        files = list(fixtures_dir.glob("*.json"))
    elif args.file:
        files = [Path(args.file)]
    else:
        files = list(fixtures_dir.glob("*.json"))
    
    all_valid = True
    for f in files:
        valid, errors = validate_fixture(f)
        status = "PASS" if valid else "FAIL"
        print(f"[{status}] {f.name}")
        if not valid:
            all_valid = False
            for err in errors[:5]:
                print(f"  - {err}")
    
    return 0 if all_valid else 1

if __name__ == "__main__":
    sys.exit(main())
