#!/usr/bin/env python3
"""
Cross-platform compatibility tests.

These tests verify the dashboard works correctly across different
operating systems and Python environments.
"""

import os
import sys
import subprocess
import platform
import pytest
from pathlib import Path


class TestPythonEnvironment:
    """Tests for Python environment compatibility."""

    def test_python_version(self):
        """Python version should be 3.9+."""
        assert sys.version_info >= (3, 9), \
            f"Python 3.9+ required, found {sys.version}"

    def test_python_executable_exists(self):
        """At least one Python command should work."""
        commands = ['python3', 'python']
        found = False

        for cmd in commands:
            try:
                result = subprocess.run(
                    [cmd, '--version'],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    found = True
                    break
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue

        assert found, "No Python interpreter found"

    def test_sys_prefix_defined(self):
        """sys.prefix should be defined."""
        assert sys.prefix is not None
        assert len(sys.prefix) > 0


class TestDependencies:
    """Tests for required Python packages."""

    @pytest.mark.parametrize("package", ["rich", "aiohttp"])
    def test_required_package(self, package):
        """Required packages should be importable."""
        __import__(package)

    def test_tiktoken_optional(self):
        """tiktoken should work or gracefully degrade."""
        try:
            import tiktoken
            # If imported, encoding should work
            enc = tiktoken.get_encoding("cl100k_base")
            tokens = enc.encode("test")
            assert len(tokens) > 0
        except ImportError:
            # OK - tiktoken is optional
            pass
        except Exception as e:
            # Network errors are OK in CI
            if "network" in str(e).lower() or "connection" in str(e).lower():
                pytest.skip("tiktoken network error")
            raise


class TestInstallation:
    """Tests for installation structure."""

    def test_agents_directory_exists(self):
        """Agents directory should exist."""
        agents_dir = Path(__file__).parent.parent / "agents"
        assert agents_dir.exists(), "agents/ directory not found"

    def test_agents_count(self):
        """Should have 20 agent definitions (14 base + 6 panel judges)."""
        agents_dir = Path(__file__).parent.parent / "agents"
        agent_files = list(agents_dir.glob("*.md"))
        assert len(agent_files) == 20, \
            f"Expected 20 agents, found {len(agent_files)}"

    def test_all_agents_have_frontmatter(self):
        """All agent files should have valid YAML frontmatter."""
        agents_dir = Path(__file__).parent.parent / "agents"

        for agent_file in agents_dir.glob("*.md"):
            content = agent_file.read_text(encoding='utf-8')
            assert content.startswith("---"), \
                f"{agent_file.name} missing YAML frontmatter"
            assert "name:" in content, \
                f"{agent_file.name} missing 'name' field"
            assert "model:" in content, \
                f"{agent_file.name} missing 'model' field"

    def test_required_python_files_exist(self):
        """Required Python files should exist."""
        root = Path(__file__).parent.parent
        required = [
            "dashboard/agent_monitor.py",
            "src/web_server.py",
            "src/cli.py",
            "src/workflow_engine.py",
            "hooks/send_event.py",
        ]

        for filepath in required:
            assert (root / filepath).exists(), \
                f"Required file missing: {filepath}"

    def test_required_scripts_exist(self):
        """Required shell scripts should exist."""
        root = Path(__file__).parent.parent
        required = [
            "scripts/install.sh",
            "scripts/uninstall.sh",
            "scripts/upgrade.sh",
            "scripts/doctor.sh",
            "scripts/docker-start.sh",
        ]

        for filepath in required:
            assert (root / filepath).exists(), \
                f"Required script missing: {filepath}"

    def test_docker_files_exist(self):
        """Docker files should exist."""
        root = Path(__file__).parent.parent
        required = [
            "Dockerfile",
            "docker-compose.yml",
            ".dockerignore",
        ]

        for filepath in required:
            assert (root / filepath).exists(), \
                f"Docker file missing: {filepath}"

    def test_documentation_files_exist(self):
        """Documentation files should exist."""
        root = Path(__file__).parent.parent
        required = [
            "README.md",
            "INSTALL.md",
            "TROUBLESHOOTING.md",
            "requirements.txt",
            "pyproject.toml",
        ]

        for filepath in required:
            assert (root / filepath).exists(), \
                f"Documentation file missing: {filepath}"


class TestScripts:
    """Tests for shell scripts."""

    def test_install_script_has_unix_line_endings(self):
        """install.sh should have Unix line endings (LF)."""
        script = Path(__file__).parent.parent / "scripts" / "install.sh"
        content = script.read_bytes()

        # Check for CRLF (Windows line endings)
        assert b'\r\n' not in content, \
            "install.sh has Windows line endings (CRLF). Convert to Unix (LF)."

    def test_install_script_is_executable(self):
        """install.sh should be executable on Unix."""
        if platform.system() == "Windows":
            pytest.skip("Executable check not applicable on Windows")

        script = Path(__file__).parent.parent / "scripts" / "install.sh"
        assert os.access(script, os.X_OK), \
            "install.sh is not executable. Run: chmod +x scripts/install.sh"

    def test_install_script_has_shebang(self):
        """install.sh should have proper shebang."""
        script = Path(__file__).parent.parent / "scripts" / "install.sh"
        first_line = script.read_text().split('\n')[0]

        assert first_line.startswith("#!/"), \
            "install.sh missing shebang"
        assert "bash" in first_line or "sh" in first_line, \
            f"Unexpected shebang: {first_line}"

    def test_all_scripts_have_unix_line_endings(self):
        """All shell scripts should have Unix line endings."""
        scripts_dir = Path(__file__).parent.parent / "scripts"

        for script in scripts_dir.glob("*.sh"):
            content = script.read_bytes()
            assert b'\r\n' not in content, \
                f"{script.name} has Windows line endings (CRLF)"


class TestNoStaleReferences:
    """Tests for stale references in documentation."""

    def test_no_11_agent_references(self):
        """No files should reference '11 agent' (should be 14)."""
        root = Path(__file__).parent.parent
        stale_pattern = "11 " + "agent"  # Split to avoid self-match

        files_to_check = list(root.glob("**/*.py")) + \
                        list(root.glob("**/*.md")) + \
                        list(root.glob("**/*.sh"))

        for filepath in files_to_check:
            # Skip git directory and test files (which contain the pattern for testing)
            if '.git' in str(filepath) or 'test_cross_platform.py' in str(filepath):
                continue

            try:
                content = filepath.read_text(encoding='utf-8')
                assert stale_pattern not in content.lower(), \
                    f"Stale agent count reference found in {filepath}"
            except (UnicodeDecodeError, OSError):
                continue  # Skip binary files or files with encoding issues


class TestPlatformSpecific:
    """Platform-specific tests."""

    @pytest.mark.skipif(
        platform.system() != "Windows",
        reason="Windows-specific test"
    )
    def test_windows_python_command(self):
        """On Windows, 'python' command should work."""
        result = subprocess.run(
            ["python", "--version"],
            capture_output=True
        )
        assert result.returncode == 0

    @pytest.mark.skipif(
        platform.system() != "Darwin",
        reason="macOS-specific test"
    )
    def test_macos_python3_command(self):
        """On macOS, 'python3' command should work."""
        result = subprocess.run(
            ["python3", "--version"],
            capture_output=True
        )
        assert result.returncode == 0

    @pytest.mark.skipif(
        platform.system() != "Linux",
        reason="Linux-specific test"
    )
    def test_linux_python3_command(self):
        """On Linux, 'python3' command should work."""
        result = subprocess.run(
            ["python3", "--version"],
            capture_output=True
        )
        assert result.returncode == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
