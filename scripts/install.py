#!/usr/bin/env python3
"""Cross-Platform Install Script for Agent Dashboard v2.7.0."""
import argparse, importlib, os, platform, shutil, sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION = "2.7.0"

class Colors:
    GREEN = "\033[0;32m" if sys.stdout.isatty() else ""
    YELLOW = "\033[1;33m" if sys.stdout.isatty() else ""
    BLUE = "\033[0;34m" if sys.stdout.isatty() else ""
    NC = "\033[0m" if sys.stdout.isatty() else ""

def print_status(s, m): print(f"  {Colors.GREEN if s=='OK' else Colors.YELLOW}[{s}]{Colors.NC} {m}")
def print_header(t): print(f"\n{Colors.BLUE}{t}{Colors.NC}")
def get_version(): return VERSION

@dataclass
class InstallConfig:
    non_interactive: bool = False
    force: bool = False
    skip_hooks: bool = False
    skip_optional: bool = False
    install_embeddings: bool = True
    install_tokenizer: bool = True
    install_z3: bool = False
    install_outlines: bool = False
    base_dir: Optional[str] = None

    @classmethod
    def from_args(cls, args):
        p = argparse.ArgumentParser(description="Agent Dashboard Installer")
        p.add_argument("--non-interactive", "-y", action="store_true")
        p.add_argument("--force", "-f", action="store_true")
        p.add_argument("--skip-hooks", action="store_true")
        p.add_argument("--skip-optional", action="store_true")
        p.add_argument("--with-z3", action="store_true")
        p.add_argument("--with-outlines", action="store_true")
        p.add_argument("--base-dir", type=str)
        a = p.parse_args(args)
        return cls(non_interactive=a.non_interactive, force=a.force, skip_hooks=a.skip_hooks,
                   skip_optional=a.skip_optional, install_z3=a.with_z3, install_outlines=a.with_outlines, base_dir=a.base_dir)

def detect_platform():
    system = platform.system().lower()
    os_name = {"windows": "windows", "darwin": "macos", "linux": "linux"}.get(system, "unknown")
    in_venv = hasattr(sys, "real_prefix") or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)
    return {"os": os_name, "python_cmd": sys.executable, "python_version": sys.version_info[:2], "in_venv": in_venv,
            "has_uv": shutil.which("uv") is not None, "is_windows": os_name == "windows"}

def check_dependencies(pkgs):
    result = {}
    for pkg in pkgs:
        try:
            mod = importlib.import_module(pkg.replace("-", "_"))
            result[pkg] = {"installed": True, "version": getattr(mod, "__version__", "installed")}
        except ImportError:
            result[pkg] = {"installed": False, "version": None}
    return result

def get_optional_dependencies():
    return {"knowledge_graph": ["networkx"], "embeddings": ["sentence-transformers", "pecanpy"],
            "search": ["rank-bm25", "hnswlib"], "tokenizer": ["transformers", "tokenizers"], "z3": ["z3-solver"]}

def get_optional_dependencies_with_descriptions():
    return {"knowledge_graph": {"packages": ["networkx"], "description": "Graph operations"},
            "embeddings": {"packages": ["sentence-transformers"], "description": "Semantic embeddings"},
            "search": {"packages": ["rank-bm25"], "description": "BM25 search"},
            "tokenizer": {"packages": ["transformers"], "description": "Claude tokenizer"},
            "z3": {"packages": ["z3-solver"], "description": "Z3 theorem prover"}}

def get_install_paths(base_dir=None):
    home = Path(base_dir) if base_dir else Path.home()
    cfg = home / ".claude"
    return {"home": str(home), "config_dir": str(cfg), "install_dir": str(cfg / "dashboard"),
            "agents_dir": str(cfg / "agents"), "commands_dir": str(cfg / "commands"),
            "bin_dir": str(home / ".local" / "bin"), "hooks_dir": str(cfg / "dashboard" / "hooks"),
            "logs_dir": str(cfg / "logs")}

def create_directory_structure(paths):
    created, errors = [], []
    for k in ["config_dir", "install_dir", "agents_dir", "commands_dir", "bin_dir", "hooks_dir", "logs_dir"]:
        try: Path(paths[k]).mkdir(parents=True, exist_ok=True); created.append(paths[k])
        except Exception as e: errors.append((paths[k], str(e)))
    return {"success": len(errors) == 0, "created": created, "errors": errors}

def generate_install_summary(installed, failed, skipped):
    lines = [f"\n{Colors.GREEN}{'=' * 60}{Colors.NC}", f"{Colors.GREEN}Installation Summary{Colors.NC}"]
    if installed: lines.extend([f"  Installed: {pkg} {ver}" for pkg, ver in installed])
    if skipped: lines.extend([f"  Skipped: {pkg}" for pkg in skipped])
    if failed: lines.extend([f"  Failed: {pkg} - {r}" for pkg, r in failed])
    return "\n".join(lines)

def run_health_check():
    result = {"python": {"ok": sys.version_info >= (3, 9), "version": f"{sys.version_info.major}.{sys.version_info.minor}"},
              "core_deps": {"ok": False, "details": {}}, "paths": {"ok": False, "details": {}}}
    deps = check_dependencies(["rich", "aiohttp"])
    result["core_deps"] = {"ok": all(d["installed"] for d in deps.values()), "details": deps}
    paths = get_install_paths()
    result["paths"] = {"ok": all(Path(p).exists() for p in paths.values()), "details": {k: Path(p).exists() for k, p in paths.items()}}
    return result

def print_banner():
    print(f"\n======================================================================\n    Agent Dashboard v{VERSION} Cross-Platform Installer\n======================================================================")

def main(args=None):
    if args is None: args = sys.argv[1:]
    if "--help" in args or "-h" in args: InstallConfig.from_args(["--help"]); return 0
    config = InstallConfig.from_args(args)
    print_banner()
    print_header("[1/4] Detecting platform...")
    pi = detect_platform()
    print_status("OK", f"{pi['os'].title()}")
    print_status("OK", f"Python {'.'.join(map(str, pi['python_version']))}")
    print_header("[2/4] Setting up directories...")
    paths = get_install_paths(config.base_dir)
    dr = create_directory_structure(paths)
    if dr["success"]:
        for p in dr["created"][:4]: print_status("OK", Path(p).name)
    else: return 1
    print_header("[3/4] Checking dependencies...")
    for pkg in ["rich", "aiohttp"]:
        d = check_dependencies([pkg])
        print_status("OK" if d[pkg]["installed"] else "WARN", f"{pkg} {'installed' if d[pkg]['installed'] else 'not installed'}")
    print_header("[4/4] Health Check...")
    h = run_health_check()
    print_status("OK" if h["python"]["ok"] else "WARN", f"Python: {h['python']['version']}")
    print(f"\nQuick Start:\n  agent-dashboard --web\n  agent-dashboard doctor\n")
    return 0

if __name__ == "__main__": sys.exit(main())
