#!/usr/bin/env python3
"""
generate_test_queries.py - Generate diverse test queries.

Usage:
    python generate_test_queries.py --count 100 --output tests/fixtures/stress_queries.json
"""

import argparse
import json
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import List

QUERY_TEMPLATES = [
    "What is {topic}?",
    "How does {topic} work?",
    "Explain {topic} in detail",
    "Compare {topic1} and {topic2}",
    "Find all claims about {topic}",
    "Summarize {topic}",
    "{topic} best practices",
    "{topic} examples",
    "Relationship between {topic1} and {topic2}",
    "History of {topic}"
]

TOPICS = [
    "Python", "JavaScript", "machine learning", "neural networks",
    "Flask", "Django", "TensorFlow", "PyTorch", "React", "Vue",
    "Docker", "Kubernetes", "microservices", "REST API", "GraphQL",
    "databases", "SQL", "NoSQL", "Redis", "PostgreSQL",
    "testing", "CI/CD", "DevOps", "security", "authentication",
    "error handling", "logging", "monitoring", "performance"
]

def generate_query(rng: random.Random) -> str:
    template = rng.choice(QUERY_TEMPLATES)
    topic1 = rng.choice(TOPICS)
    topic2 = rng.choice([t for t in TOPICS if t != topic1])
    return template.format(topic=topic1, topic1=topic1, topic2=topic2)

def generate_queries(count: int, seed: int = 42) -> List[dict]:
    rng = random.Random(seed)
    queries = []
    for i in range(count):
        queries.append({
            "id": f"gen_{i+1:04d}",
            "query": generate_query(rng),
            "min_results": 0,
            "max_latency_ms": 10000
        })
    return queries

def main():
    parser = argparse.ArgumentParser(description="Generate test queries")
    parser.add_argument("--count", "-n", type=int, default=100)
    parser.add_argument("--seed", "-s", type=int, default=42)
    parser.add_argument("--output", "-o", type=str, default=None)
    args = parser.parse_args()
    
    queries = generate_queries(args.count, args.seed)
    
    data = {
        "metadata": {
            "name": "generated_queries",
            "created": datetime.now().isoformat(),
            "count": len(queries),
            "seed": args.seed
        },
        "queries": queries
    }
    
    output = json.dumps(data, indent=2)
    
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Generated {len(queries)} queries to {args.output}")
    else:
        print(output)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
