#!/usr/bin/env python3
import json
import logging
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class LatencyStats:
    count: int = 0
    min_ms: float = 0.0
    max_ms: float = 0.0
    mean_ms: float = 0.0
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    
    def to_dict(self):
        return {"count": self.count, "min_ms": self.min_ms, "max_ms": self.max_ms,
                "mean_ms": self.mean_ms, "p50_ms": self.p50_ms, "p95_ms": self.p95_ms, "p99_ms": self.p99_ms}

class MetricsCollector:
    def __init__(self):
        self.latencies = defaultdict(list)
        self.counters = defaultdict(int)
        self.gauges = {}
        self.start_time = time.time()
    
    def record_latency(self, name, value_ms):
        self.latencies[name].append(value_ms)
    
    def increment_counter(self, name, amount=1):
        self.counters[name] += amount
    
    def set_gauge(self, name, value):
        self.gauges[name] = value
    
    def get_statistics(self, name):
        values = self.latencies.get(name, [])
        if not values:
            return LatencyStats()
        sorted_values = sorted(values)
        n = len(sorted_values)
        return LatencyStats(
            count=n, min_ms=min(values), max_ms=max(values),
            mean_ms=statistics.mean(values),
            p50_ms=sorted_values[int(n*0.5)] if n > 0 else 0,
            p95_ms=sorted_values[int(n*0.95)] if n >= 20 else sorted_values[-1],
            p99_ms=sorted_values[int(n*0.99)] if n >= 100 else sorted_values[-1]
        )
    
    def get_all_statistics(self):
        return {name: self.get_statistics(name) for name in self.latencies}
    
    def export_json(self, output_path):
        data = {"timestamp": datetime.now().isoformat(), "latencies": {n: self.get_statistics(n).to_dict() for n in self.latencies}, "counters": dict(self.counters)}
        Path(output_path).write_text(json.dumps(data, indent=2), encoding="utf-8")
    
    def print_summary(self):
        print("Metrics Summary:")
        for name, stats in self.get_all_statistics().items():
            print(f"  {name}: count={stats.count}, p50={stats.p50_ms:.1f}ms, p95={stats.p95_ms:.1f}ms")

if __name__ == "__main__":
    import random
    collector = MetricsCollector()
    for _ in range(100):
        collector.record_latency("search", random.gauss(100, 30))
    collector.print_summary()
