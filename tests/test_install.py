"""
Tests for P1-003: Cross-Platform Install Script.
Version: 2.7.0

Tests the Python-based cross-platform installer that supplements install.sh.
"""

import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add scripts directory to path for import
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


class TestPlatformDetection:
    """Test platform detection utilities."""

    def test_detect_platform_returns_dict(self):
        from install import detect_platform
        result = detect_platform()
        assert isinstance(result, dict)
        assert "os" in result
        assert "python_cmd" in result
        assert "python_version" in result

    def test_detect_platform_os_name(self):
        from install import detect_platform
        result = detect_platform()
        assert result["os"] in ["windows", "macos", "linux", "unknown"]

    def test_detect_platform_python_version(self):
        from install import detect_platform
        result = detect_platform()
        assert result["python_version"] >= (3, 9)


class TestDependencyChecker:
    """Test dependency checking utilities."""

    def test_check_core_dependencies(self):
        from install import check_dependencies
        # These should be installed in test environment
        result = check_dependencies(["pytest"])
        assert "pytest" in result
        assert result["pytest"]["installed"] is True

    def test_check_missing_dependency(self):
        from install import check_dependencies
        result = check_dependencies(["nonexistent_package_xyz_123"])
        assert "nonexistent_package_xyz_123" in result
        assert result["nonexistent_package_xyz_123"]["installed"] is False

    def test_get_optional_dependencies(self):
        from install import get_optional_dependencies
        deps = get_optional_dependencies()
        assert isinstance(deps, dict)
        assert "knowledge_graph" in deps
        assert "tokenizer" in deps


class TestDirectorySetup:
    """Test directory structure creation."""

    def test_get_install_paths(self):
        from install import get_install_paths
        paths = get_install_paths()
        assert "install_dir" in paths
        assert "agents_dir" in paths
        assert "config_dir" in paths
        assert "bin_dir" in paths

    def test_create_directory_structure(self):
        from install import create_directory_structure, get_install_paths
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"HOME": tmpdir}):
                paths = get_install_paths(base_dir=tmpdir)
                result = create_directory_structure(paths)
                assert result["success"] is True
                assert Path(paths["install_dir"]).exists()


class TestInstallConfig:
    """Test installation configuration."""

    def test_install_config_default(self):
        from install import InstallConfig
        config = InstallConfig()
        assert config.non_interactive is False
        assert config.force is False
        assert config.skip_hooks is False

    def test_install_config_non_interactive(self):
        from install import InstallConfig
        config = InstallConfig(non_interactive=True)
        assert config.non_interactive is True

    def test_install_config_from_args(self):
        from install import InstallConfig
        config = InstallConfig.from_args(["--non-interactive", "--force"])
        assert config.non_interactive is True
        assert config.force is True


class TestDependencyGroups:
    """Test optional dependency groups for v2.7.0 features."""

    def test_knowledge_graph_deps(self):
        from install import get_optional_dependencies
        deps = get_optional_dependencies()
        kg_deps = deps.get("knowledge_graph", [])
        # Check for v2.7.0 knowledge graph dependencies
        assert isinstance(kg_deps, list)

    def test_embeddings_deps(self):
        from install import get_optional_dependencies
        deps = get_optional_dependencies()
        # Check for embedding-related dependencies (P1-001)
        assert "embeddings" in deps or "knowledge_graph" in deps

    def test_all_deps_have_descriptions(self):
        from install import get_optional_dependencies_with_descriptions
        deps = get_optional_dependencies_with_descriptions()
        for group_name, group_info in deps.items():
            assert "packages" in group_info
            assert "description" in group_info


class TestVersionInfo:
    """Test version information utilities."""

    def test_get_version(self):
        from install import get_version
        version = get_version()
        assert isinstance(version, str)
        assert version.count(".") >= 1  # At least X.Y format

    def test_version_matches_pyproject(self):
        from install import get_version
        import tomllib
        
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        if pyproject_path.exists():
            with open(pyproject_path, "rb") as f:
                pyproject = tomllib.load(f)
            expected_version = pyproject.get("project", {}).get("version")
            if expected_version:
                assert get_version() == expected_version


class TestInstallSummary:
    """Test installation summary generation."""

    def test_generate_summary(self):
        from install import generate_install_summary
        summary = generate_install_summary(
            installed=[("rich", "13.0.0"), ("aiohttp", "3.9.0")],
            failed=[],
            skipped=["outlines"],
        )
        assert "installed" in summary.lower() or "complete" in summary.lower()

    def test_summary_includes_failures(self):
        from install import generate_install_summary
        summary = generate_install_summary(
            installed=[("rich", "13.0.0")],
            failed=[("z3-solver", "Build error")],
            skipped=[],
        )
        assert "failed" in summary.lower() or "error" in summary.lower()


class TestHealthCheck:
    """Test post-installation health check."""

    def test_run_health_check(self):
        from install import run_health_check
        result = run_health_check()
        assert isinstance(result, dict)
        assert "python" in result
        assert "core_deps" in result

    def test_health_check_python_version(self):
        from install import run_health_check
        result = run_health_check()
        assert result["python"]["ok"] is True
        assert tuple(map(int, result["python"]["version"].split("."))) >= (3, 9)
