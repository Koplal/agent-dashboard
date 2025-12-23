#!/usr/bin/env bash
# =============================================================================
# install.sh - Agent Dashboard v2.6.0 Installation Script
# =============================================================================
#
# DESCRIPTION:
#   Automated installer for the Agent Dashboard multi-agent workflow framework.
#   Installs 14 specialized agents, dashboard components, and configures
#   Claude Code hooks for real-time monitoring.
#
# CROSS-PLATFORM SUPPORT:
#   - Windows: Git Bash, WSL2 (not PowerShell/CMD)
#   - macOS: Bash, Zsh (Intel & Apple Silicon)
#   - Linux: All major distributions
#   - Docker: Containerized deployment
#
# USAGE:
#   ./scripts/install.sh
#   ./scripts/install.sh --non-interactive  # Skip prompts
#   ./scripts/install.sh --force            # Overwrite existing files
#
# VERSION: 2.6.0
# =============================================================================

# Note: set -e removed for controlled error handling
# Critical errors are handled explicitly with verification steps

# =============================================================================
# COMMAND LINE ARGUMENT PARSING
# =============================================================================
NON_INTERACTIVE=false
FORCE_INSTALL=false

for arg in "$@"; do
    case $arg in
        --non-interactive|-y)
            NON_INTERACTIVE=true
            ;;
        --force|-f)
            FORCE_INSTALL=true
            ;;
        --help|-h)
            echo "Usage: install.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --non-interactive, -y  Skip all prompts, use defaults"
            echo "  --force, -f            Force overwrite existing files"
            echo "  --help, -h             Show this help message"
            exit 0
            ;;
    esac
done

if [ "$NON_INTERACTIVE" = true ]; then
    echo -e "\033[0;36m[INFO]\033[0m Running in non-interactive mode"
fi

# =============================================================================
# LINE ENDING NORMALIZATION (Windows Fix)
# =============================================================================
# Ensure this script has Unix line endings (LF, not CRLF)
# This fixes "command not found" errors on Windows when files have CRLF

if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    IS_WINDOWS=true
    # Check for CRLF line endings
    if head -1 "$0" 2>/dev/null | grep -q $'\r'; then
        echo "Converting line endings to Unix format..."
        sed -i 's/\r$//' "$0" 2>/dev/null || true
        echo "Please re-run the script: ./scripts/install.sh"
        exit 0
    fi
else
    IS_WINDOWS=false
fi

# =============================================================================
# COLOR DEFINITIONS
# =============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# =============================================================================
# ERROR HANDLING FRAMEWORK
# =============================================================================
INSTALL_LOG="$HOME/.claude/install.log"

# Severity levels
SEVERITY_CRITICAL="CRITICAL"
SEVERITY_WARNING="WARNING"
SEVERITY_INFO="INFO"

# Installation status tracking
declare -A INSTALL_STATUS=(
    [cli_launcher]="pending"
    [dependency_rich]="pending"
    [dependency_aiohttp]="pending"
    [path_update]="pending"
)

# Log message to install log file
log_message() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    mkdir -p "$(dirname "$INSTALL_LOG")" 2>/dev/null
    echo "[$timestamp] $message" >> "$INSTALL_LOG" 2>/dev/null
}

# Show formatted error message
show_error() {
    local severity="$1"
    local code="$2"
    local message="$3"
    local suggestion="$4"
    
    case "$severity" in
        CRITICAL) echo -e "${RED}[$severity]${NC} $message" ;;
        WARNING)  echo -e "${YELLOW}[$severity]${NC} $message" ;;
        INFO)     echo -e "${CYAN}[$severity]${NC} $message" ;;
    esac
    
    if [ -n "$suggestion" ]; then
        echo -e "         ${CYAN}Suggestion:${NC} $suggestion"
    fi
    
    log_message "[$severity] $code: $message"
}

# Prompt user for action (Retry/Continue/Abort)
prompt_user() {
    local prompt_message="$1"
    local default="${2:-a}"  # Default to abort
    
    if [ "$NON_INTERACTIVE" = true ]; then
        echo "Non-interactive mode: using default ($default)"
        echo "$default"
        return
    fi
    
    echo ""
    echo -e "${YELLOW}$prompt_message${NC}"
    echo -e "  [${GREEN}R${NC}]etry  |  [${YELLOW}C${NC}]ontinue anyway  |  [${RED}A${NC}]bort"
    read -p "  Choice [$default]: " -n 1 -r choice
    echo ""
    
    choice=${choice:-$default}
    echo "${choice,,}"  # Return lowercase
}

# Verify Python package is importable
verify_python_import() {
    local package="$1"
    $PYTHON_CMD -c "import $package" 2>/dev/null
    return $?
}

# Update installation status
update_status() {
    local component="$1"
    local status="$2"
    INSTALL_STATUS[$component]="$status"
    log_message "Status update: $component = $status"
}

# =============================================================================
# DIRECTORY CONFIGURATION
# =============================================================================
INSTALL_DIR="$HOME/.claude/dashboard"
AGENTS_DIR="$HOME/.claude/agents"
CONFIG_DIR="$HOME/.claude"
COMMANDS_DIR="$HOME/.claude/commands"
BIN_DIR="$HOME/.local/bin"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Initialize install log
log_message "=== Installation started ==="
log_message "Platform: $OSTYPE"
log_message "Non-interactive: $NON_INTERACTIVE"

# =============================================================================
# INSTALLATION BANNER
# =============================================================================
echo -e "${MAGENTA}"
echo "============================================================================="
echo "                    Agent Dashboard v2.6.0 Installer                           "
echo "            Multi-Agent Workflow Framework for Claude Code                   "
echo "============================================================================="
echo ""
echo "  Agent Tiers (16 agents total):"
echo "    Tier 0 (Sonnet/Haiku): prompt-enhancer, prompt-validator"
echo "    Tier 1 (Opus):   orchestrator, synthesis, critic, planner"
echo "    Tier 2 (Sonnet): researcher, perplexity, judge, auditor, implementer"
echo "    Tier 3 (Haiku):  web-search, summarizer, test-writer, installer, validator"
echo ""
echo "  Slash Commands: /project, /enhance"
echo ""
echo "============================================================================="
echo -e "${NC}"

# =============================================================================
# PLATFORM DETECTION
# =============================================================================
echo -e "${BLUE}[1/9] Detecting platform...${NC}"

IS_MACOS=false
IS_LINUX=false
IS_HEADLESS=false
MACOS_ARCH=""
LINUX_DISTRO=""
HOMEBREW_PREFIX="/usr/local"

if [[ "$OSTYPE" == "darwin"* ]]; then
    IS_MACOS=true
    if [[ $(uname -m) == "arm64" ]]; then
        MACOS_ARCH="Apple Silicon"
        HOMEBREW_PREFIX="/opt/homebrew"
    else
        MACOS_ARCH="Intel"
    fi
    echo -e "  ${GREEN}[OK]${NC} macOS ($MACOS_ARCH)"

    # Check for Xcode Command Line Tools
    if ! xcode-select -p &> /dev/null; then
        echo -e "  ${YELLOW}[WARN]${NC} Xcode Command Line Tools not installed"
        echo "         Some pip packages may fail to build."
        echo "         Install with: xcode-select --install"
    fi

elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    IS_LINUX=true

    # Detect distro
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        LINUX_DISTRO="$ID"
        echo -e "  ${GREEN}[OK]${NC} Linux ($LINUX_DISTRO)"
    else
        LINUX_DISTRO="unknown"
        echo -e "  ${GREEN}[OK]${NC} Linux"
    fi

    # Check if headless (no display)
    if [ -z "$DISPLAY" ] && [ -z "$WAYLAND_DISPLAY" ]; then
        IS_HEADLESS=true
        echo -e "  ${CYAN}[INFO]${NC} Headless server detected"
    fi

elif [ "$IS_WINDOWS" = true ]; then
    echo -e "  ${GREEN}[OK]${NC} Windows (Git Bash/MSYS)"
else
    echo -e "  ${YELLOW}[WARN]${NC} Unknown platform: $OSTYPE"
fi

# =============================================================================
# PYTHON DETECTION - Cross-Platform Compatible
# =============================================================================
# Finds Python 3.9+ on any platform:
#   - Linux/macOS: typically 'python3'
#   - Windows Git Bash: typically 'python'
#   - pyenv/conda: may use versioned names

find_python() {
    local cmd version major minor

    # Priority order: python3 (Unix standard), python (Windows), versioned
    for cmd in python3 python python3.12 python3.11 python3.10 python3.9; do
        if command -v "$cmd" &> /dev/null; then
            # Verify it's actually Python and get version
            version=$("$cmd" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null) || continue
            major=$("$cmd" -c 'import sys; print(sys.version_info.major)' 2>/dev/null) || continue
            minor=$("$cmd" -c 'import sys; print(sys.version_info.minor)' 2>/dev/null) || continue

            # Check version >= 3.9
            if [ "$major" -ge 3 ] && [ "$minor" -ge 9 ]; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    return 1
}

find_pip() {
    local cmd

    # Try pip commands in order of preference
    for cmd in pip3 pip; do
        if command -v "$cmd" &> /dev/null; then
            if "$cmd" --version &> /dev/null; then
                echo "$cmd"
                return 0
            fi
        fi
    done

    # Fallback to python -m pip
    if [ -n "$PYTHON_CMD" ]; then
        if "$PYTHON_CMD" -m pip --version &> /dev/null; then
            echo "$PYTHON_CMD -m pip"
            return 0
        fi
    fi

    return 1
}

echo -e "\n${BLUE}[2/9] Checking Python installation...${NC}"

# Ensure Homebrew Python is in PATH (macOS)
if [ "$IS_MACOS" = true ] && [ -d "$HOMEBREW_PREFIX/bin" ]; then
    export PATH="$HOMEBREW_PREFIX/bin:$PATH"
fi

PYTHON_CMD=$(find_python)
if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}ERROR: Python 3.9+ is required but not found.${NC}"
    echo ""
    echo "Commands checked: python3, python, python3.12, python3.11, python3.10, python3.9"
    echo ""
    echo "Installation instructions by platform:"
    echo ""
    if [ "$IS_WINDOWS" = true ]; then
        echo "  Windows (Git Bash):"
        echo "    1. Download from https://www.python.org/downloads/"
        echo "    2. Run installer - CHECK 'Add Python to PATH'"
        echo "    3. Restart Git Bash"
    elif [ "$IS_MACOS" = true ]; then
        echo "  macOS (Homebrew):"
        echo "    brew install python@3.11"
    elif [ "$IS_LINUX" = true ]; then
        case "$LINUX_DISTRO" in
            ubuntu|debian|pop)
                echo "  Ubuntu/Debian:"
                echo "    sudo apt update && sudo apt install python3 python3-pip python3-venv"
                ;;
            fedora)
                echo "  Fedora:"
                echo "    sudo dnf install python3 python3-pip"
                ;;
            centos|rhel|rocky|alma)
                echo "  RHEL/CentOS:"
                echo "    sudo dnf install python3 python3-pip"
                ;;
            arch|manjaro)
                echo "  Arch Linux:"
                echo "    sudo pacman -S python python-pip"
                ;;
            *)
                echo "  Linux:"
                echo "    Use your package manager to install python3 and python3-pip"
                ;;
        esac
    else
        echo "  Visit: https://www.python.org/downloads/"
    fi
    echo ""
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "  ${GREEN}[OK]${NC} Python $PYTHON_VERSION (command: $PYTHON_CMD)"

# Store for use in generated scripts
export PYTHON_CMD
export PYTHON_VERSION

# =============================================================================
# VIRTUAL ENVIRONMENT DETECTION
# =============================================================================
echo -e "\n${BLUE}[3/9] Checking Python environment...${NC}"

IN_VENV=false

if [ -n "$VIRTUAL_ENV" ]; then
    echo -e "  ${GREEN}[OK]${NC} Virtual environment: $VIRTUAL_ENV"
    IN_VENV=true
elif [ -n "$CONDA_PREFIX" ]; then
    echo -e "  ${GREEN}[OK]${NC} Conda environment: $CONDA_PREFIX"
    IN_VENV=true
    if [ "$CONDA_DEFAULT_ENV" = "base" ]; then
        echo -e "  ${YELLOW}[WARN]${NC} Installing to conda 'base' environment"
        echo "         Consider: conda create -n claude-dashboard python=3.11"
    fi
elif $PYTHON_CMD -c "import sys; sys.exit(0 if sys.prefix != sys.base_prefix else 1)" 2>/dev/null; then
    echo -e "  ${GREEN}[OK]${NC} Virtual environment detected"
    IN_VENV=true
else
    echo -e "  ${CYAN}[INFO]${NC} No virtual environment (installing to user site-packages)"
fi

# Warn about pyenv
if command -v pyenv &> /dev/null; then
    PYENV_VERSION=$(pyenv version-name 2>/dev/null)
    echo -e "  ${CYAN}[INFO]${NC} pyenv detected (version: $PYENV_VERSION)"
fi

# =============================================================================
# PACKAGE MANAGER CHECK
# =============================================================================
echo -e "\n${BLUE}[4/9] Checking package manager...${NC}"

PKG_MANAGER=""
PIP_CMD=""

# Check for uv first (10-100x faster than pip)
if command -v uv &> /dev/null; then
    PKG_MANAGER="uv"
    echo -e "  ${GREEN}[OK]${NC} uv package manager (recommended)"
else
    PIP_CMD=$(find_pip)
    if [ -z "$PIP_CMD" ]; then
        echo -e "${RED}ERROR: No package manager found.${NC}"
        echo ""
        echo "Install pip:"
        echo "  $PYTHON_CMD -m ensurepip --upgrade"
        echo ""
        echo "Or install uv (recommended - much faster):"
        echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
        echo ""
        exit 1
    fi
    PKG_MANAGER="pip"
    echo -e "  ${YELLOW}[OK]${NC} $PIP_CMD (consider installing uv for faster installs)"
fi

# Check Claude Code CLI (optional)
if command -v claude &> /dev/null; then
    echo -e "  ${GREEN}[OK]${NC} Claude Code CLI detected"
else
    echo -e "  ${YELLOW}[WARN]${NC} Claude Code CLI not found"
    echo -e "         Install from: ${CYAN}https://docs.anthropic.com/claude-code${NC}"
fi

# =============================================================================
# CREATE DIRECTORY STRUCTURE
# =============================================================================
echo -e "\n${BLUE}[5/9] Creating directory structure...${NC}"

mkdir -p "$INSTALL_DIR/hooks"
mkdir -p "$AGENTS_DIR"
mkdir -p "$BIN_DIR"
mkdir -p "$CONFIG_DIR/logs"

echo -e "  ${GREEN}[OK]${NC} $INSTALL_DIR"
echo -e "  ${GREEN}[OK]${NC} $INSTALL_DIR/hooks"
echo -e "  ${GREEN}[OK]${NC} $AGENTS_DIR"
echo -e "  ${GREEN}[OK]${NC} $BIN_DIR"

# =============================================================================
# INSTALL DASHBOARD FILES
# =============================================================================
echo -e "\n${BLUE}[6/9] Installing dashboard files...${NC}"

# Core Python modules
cp "$SCRIPT_DIR/dashboard/agent_monitor.py" "$INSTALL_DIR/"
echo -e "  ${GREEN}[OK]${NC} agent_monitor.py (Terminal TUI)"

cp "$SCRIPT_DIR/src/web_server.py" "$INSTALL_DIR/"
echo -e "  ${GREEN}[OK]${NC} web_server.py (Web dashboard)"

cp "$SCRIPT_DIR/src/cli.py" "$INSTALL_DIR/"
echo -e "  ${GREEN}[OK]${NC} cli.py (CLI interface)"

cp "$SCRIPT_DIR/src/workflow_engine.py" "$INSTALL_DIR/"
echo -e "  ${GREEN}[OK]${NC} workflow_engine.py (Workflow orchestration)"

cp "$SCRIPT_DIR/hooks/send_event.py" "$INSTALL_DIR/hooks/"
echo -e "  ${GREEN}[OK]${NC} hooks/send_event.py (Event capture)"

# Create cross-platform hook wrapper
cat > "$INSTALL_DIR/hooks/run_hook.sh" << 'HOOK_WRAPPER_EOF'
#!/usr/bin/env bash
# =============================================================================
# run_hook.sh - Cross-Platform Hook Wrapper
# =============================================================================
# Finds the correct Python command and executes send_event.py
# Works on: Windows Git Bash, macOS, Linux, WSL2

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Find Python (same logic as installer)
find_python() {
    for cmd in python3 python python3.11 python3.10 python3.9; do
        if command -v "$cmd" &> /dev/null; then
            local major minor
            major=$("$cmd" -c 'import sys; print(sys.version_info.major)' 2>/dev/null) || continue
            minor=$("$cmd" -c 'import sys; print(sys.version_info.minor)' 2>/dev/null) || continue
            if [ "$major" -ge 3 ] && [ "$minor" -ge 9 ]; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    return 1
}

PYTHON_CMD=$(find_python)

# Silently exit if no Python (don't break Claude Code)
if [ -z "$PYTHON_CMD" ]; then
    exit 0
fi

# Execute the hook
exec "$PYTHON_CMD" "$SCRIPT_DIR/send_event.py" "$@"
HOOK_WRAPPER_EOF

chmod +x "$INSTALL_DIR/hooks/run_hook.sh"
echo -e "  ${GREEN}[OK]${NC} hooks/run_hook.sh (Cross-platform wrapper)"

# Install agent definitions (append-safe: skip if file exists and is newer)
AGENT_COUNT=0
AGENT_SKIPPED=0
for agent_file in "$SCRIPT_DIR/agents/"*.md; do
    if [ -f "$agent_file" ]; then
        agent_name=$(basename "$agent_file")
        target_file="$AGENTS_DIR/$agent_name"
        if [ -f "$target_file" ]; then
            # File exists - check if source is newer or force install
            if [ "$FORCE_INSTALL" = true ] || [ "$agent_file" -nt "$target_file" ]; then
                cp "$agent_file" "$target_file"
                AGENT_COUNT=$((AGENT_COUNT + 1))
            else
                AGENT_SKIPPED=$((AGENT_SKIPPED + 1))
            fi
        else
            cp "$agent_file" "$AGENTS_DIR/"
            AGENT_COUNT=$((AGENT_COUNT + 1))
        fi
    fi
done
echo -e "  ${GREEN}[OK]${NC} Installed $AGENT_COUNT agent definitions"
if [ $AGENT_SKIPPED -gt 0 ]; then
    echo -e "  ${CYAN}[INFO]${NC} Skipped $AGENT_SKIPPED existing agent files (use --force to overwrite)"
fi

# Install CLAUDE.md project context file
CLAUDE_MD_SRC="$SCRIPT_DIR/CLAUDE.md"
CLAUDE_MD_DST="$CONFIG_DIR/CLAUDE.md"
if [ -f "$CLAUDE_MD_SRC" ]; then
    if [ -f "$CLAUDE_MD_DST" ]; then
        # Append new content if not already present
        if ! grep -q "Agent Definitions" "$CLAUDE_MD_DST" 2>/dev/null; then
            echo "" >> "$CLAUDE_MD_DST"
            echo "# --- Agent Dashboard Context (appended) ---" >> "$CLAUDE_MD_DST"
            cat "$CLAUDE_MD_SRC" >> "$CLAUDE_MD_DST"
            echo -e "  ${GREEN}[OK]${NC} Appended agent context to existing CLAUDE.md"
        else
            echo -e "  ${CYAN}[INFO]${NC} CLAUDE.md already contains agent context"
        fi
    else
        cp "$CLAUDE_MD_SRC" "$CLAUDE_MD_DST"
        echo -e "  ${GREEN}[OK]${NC} Installed CLAUDE.md (project context)"
    fi
fi

# Display agent summary
echo ""
echo -e "  ${CYAN}Installed Agents by Tier:${NC}"
echo ""
echo -e "  ${GREEN}Tier 0 - Prompt Enhancement [\$]:${NC}"
echo "    prompt-enhancer (Sonnet), prompt-validator (Haiku)"
echo ""
echo -e "  ${MAGENTA}Tier 1 - Opus (Strategic) [\$\$\$]:${NC}"
echo "    orchestrator, synthesis, critic, planner"
echo ""
echo -e "  ${BLUE}Tier 2 - Sonnet (Analysis) [\$\$]:${NC}"
echo "    researcher, perplexity-researcher, research-judge,"
echo "    claude-md-auditor, implementer"
echo ""
echo -e "  ${CYAN}Tier 3 - Haiku (Execution) [\$]:${NC}"
echo "    web-search-researcher, summarizer, test-writer,"
echo "    installer, validator"

# =============================================================================
# INSTALL SLASH COMMANDS
# =============================================================================
echo -e "\n${BLUE}[7/9] Installing slash commands...${NC}"

mkdir -p "$COMMANDS_DIR"

if [ -d "$SCRIPT_DIR/commands" ]; then
    COMMAND_COUNT=0
    for cmd_file in "$SCRIPT_DIR/commands"/*.md; do
        if [ -f "$cmd_file" ]; then
            cp "$cmd_file" "$COMMANDS_DIR/"
            cmd_name=$(basename "$cmd_file" .md)
            echo -e "  ${GREEN}[OK]${NC} /${cmd_name}"
            ((COMMAND_COUNT++))
        fi
    done
    echo -e "  ${GREEN}[OK]${NC} Installed $COMMAND_COUNT slash commands"
else
    echo -e "  ${YELLOW}[SKIP]${NC} No commands directory found"
fi

# =============================================================================
# CREATE CLI LAUNCHER SCRIPT
# =============================================================================
echo -e "\n${BLUE}[8/9] Creating CLI launcher...${NC}"

# Pre-flight: Ensure BIN_DIR exists and is writable
if [ ! -d "$BIN_DIR" ]; then
    mkdir -p "$BIN_DIR" 2>/dev/null
    if [ $? -ne 0 ]; then
        show_error "$SEVERITY_CRITICAL" "E001" \
            "Cannot create directory $BIN_DIR" \
            "Run: mkdir -p $BIN_DIR"
        choice=$(prompt_user "Directory creation failed. What would you like to do?" "a")
        case "$choice" in
            c) update_status "cli_launcher" "skipped" ;;
            *) exit 1 ;;
        esac
    fi
fi

cat > "$BIN_DIR/agent-dashboard" << 'LAUNCHER_EOF'
#!/usr/bin/env bash
# =============================================================================
# agent-dashboard - Cross-Platform CLI Launcher v2.3
# =============================================================================

DASHBOARD_DIR="$HOME/.claude/dashboard"

# Detect platform
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    IS_WINDOWS=true
else
    IS_WINDOWS=false
fi

# Find Python
find_python() {
    for cmd in python3 python python3.11 python3.10 python3.9; do
        if command -v "$cmd" &> /dev/null; then
            local major minor
            major=$("$cmd" -c 'import sys; print(sys.version_info.major)' 2>/dev/null) || continue
            minor=$("$cmd" -c 'import sys; print(sys.version_info.minor)' 2>/dev/null) || continue
            if [ "$major" -ge 3 ] && [ "$minor" -ge 9 ]; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    return 1
}

PYTHON_CMD=$(find_python)
if [ -z "$PYTHON_CMD" ]; then
    echo "ERROR: Python 3.9+ not found"
    echo ""
    echo "Install Python from https://python.org"
    if [ "$IS_WINDOWS" = true ]; then
        echo "  - Make sure to check 'Add Python to PATH' during installation"
        echo "  - Restart Git Bash after installing"
    fi
    exit 1
fi

# Parse arguments
WEB_MODE=false
PORT=4200
COMMAND=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --web|-w)
            WEB_MODE=true
            shift
            ;;
        --port|-p)
            PORT="$2"
            shift 2
            ;;
        doctor|status|test|tokenizer|uninstall|upgrade|logs|config)
            COMMAND="$1"
            shift
            break
            ;;
        --help|-h)
            echo "Agent Dashboard v2.6.0 - Multi-Agent Workflow Monitor"
            echo ""
            echo "USAGE:"
            echo "  agent-dashboard [OPTIONS] [COMMAND]"
            echo ""
            echo "OPTIONS:"
            echo "  --web, -w     Launch web dashboard (default: terminal TUI)"
            echo "  --port, -p    Server port (default: 4200)"
            echo "  --help, -h    Show this help message"
            echo ""
            echo "COMMANDS:"
            echo "  doctor        Diagnose installation issues"
            echo "  status        Show system status"
            echo "  test          Send a test event"
            echo "  tokenizer     Show tokenizer status"
            echo "  uninstall     Remove Agent Dashboard"
            echo "  upgrade       Update to latest version"
            echo "  logs          View recent logs"
            echo "  config        Show configuration"
            echo ""
            echo "EXAMPLES:"
            echo "  agent-dashboard              # Terminal TUI dashboard"
            echo "  agent-dashboard --web        # Web dashboard on port 4200"
            echo "  agent-dashboard doctor       # Check installation"
            echo "  agent-dashboard tokenizer    # Show tokenizer status"
            echo ""
            exit 0
            ;;
        *)
            shift
            ;;
    esac
done

# Handle commands
case "$COMMAND" in
    doctor)
        $PYTHON_CMD "$DASHBOARD_DIR/cli.py" doctor "$@"
        exit $?
        ;;
    status)
        $PYTHON_CMD "$DASHBOARD_DIR/cli.py" status "$@"
        exit $?
        ;;
    test)
        $PYTHON_CMD "$DASHBOARD_DIR/cli.py" test "$@"
        exit $?
        ;;
    uninstall)
        if [ -f "$HOME/.claude/scripts/uninstall.sh" ]; then
            bash "$HOME/.claude/scripts/uninstall.sh"
        else
            echo "Uninstall script not found. Manual removal:"
            echo "  rm -rf ~/.claude/dashboard ~/.claude/agents ~/.local/bin/agent-dashboard"
        fi
        exit $?
        ;;
    upgrade)
        if [ -f "$HOME/.claude/scripts/upgrade.sh" ]; then
            bash "$HOME/.claude/scripts/upgrade.sh"
        else
            echo "Upgrade script not found. Manual upgrade:"
            echo "  cd agent-dashboard && git pull && ./scripts/install.sh"
        fi
        exit $?
        ;;
    logs)
        $PYTHON_CMD "$DASHBOARD_DIR/cli.py" logs "$@"
        exit $?
        ;;
    config)
        $PYTHON_CMD "$DASHBOARD_DIR/cli.py" config "$@"
        exit $?
        ;;
    tokenizer)
        $PYTHON_CMD "$DASHBOARD_DIR/cli.py" tokenizer "$@"
        exit $?
        ;;
esac

# Auto-install missing dependencies
for pkg in rich aiohttp; do
    if ! $PYTHON_CMD -c "import $pkg" 2>/dev/null; then
        echo "Installing missing dependency: $pkg"
        $PYTHON_CMD -m pip install --quiet --user "$pkg" 2>/dev/null || \
        $PYTHON_CMD -m pip install --quiet "$pkg"
    fi
done

# Launch dashboard
if [ "$WEB_MODE" = true ]; then
    echo ""
    echo "Starting Agent Dashboard v2.6.0 (Web Mode)"
    echo "==========================================="
    echo ""
    echo "  URL: http://localhost:$PORT"
    echo ""
    if [ "$IS_WINDOWS" = true ]; then
        echo "  Windows: Firewall may prompt - click 'Allow access'"
    fi
    echo "  Press Ctrl+C to stop"
    echo ""
    $PYTHON_CMD "$DASHBOARD_DIR/web_server.py" --port "$PORT"
else
    echo ""
    echo "Starting Agent Dashboard v2.6.0 (Terminal TUI)"
    echo "============================================="
    echo ""
    echo "  Press 'q' to quit"
    echo ""
    $PYTHON_CMD "$DASHBOARD_DIR/agent_monitor.py" --port "$PORT"
fi
LAUNCHER_EOF

chmod +x "$BIN_DIR/agent-dashboard"

# Verify launcher was created successfully
if [ ! -f "$BIN_DIR/agent-dashboard" ]; then
    show_error "$SEVERITY_CRITICAL" "E004" \
        "CLI launcher was not created at $BIN_DIR/agent-dashboard" \
        "Check that $BIN_DIR exists and is writable"
    
    choice=$(prompt_user "CLI launcher creation failed. What would you like to do?" "a")
    case "$choice" in
        r) 
            # Retry logic - attempt mkdir and recreate
            mkdir -p "$BIN_DIR" 2>/dev/null
            echo -e "${YELLOW}Please re-run the installer to retry launcher creation${NC}"
            update_status "cli_launcher" "failed"
            ;;
        c)
            update_status "cli_launcher" "failed"
            echo -e "${YELLOW}Continuing without CLI launcher...${NC}"
            ;;
        *)
            echo -e "${RED}Installation aborted.${NC}"
            exit 1
            ;;
    esac
elif [ ! -x "$BIN_DIR/agent-dashboard" ]; then
    show_error "$SEVERITY_WARNING" "E003" \
        "CLI launcher exists but is not executable" \
        "Run: chmod +x $BIN_DIR/agent-dashboard"
    chmod +x "$BIN_DIR/agent-dashboard" 2>/dev/null || true
    update_status "cli_launcher" "warning"
else
    update_status "cli_launcher" "success"
    echo -e "  ${GREEN}[OK]${NC} Created $BIN_DIR/agent-dashboard"
fi

# =============================================================================
# INSTALL PYTHON DEPENDENCIES
# =============================================================================
echo -e "\n${BLUE}[9/9] Installing Python dependencies...${NC}"

# Core dependencies installation function
install_core_deps() {
    if [ "$IN_VENV" = true ]; then
        $PYTHON_CMD -m pip install --quiet rich aiohttp 2>/dev/null || \
        $PYTHON_CMD -m pip install rich aiohttp
    else
        $PYTHON_CMD -m pip install --quiet --user rich aiohttp 2>/dev/null || \
        $PYTHON_CMD -m pip install --user rich aiohttp
    fi
}

# Tokenizer installation function
install_tokenizer() {
    local tokenizer_type="$1"
    if [ "$IN_VENV" = true ]; then
        case "$tokenizer_type" in
            transformers)
                $PYTHON_CMD -m pip install --quiet transformers tokenizers 2>/dev/null || \
                $PYTHON_CMD -m pip install transformers tokenizers
                ;;
            tiktoken)
                $PYTHON_CMD -m pip install --quiet tiktoken 2>/dev/null || \
                $PYTHON_CMD -m pip install tiktoken
                ;;
        esac
    else
        case "$tokenizer_type" in
            transformers)
                $PYTHON_CMD -m pip install --quiet --user transformers tokenizers 2>/dev/null || \
                $PYTHON_CMD -m pip install --user transformers tokenizers
                ;;
            tiktoken)
                $PYTHON_CMD -m pip install --quiet --user tiktoken 2>/dev/null || \
                $PYTHON_CMD -m pip install --user tiktoken
                ;;
        esac
    fi
}

# Verify and retry installation function
verify_and_retry_install() {
    local package="$1"
    local description="$2"
    local retry_count=0
    local max_retries=1
    
    while [ $retry_count -le $max_retries ]; do
        if verify_python_import "$package"; then
            local version=$($PYTHON_CMD -c "import $package; print(getattr($package, '__version__', 'installed'))" 2>/dev/null)
            echo -e "  ${GREEN}[OK]${NC} $package $version ($description)"
            update_status "dependency_$package" "success"
            return 0
        fi
        
        if [ $retry_count -lt $max_retries ]; then
            echo -e "  ${YELLOW}[RETRY]${NC} $package import failed, retrying installation..."
            log_message "Retrying $package installation (attempt $((retry_count + 2)))"
            
            if [ "$IN_VENV" = true ]; then
                $PYTHON_CMD -m pip install --quiet "$package" 2>/dev/null
            else
                $PYTHON_CMD -m pip install --quiet --user "$package" 2>/dev/null
            fi
        fi
        
        retry_count=$((retry_count + 1))
    done
    
    # Failed after retries
    show_error "$SEVERITY_CRITICAL" "E006" \
        "Package '$package' installed but cannot be imported" \
        "Run: $PYTHON_CMD -m pip install $package"
    
    update_status "dependency_$package" "failed"
    
    choice=$(prompt_user "Dependency verification failed. What would you like to do?" "c")
    case "$choice" in
        r)
            $PYTHON_CMD -m pip install "$package"
            if verify_python_import "$package"; then
                update_status "dependency_$package" "success"
            fi
            ;;
        c)
            echo -e "${YELLOW}Continuing without $package...${NC}"
            ;;
        *)
            echo -e "${RED}Installation aborted.${NC}"
            exit 1
            ;;
    esac
}

# Install core dependencies first
echo "  Installing core dependencies..."
if [ "$PKG_MANAGER" = "uv" ]; then
    uv pip install --system rich aiohttp 2>/dev/null || \
    uv pip install rich aiohttp 2>/dev/null || \
    install_core_deps
else
    install_core_deps
fi

# Verify dependencies after installation
echo "  Verifying dependencies..."
verify_and_retry_install "rich" "terminal UI"
verify_and_retry_install "aiohttp" "web server"

# Tokenizer selection
echo ""
echo -e "${CYAN}Token counting options:${NC}"
echo "   1) transformers (recommended, ~95% accuracy for Claude)"
echo "   2) tiktoken (legacy, ~70-85% accuracy)"
echo "   3) skip (use character estimation)"
echo ""

if [ "$NON_INTERACTIVE" = true ]; then
    tokenizer_choice=1
    echo "  Non-interactive mode: selecting option 1 (transformers)"
else
    read -p "  Install tokenizer? [1/2/3] (default: 1): " tokenizer_choice
fi
tokenizer_choice=${tokenizer_choice:-1}

case $tokenizer_choice in
    1)
        echo "  Installing HuggingFace transformers..."
        if [ "$PKG_MANAGER" = "uv" ]; then
            uv pip install --system transformers tokenizers 2>/dev/null || \
            uv pip install transformers tokenizers 2>/dev/null || \
            install_tokenizer "transformers"
        else
            install_tokenizer "transformers"
        fi
        echo -e "  ${GREEN}[OK]${NC} transformers + tokenizers (Claude tokenizer)"
        ;;
    2)
        echo "  Installing tiktoken..."
        if [ "$PKG_MANAGER" = "uv" ]; then
            uv pip install --system tiktoken 2>/dev/null || \
            uv pip install tiktoken 2>/dev/null || \
            install_tokenizer "tiktoken"
        else
            install_tokenizer "tiktoken"
        fi
        echo -e "  ${GREEN}[OK]${NC} tiktoken (legacy tokenizer)"
        ;;
    *)
        echo -e "  ${YELLOW}[SKIP]${NC} Tokenizer installation skipped"
        echo "         Using character estimation (~60-70% accuracy)"
        ;;
esac

# =============================================================================
# UPDATE PATH
# =============================================================================
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo -e "
${YELLOW}[PATH]${NC} Adding $BIN_DIR to PATH..."

    SHELL_RC=""
    if [ -n "$ZSH_VERSION" ] || [ -f "$HOME/.zshrc" ]; then
        SHELL_RC="$HOME/.zshrc"
    elif [ -n "$BASH_VERSION" ] || [ -f "$HOME/.bashrc" ]; then
        SHELL_RC="$HOME/.bashrc"
    fi

    if [ -n "$SHELL_RC" ]; then
        if ! grep -q "Agent Dashboard" "$SHELL_RC" 2>/dev/null; then
            echo "" >> "$SHELL_RC"
            echo "# Agent Dashboard v2.6.0" >> "$SHELL_RC"
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
        fi
        
        # Verify PATH was added
        if grep -q "Agent Dashboard" "$SHELL_RC" 2>/dev/null; then
            echo -e "  ${GREEN}[OK]${NC} Added to $SHELL_RC"
            update_status "path_update" "success"
        else
            show_error "$SEVERITY_WARNING" "E007"                 "Could not verify PATH update in $SHELL_RC"                 "Add manually: export PATH=\"\$HOME/.local/bin:\$PATH\""
            update_status "path_update" "warning"
        fi
        
        echo ""
        echo -e "  ${CYAN}[ACTION REQUIRED]${NC} Run one of these to activate:"
        echo -e "    ${GREEN}source $SHELL_RC${NC}  (current terminal)"
        echo -e "    Or open a new terminal"
    fi
fi

# =============================================================================
# CONFIGURE CLAUDE CODE HOOKS
# =============================================================================
echo -e "
${BLUE}Configure Claude Code hooks?${NC}"
echo ""
echo "  This will update ~/.claude/settings.json to send events to the dashboard."
echo "  Events: PreToolUse, PostToolUse, UserPromptSubmit, Stop, SubagentStop"
echo ""

if [ "$NON_INTERACTIVE" = true ]; then
    REPLY="y"
    echo "  Non-interactive mode: proceeding with hook configuration"
else
    read -p "  Proceed with hook configuration? [y/N] " -n 1 -r
    echo ""
fi

if [[ $REPLY =~ ^[Yy]$ ]]; then
    SETTINGS_FILE="$CONFIG_DIR/settings.json"

    # Backup existing settings
    if [ -f "$SETTINGS_FILE" ]; then
        BACKUP_FILE="$SETTINGS_FILE.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$SETTINGS_FILE" "$BACKUP_FILE"
        echo -e "  ${GREEN}[OK]${NC} Backed up to $BACKUP_FILE"
    fi

    # Dashboard hooks to add
    DASHBOARD_HOOKS='{
  "hooks": {
    "PreToolUse": [{"matcher": ".*", "hooks": [{"type": "command", "command": "bash \"$HOME/.claude/dashboard/hooks/run_hook.sh\" --event-type PreToolUse --agent-name ${AGENT_NAME:-claude} --model ${AGENT_MODEL:-sonnet}"}]}],
    "PostToolUse": [{"matcher": ".*", "hooks": [{"type": "command", "command": "bash \"$HOME/.claude/dashboard/hooks/run_hook.sh\" --event-type PostToolUse --agent-name ${AGENT_NAME:-claude} --model ${AGENT_MODEL:-sonnet}"}]}],
    "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "bash \"$HOME/.claude/dashboard/hooks/run_hook.sh\" --event-type UserPromptSubmit --agent-name ${AGENT_NAME:-claude}"}]}],
    "Stop": [{"hooks": [{"type": "command", "command": "bash \"$HOME/.claude/dashboard/hooks/run_hook.sh\" --event-type Stop --agent-name ${AGENT_NAME:-claude}"}]}],
    "SubagentStop": [{"hooks": [{"type": "command", "command": "bash \"$HOME/.claude/dashboard/hooks/run_hook.sh\" --event-type SubagentStop --agent-name ${AGENT_NAME:-claude}"}]}]
  }
}'

    # Merge hooks into existing settings (preserves other settings)
    if [ -f "$SETTINGS_FILE" ]; then
        $PYTHON_CMD << MERGE_SCRIPT
import json
import sys

# Read existing settings
try:
    with open("$SETTINGS_FILE", "r") as f:
        existing = json.load(f)
except (json.JSONDecodeError, FileNotFoundError):
    existing = {}

# Parse new hooks
new_hooks = json.loads('"'"'$DASHBOARD_HOOKS'"'"')

# Merge hooks - add dashboard hooks without removing existing ones
if "hooks" not in existing:
    existing["hooks"] = {}

for hook_type, hook_list in new_hooks.get("hooks", {}).items():
    if hook_type not in existing["hooks"]:
        existing["hooks"][hook_type] = hook_list
    else:
        # Check if dashboard hook already exists
        existing_commands = [h.get("hooks", [{}])[0].get("command", "") for h in existing["hooks"][hook_type] if isinstance(h, dict)]
        for new_hook in hook_list:
            new_cmd = new_hook.get("hooks", [{}])[0].get("command", "")
            if "run_hook.sh" not in str(existing_commands):
                existing["hooks"][hook_type].append(new_hook)

# Write merged settings
with open("$SETTINGS_FILE", "w") as f:
    json.dump(existing, f, indent=2)

print("Merged dashboard hooks into existing settings")
MERGE_SCRIPT
        echo -e "  ${GREEN}[OK]${NC} Merged hooks into existing $SETTINGS_FILE"
    else
        # Create new settings file
        echo "$DASHBOARD_HOOKS" | $PYTHON_CMD -c "import sys,json; print(json.dumps(json.load(sys.stdin), indent=2))" > "$SETTINGS_FILE"
        echo -e "  ${GREEN}[OK]${NC} Created $SETTINGS_FILE with dashboard hooks"
    fi
else
    echo -e "  ${YELLOW}[SKIP]${NC} Hook configuration skipped"
fi

# =============================================================================
# INSTALLATION HEALTH CHECK
# =============================================================================
show_health_check() {
    echo ""
    echo -e "${CYAN}=============================================================================${NC}"
    echo -e "${CYAN}                    Installation Health Check                                ${NC}"
    echo -e "${CYAN}=============================================================================${NC}"
    echo ""
    
    local has_failures=false
    
    # Check CLI Launcher
    printf "  %-25s" "CLI Launcher:"
    if [ -x "$BIN_DIR/agent-dashboard" ]; then
        echo -e "${GREEN}[OK]${NC}"
    elif [ -f "$BIN_DIR/agent-dashboard" ]; then
        echo -e "${YELLOW}[WARN]${NC} Exists but not executable"
        has_failures=true
    else
        echo -e "${RED}[FAIL]${NC} Not found"
        has_failures=true
    fi
    
    # Check Python dependencies
    for pkg in rich aiohttp; do
        printf "  %-25s" "Python ($pkg):"
        if verify_python_import "$pkg" 2>/dev/null; then
            echo -e "${GREEN}[OK]${NC}"
        else
            echo -e "${RED}[FAIL]${NC} Not importable"
            has_failures=true
        fi
    done
    
    # Check PATH
    printf "  %-25s" "PATH configured:"
    if [[ ":$PATH:" == *":$BIN_DIR:"* ]] || grep -q ".local/bin" "$HOME/.bashrc" 2>/dev/null || grep -q ".local/bin" "$HOME/.zshrc" 2>/dev/null; then
        echo -e "${GREEN}[OK]${NC}"
    else
        echo -e "${YELLOW}[WARN]${NC} May need shell restart"
    fi
    
    # Check agents
    printf "  %-25s" "Agent definitions:"
    local agent_count=$(ls -1 "$AGENTS_DIR"/*.md 2>/dev/null | wc -l)
    if [ "$agent_count" -ge 10 ]; then
        echo -e "${GREEN}[OK]${NC} ($agent_count agents)"
    else
        echo -e "${YELLOW}[WARN]${NC} Only $agent_count agents found"
    fi
    
    echo ""
    
    if [ "$has_failures" = true ]; then
        echo -e "  ${YELLOW}Some issues detected. Run:${NC} ${GREEN}agent-dashboard doctor${NC}"
    fi
    
    echo -e "  ${CYAN}Install log:${NC} $INSTALL_LOG"
    echo ""
}

# Call health check before final banner
show_health_check

# =============================================================================
# INSTALLATION COMPLETE
# =============================================================================
echo ""
echo -e "${GREEN}=============================================================================${NC}"
echo -e "${GREEN}                    Installation Complete!                                   ${NC}"
echo -e "${GREEN}=============================================================================${NC}"
echo ""

# Platform-specific notes
if [ "$IS_WINDOWS" = true ]; then
    echo -e "${YELLOW}WINDOWS NOTE:${NC}"
    echo "  Windows Firewall may prompt when starting the dashboard."
    echo "  Click 'Allow access' to enable network connections."
    echo ""
fi

if [ "$IS_MACOS" = true ]; then
    echo -e "${CYAN}macOS NOTE:${NC}"
    echo "  If you see 'cannot be opened because the developer cannot be verified':"
    echo "    Right-click the script -> Open -> Open"
    echo "  Or run: xattr -d com.apple.quarantine scripts/install.sh"
    echo ""
fi

if [ "$IS_HEADLESS" = true ]; then
    echo -e "${CYAN}HEADLESS SERVER:${NC}"
    echo "  To access the web dashboard from your local machine:"
    echo ""
    echo "  1. On your local machine, create SSH tunnel:"
    echo "     ssh -L 4200:localhost:4200 user@your-server"
    echo ""
    echo "  2. Start dashboard on server:"
    echo "     agent-dashboard --web"
    echo ""
    echo "  3. Open in local browser:"
    echo "     http://localhost:4200"
    echo ""
fi

echo -e "${CYAN}QUICK START${NC}"
echo -e "${CYAN}===========${NC}"
echo ""
echo "  1. Start the dashboard:"
echo -e "     ${GREEN}agent-dashboard --web${NC}"
echo ""
echo "  2. Open in browser:"
echo -e "     ${GREEN}http://localhost:4200${NC}"
echo ""
echo "  3. Use with an agent:"
echo -e "     ${GREEN}export AGENT_NAME=orchestrator${NC}"
echo -e "     ${GREEN}export AGENT_MODEL=opus${NC}"
echo -e "     ${GREEN}claude${NC}"
echo ""
echo -e "${CYAN}AVAILABLE COMMANDS${NC}"
echo -e "${CYAN}==================${NC}"
echo ""
echo "  agent-dashboard --web     # Web dashboard"
echo "  agent-dashboard           # Terminal TUI"
echo "  agent-dashboard doctor    # Diagnose issues"
echo "  agent-dashboard test      # Send test event"
echo "  agent-dashboard status    # Check status"
echo ""
echo -e "${CYAN}SLASH COMMANDS${NC}"
echo -e "${CYAN}==============${NC}"
echo ""
echo "  /project [description]    # Start structured project workflow"
echo "  /enhance [request]        # Enhance prompt before execution"
echo ""
echo -e "${YELLOW}NOTE:${NC} Open a new terminal or run:"
echo -e "      ${GREEN}source ~/.bashrc${NC}  (Bash) or ${GREEN}source ~/.zshrc${NC}  (Zsh)"
echo ""

log_message "=== Installation completed ==="
