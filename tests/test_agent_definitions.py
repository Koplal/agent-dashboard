#!/usr/bin/env python3
"""test_agent_definitions.py - Validation tests for agent definition files.

Version: 2.5.2
"""

import re
import pytest
from pathlib import Path
from typing import Dict, Any, List, Optional

AGENTS_DIR = Path(__file__).parent.parent / "agents"
REQUIRED_FIELDS = {"name", "description", "tools", "model", "version", "tier"}
VALID_MODELS = {"opus", "sonnet", "haiku"}
VALID_TIERS = {0, 1, 2, 3}
TIER_MODEL_MAP = {0: {"opus"}, 1: {"opus"}, 2: {"sonnet"}, 3: {"haiku"}}


def parse_frontmatter(content: str) -> Optional[Dict[str, Any]]:
    """Parse YAML frontmatter from markdown content."""
    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return None
    frontmatter = {}
    lines = match.group(1).strip().split('\n')
    for line in lines:
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            if key == "tier":
                try:
                    value = int(value)
                except ValueError:
                    pass
            frontmatter[key] = value
    return frontmatter


def get_agent_files() -> List[Path]:
    if not AGENTS_DIR.exists():
        return []
    return list(AGENTS_DIR.glob("*.md"))


class TestAgentFilesExist:
    def test_agents_directory_exists(self):
        assert AGENTS_DIR.exists(), f"Agents directory not found: {AGENTS_DIR}"

    def test_agents_directory_has_files(self):
        files = get_agent_files()
        assert len(files) > 0, "No agent files found"

    def test_minimum_agent_count(self):
        files = get_agent_files()
        assert len(files) >= 10, f"Expected >= 10 agents, found {len(files)}"


class TestAgentFrontmatter:
    @pytest.fixture
    def agent_files(self):
        return get_agent_files()

    def test_all_agents_have_valid_frontmatter(self, agent_files):
        for agent_file in agent_files:
            content = agent_file.read_text(encoding="utf-8")
            fm = parse_frontmatter(content)
            assert fm is not None, f"{agent_file.name}: No valid frontmatter"

    def test_all_agents_have_required_fields(self, agent_files):
        for agent_file in agent_files:
            content = agent_file.read_text(encoding="utf-8")
            fm = parse_frontmatter(content)
            if fm is None:
                pytest.fail(f"{agent_file.name}: Could not parse")
            missing = REQUIRED_FIELDS - set(fm.keys())
            assert not missing, f"{agent_file.name}: Missing {missing}"

    def test_all_agents_have_valid_model(self, agent_files):
        for agent_file in agent_files:
            content = agent_file.read_text(encoding="utf-8")
            fm = parse_frontmatter(content)
            if fm is None:
                continue
            model = fm.get("model", "").lower()
            assert model in VALID_MODELS, f"{agent_file.name}: Invalid model"

    def test_all_agents_have_valid_tier(self, agent_files):
        for agent_file in agent_files:
            content = agent_file.read_text(encoding="utf-8")
            fm = parse_frontmatter(content)
            if fm is None:
                continue
            tier = fm.get("tier")
            assert tier in VALID_TIERS, f"{agent_file.name}: Invalid tier"

    def test_tier_model_consistency(self, agent_files):
        for agent_file in agent_files:
            content = agent_file.read_text(encoding="utf-8")
            fm = parse_frontmatter(content)
            if fm is None:
                continue
            tier = fm.get("tier")
            model = fm.get("model", "").lower()
            if tier not in TIER_MODEL_MAP:
                continue
            expected = TIER_MODEL_MAP[tier]
            assert model in expected, f"{agent_file.name}: Tier/model mismatch"

    def test_all_agents_have_version(self, agent_files):
        for agent_file in agent_files:
            content = agent_file.read_text(encoding="utf-8")
            fm = parse_frontmatter(content)
            if fm is None:
                continue
            version = fm.get("version", "")
            assert re.match(r"^\d+\.\d+\.\d+$", str(version)), f"{agent_file.name}: Invalid version"


class TestTierDistribution:
    def test_has_opus_agents(self):
        agent_files = get_agent_files()
        opus_count = 0
        for a in agent_files:
            fm = parse_frontmatter(a.read_text(encoding="utf-8"))
            if fm and fm.get("model", "").lower() == "opus":
                opus_count += 1
        assert opus_count >= 1, "Should have at least one Opus agent"

    def test_has_sonnet_agents(self):
        agent_files = get_agent_files()
        sonnet_count = 0
        for a in agent_files:
            fm = parse_frontmatter(a.read_text(encoding="utf-8"))
            if fm and fm.get("model", "").lower() == "sonnet":
                sonnet_count += 1
        assert sonnet_count >= 1, "Should have at least one Sonnet agent"

    def test_has_haiku_agents(self):
        agent_files = get_agent_files()
        haiku_count = 0
        for a in agent_files:
            fm = parse_frontmatter(a.read_text(encoding="utf-8"))
            if fm and fm.get("model", "").lower() == "haiku":
                haiku_count += 1
        assert haiku_count >= 1, "Should have at least one Haiku agent"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
