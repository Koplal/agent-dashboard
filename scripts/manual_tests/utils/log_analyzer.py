#\!/usr/bin/env python3
import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class LogEntry:
    timestamp: str
    level: str
    message: str
    source: str = ""
    line_number: int = 0

@dataclass
class LogAnalysisReport:
    total_lines: int = 0
    error_count: int = 0
    warning_count: int = 0
    errors: List[LogEntry] = field(default_factory=list)
    patterns_found: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self):
        return {"total_lines": self.total_lines, "error_count": self.error_count, "warning_count": self.warning_count}

class LogAnalyzer:
    LOG_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[^\s]*)\s*-?\s*(ERROR|WARN|WARNING|INFO|DEBUG)\s*-?\s*(.*)", re.IGNORECASE)
    
    ERROR_PATTERNS = {
        "connection_error": re.compile(r"connection (refused|reset|timeout)", re.IGNORECASE),
        "timeout": re.compile(r"timeout|timed out", re.IGNORECASE),
        "memory_error": re.compile(r"memory (error|exhausted)", re.IGNORECASE),
    }
    
    def __init__(self):
        self.entries = []
        self.report = LogAnalysisReport()
    
    def parse_line(self, line, line_number, source=""):
        line = line.strip()
        if not line:
            return None
        match = self.LOG_PATTERN.match(line)
        if match:
            return LogEntry(match.group(1), match.group(2).upper(), match.group(3), source, line_number)
        return None
    
    def analyze_file(self, file_path):
        path = Path(file_path)
        if not path.exists():
            logger.warning(f"Log file not found: {file_path}")
            return
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line_num, line in enumerate(f, 1):
                self.report.total_lines += 1
                entry = self.parse_line(line, line_num, path.name)
                if entry:
                    self.entries.append(entry)
                    if entry.level == "ERROR":
                        self.report.error_count += 1
                        self.report.errors.append(entry)
                    elif entry.level in ("WARN", "WARNING"):
                        self.report.warning_count += 1
    
    def get_report(self):
        return self.report
    
    def print_summary(self):
        r = self.report
        print(f"Log Analysis: {r.total_lines} lines, {r.error_count} errors, {r.warning_count} warnings")

if __name__ == "__main__":
    import sys
    analyzer = LogAnalyzer()
    if len(sys.argv) > 1:
        analyzer.analyze_file(sys.argv[1])
    analyzer.print_summary()
