#!/usr/bin/env python3
"""
generate_test_data.py - Generate test data for Agent Dashboard manual testing.

Usage:
    python generate_test_data.py --claims 1000 --output tests/fixtures/standard_kg.json
    python generate_test_data.py --claims 100000 --topics 50 --output tests/fixtures/scale.json

Options:
    --claims N      Number of claims to generate (default: 1000)
    --topics N      Number of distinct topics (default: 10)
    --seed N        Random seed for reproducibility (default: 42)
    --output PATH   Output file path (default: stdout)
    --verbose       Enable verbose output
    --quiet         Suppress all output except errors

Version: 1.0.0
"""

import argparse
import json
import logging
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

TOPIC_DOMAINS = {
    "programming": {
        "entities": ["Python", "JavaScript", "TypeScript", "Rust", "Go", "Java", "C++", "Ruby"],
        "predicates": ["is_a", "supports", "has_feature", "implements", "extends"],
        "concepts": ["programming_language", "static_typing", "garbage_collection", "async_await"]
    },
    "ml": {
        "entities": ["TensorFlow", "PyTorch", "scikit-learn", "Keras", "XGBoost", "LightGBM"],
        "predicates": ["is_a", "uses", "written_in", "optimizes", "trains"],
        "concepts": ["ml_framework", "deep_learning", "neural_network", "gradient_descent"]
    },
    "web": {
        "entities": ["Flask", "Django", "FastAPI", "Express", "Next.js", "React", "Vue"],
        "predicates": ["is_a", "written_in", "serves", "renders", "handles"],
        "concepts": ["web_framework", "REST_API", "GraphQL", "websocket", "SSR"]
    },
    "database": {
        "entities": ["PostgreSQL", "MongoDB", "Redis", "SQLite", "Elasticsearch", "Neo4j"],
        "predicates": ["is_a", "stores", "indexes", "supports", "replicates"],
        "concepts": ["relational_db", "nosql", "graph_db", "cache", "search_engine"]
    },
    "devops": {
        "entities": ["Docker", "Kubernetes", "Terraform", "Ansible", "Jenkins", "GitHub_Actions"],
        "predicates": ["is_a", "orchestrates", "provisions", "deploys", "monitors"],
        "concepts": ["containerization", "orchestration", "IaC", "CI_CD", "automation"]
    },
    "security": {
        "entities": ["OAuth2", "JWT", "TLS", "bcrypt", "OWASP", "Vault"],
        "predicates": ["is_a", "secures", "authenticates", "encrypts", "validates"],
        "concepts": ["authentication", "authorization", "encryption", "hashing", "secrets"]
    },
    "architecture": {
        "entities": ["microservices", "monolith", "serverless", "event_driven", "CQRS"],
        "predicates": ["is_a", "enables", "requires", "communicates_via", "scales_with"],
        "concepts": ["design_pattern", "distributed_system", "scalability", "resilience"]
    },
    "testing": {
        "entities": ["pytest", "Jest", "Selenium", "Cypress", "Locust", "k6"],
        "predicates": ["is_a", "tests", "validates", "measures", "simulates"],
        "concepts": ["unit_test", "integration_test", "e2e_test", "load_test", "coverage"]
    },
    "data": {
        "entities": ["Pandas", "Spark", "Airflow", "dbt", "Kafka", "Flink"],
        "predicates": ["is_a", "processes", "transforms", "streams", "orchestrates"],
        "concepts": ["data_pipeline", "ETL", "streaming", "batch", "data_warehouse"]
    },
    "cloud": {
        "entities": ["AWS", "GCP", "Azure", "Cloudflare", "Vercel", "Fly.io"],
        "predicates": ["is_a", "provides", "hosts", "scales", "manages"],
        "concepts": ["cloud_provider", "CDN", "edge_computing", "serverless", "PaaS"]
    }
}


def generate_claim(index, topic, rng, base_time):
    domain = TOPIC_DOMAINS[topic]
    subject = rng.choice(domain["entities"])
    predicate = rng.choice(domain["predicates"])
    obj = rng.choice(domain["concepts"]) if rng.random() < 0.6 else rng.choice(domain["entities"])
    while obj == subject and obj in domain["entities"]:
        obj = rng.choice(domain["entities"])
    confidence = round(max(0.5, min(1.0, rng.gauss(0.85, 0.1))), 3)
    return {
        "id": f"claim_{index:06d}",
        "subject": subject,
        "predicate": predicate,
        "object": obj,
        "confidence": confidence,
        "source": rng.choice(["documentation", "research", "inference", "user_input"]),
        "timestamp": (base_time + timedelta(seconds=index * 60)).isoformat() + "Z",
        "metadata": {"topic": topic, "verified": rng.random() > 0.2}
    }


def generate_knowledge_graph(num_claims, num_topics, seed, name="generated_kg"):
    rng = random.Random(seed)
    base_time = datetime(2025, 1, 1, 0, 0, 0)
    topics = list(TOPIC_DOMAINS.keys())[:min(num_topics, len(TOPIC_DOMAINS))]
    claims = [generate_claim(i + 1, topics[i % len(topics)], rng, base_time) for i in range(num_claims)]
    
    entities = {}
    for c in claims:
        for f in ["subject", "object"]:
            eid = c[f].lower().replace(" ", "_")
            if eid not in entities:
                domain = TOPIC_DOMAINS.get(c["metadata"]["topic"], {})
                etype = "tool" if c[f] in domain.get("entities", []) else "concept" if c[f] in domain.get("concepts", []) else "unknown"
                entities[eid] = {"id": c[f], "type": etype, "properties": {"domain": c["metadata"]["topic"]}}
    
    rels = []
    seen = set()
    for c in claims:
        key = (c["subject"], c["object"], c["predicate"])
        if key not in seen:
            seen.add(key)
            rels.append({"source": c["subject"], "target": c["object"], "type": c["predicate"]})
    
    return {
        "metadata": {
            "name": name, "description": f"Generated KG with {num_claims} claims",
            "version": "1.0.0", "created": datetime.now().isoformat(), "seed": seed,
            "claim_count": num_claims, "entity_count": len(entities),
            "relationship_count": len(rels), "topics": topics
        },
        "claims": claims, "entities": list(entities.values()), "relationships": rels
    }


def main(args=None):
    parser = argparse.ArgumentParser(description="Generate test data")
    parser.add_argument("--claims", "-n", type=int, default=1000, help="Number of claims")
    parser.add_argument("--topics", "-t", type=int, default=10, help="Number of topics")
    parser.add_argument("--seed", "-s", type=int, default=42, help="Random seed")
    parser.add_argument("--output", "-o", type=str, default=None, help="Output file")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--quiet", "-q", action="store_true")
    p = parser.parse_args(args)
    
    if p.quiet: logger.setLevel(logging.ERROR)
    elif p.verbose: logger.setLevel(logging.DEBUG)
    
    name = Path(p.output).stem if p.output else f"generated_{p.claims}"
    logger.info(f"Generating {p.claims} claims with {p.topics} topics (seed={p.seed})")
    
    kg = generate_knowledge_graph(p.claims, p.topics, p.seed, name)
    output = json.dumps(kg, indent=2)
    
    if p.output:
        Path(p.output).parent.mkdir(parents=True, exist_ok=True)
        Path(p.output).write_text(output, encoding="utf-8")
        logger.info(f"Wrote to {p.output}")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
