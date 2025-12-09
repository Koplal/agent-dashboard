#!/usr/bin/env bash
# =============================================================================
# install.sh - Agent Dashboard v2.1 Installation Script
# =============================================================================
#
# DESCRIPTION:
#   Automated installer for the Agent Dashboard multi-agent workflow framework.
#   Installs 14 specialized agents, dashboard components, and configures
#   Claude Code hooks for real-time monitoring.
#
# SUPPORTED TERMINALS:
#   - Bash (Linux, macOS, WSL) - Primary support
#   - Zsh (macOS default, Linux) - Full support
#   - Git Bash (Windows) - Full support
#   - WSL2 (Windows Subsystem for Linux) - Full support
#
# NOT SUPPORTED:
#   - PowerShell (Windows) - Use WSL2 or Git Bash instead
#   - CMD.exe (Windows) - Use WSL2 or Git Bash instead
#
# USAGE:
#   Terminal (Bash/Zsh):
#     chmod +x scripts/install.sh
#     ./scripts/install.sh
#
#   VS Code Integrated Terminal:
#     1. Open VS Code in the agent-dashboard directory
#     2. Open integrated terminal: Ctrl+` (backtick) or Cmd+` on macOS
#     3. Ensure terminal is set to Bash/Zsh (not PowerShell):
#        - Click the dropdown arrow next to the + icon in terminal
#        - Select "Git Bash" or "bash" or "zsh"
#     4. Run: ./scripts/install.sh
#
#   Windows (via WSL2):
#     wsl -d Ubuntu
#     cd /path/to/agent-dashboard
#     ./scripts/install.sh
#
# PREREQUISITES:
#   Required:
#     - Python 3.9 or higher
#     - pip3 or uv package manager
#
#   Optional but Recommended:
#     - Claude Code CLI (for agent integration)
#     - uv package manager (faster than pip)
#     - tmux (for background dashboard operation)
#
# WHAT THIS SCRIPT DOES:
#   1. Verifies Python 3.9+ is installed
#   2. Checks for uv or pip package manager
#   3. Creates directory structure:
#      - ~/.claude/dashboard/     (dashboard files)
#      - ~/.claude/dashboard/hooks/ (event hooks)
#      - ~/.claude/agents/        (agent definitions)
#      - ~/.local/bin/            (CLI launcher)
#   4. Copies dashboard Python modules
#   5. Installs 14 agent definition files (.md)
#   6. Creates 'agent-dashboard' CLI command
#   7. Installs Python dependencies (rich, aiohttp, tiktoken)
#   8. Optionally configures Claude Code hooks
#
# POST-INSTALLATION:
#   Start the dashboard:
#     agent-dashboard --web
#
#   Use with an agent:
#     export AGENT_NAME=orchestrator
#     export AGENT_MODEL=opus
#     claude
#
# TROUBLESHOOTING:
#   "command not found: agent-dashboard"
#     - Run: source ~/.bashrc  (or source ~/.zshrc)
#     - Or open a new terminal window
#
#   "Permission denied"
#     - Run: chmod +x scripts/install.sh
#
#   "Python not found"
#     - Install Python 3.9+: https://www.python.org/downloads/
#
# VERSION: 2.1.0
# UPDATED: 2025-01-09
# =============================================================================

# -----------------------------------------------------------------------------
# SHELL CONFIGURATION
# -----------------------------------------------------------------------------
# Exit immediately if any command fails (prevents partial installations)
set -e

# -----------------------------------------------------------------------------
# COLOR DEFINITIONS
# -----------------------------------------------------------------------------
# ANSI color codes for terminal output formatting
# These colors improve readability of installation progress
# Note: Colors may not display correctly in all terminals (e.g., basic CMD.exe)
RED='\033[0;31m'      # Errors
GREEN='\033[0;32m'    # Success messages
YELLOW='\033[1;33m'   # Warnings
BLUE='\033[0;34m'     # Section headers
CYAN='\033[0;36m'     # Information
MAGENTA='\033[0;35m'  # Tier 1 agents (Opus)
NC='\033[0m'          # No Color - reset to default

# -----------------------------------------------------------------------------
# DIRECTORY CONFIGURATION
# -----------------------------------------------------------------------------
# Define installation directories using $HOME for cross-platform compatibility
# These paths follow XDG Base Directory specification where applicable

# Primary dashboard installation directory
# Contains: agent_monitor.py, web_server.py, cli.py, workflow_engine.py
INSTALL_DIR="$HOME/.claude/dashboard"

# Agent definitions directory
# Contains: 14 agent .md files (orchestrator.md, researcher.md, etc.)
AGENTS_DIR="$HOME/.claude/agents"

# Claude Code configuration directory
# Contains: settings.json (hooks configuration)
CONFIG_DIR="$HOME/.claude"

# User binary directory for CLI command
# The 'agent-dashboard' command will be installed here
BIN_DIR="$HOME/.local/bin"

# Source directory (where this script is located)
# Uses BASH_SOURCE to handle symlinks correctly
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# -----------------------------------------------------------------------------
# INSTALLATION BANNER
# -----------------------------------------------------------------------------
# Display installation header with version and agent tier information
echo -e "${MAGENTA}"
echo "============================================================================="
echo "                    Agent Dashboard v2.1 Installer                           "
echo "            Multi-Agent Workflow Framework for Claude Code                   "
echo "============================================================================="
echo ""
echo "  Agent Tiers (14 agents total):"
echo "    Tier 1 (Opus):   orchestrator, synthesis, critic, planner"
echo "    Tier 2 (Sonnet): researcher, perplexity, judge, auditor, implementer"
echo "    Tier 3 (Haiku):  web-search, summarizer, test-writer, installer, validator"
echo ""
echo "============================================================================="
echo -e "${NC}"

# -----------------------------------------------------------------------------
# DEPENDENCY CHECKS
# -----------------------------------------------------------------------------
# Verify all required dependencies are installed before proceeding

echo -e "${BLUE}[1/7] Checking dependencies...${NC}"

# -----------------------------------------------------------------------------
# Check: Python Installation
# -----------------------------------------------------------------------------
# Python 3.9+ is required for:
#   - asyncio features used in web_server.py
#   - Type hints syntax used throughout codebase
#   - dataclasses used in workflow_engine.py
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}ERROR: Python 3 is required but not installed.${NC}"
    echo ""
    echo "Installation instructions:"
    echo "  macOS:   brew install python3"
    echo "  Ubuntu:  sudo apt install python3 python3-pip"
    echo "  Windows: Download from https://www.python.org/downloads/"
    echo ""
    exit 1
fi

# Get Python version for display and validation
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "  ${GREEN}[OK]${NC} Python $PYTHON_VERSION detected"

# -----------------------------------------------------------------------------
# Check: Python Version >= 3.9
# -----------------------------------------------------------------------------
# Validate Python version meets minimum requirements
# Python 3.9+ required for:
#   - dict union operator (|)
#   - Type hint improvements (list instead of List)
#   - asyncio.to_thread()
PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]); then
    echo -e "${RED}ERROR: Python 3.9+ required, found $PYTHON_VERSION${NC}"
    echo ""
    echo "Please upgrade Python:"
    echo "  macOS:   brew upgrade python3"
    echo "  Ubuntu:  sudo apt install python3.11"
    echo "  pyenv:   pyenv install 3.11 && pyenv global 3.11"
    echo ""
    exit 1
fi

# -----------------------------------------------------------------------------
# Check: Package Manager (uv or pip)
# -----------------------------------------------------------------------------
# Determine which package manager to use for installing dependencies
# uv is preferred (10-100x faster than pip) but pip works as fallback
if command -v uv &> /dev/null; then
    PKG_MANAGER="uv"
    echo -e "  ${GREEN}[OK]${NC} uv package manager detected (recommended)"
elif command -v pip3 &> /dev/null; then
    PKG_MANAGER="pip"
    echo -e "  ${YELLOW}[WARN]${NC} pip3 detected (uv recommended for faster installs)"
    echo -e "         Install uv: ${CYAN}curl -LsSf https://astral.sh/uv/install.sh | sh${NC}"
else
    echo -e "${RED}ERROR: No package manager found (uv or pip required).${NC}"
    echo ""
    echo "Installation instructions:"
    echo "  uv (recommended): curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "  pip:              Usually comes with Python"
    echo ""
    exit 1
fi

# -----------------------------------------------------------------------------
# Check: Claude Code CLI (Optional)
# -----------------------------------------------------------------------------
# Claude Code CLI is needed to use the agents but not required for installation
if command -v claude &> /dev/null; then
    CLAUDE_VERSION=$(claude --version 2>/dev/null || echo "unknown")
    echo -e "  ${GREEN}[OK]${NC} Claude Code CLI detected"
else
    echo -e "  ${YELLOW}[WARN]${NC} Claude Code CLI not found"
    echo -e "         Install from: ${CYAN}https://docs.anthropic.com/claude-code${NC}"
    echo -e "         (Required to use agents, but not for dashboard installation)"
fi

# -----------------------------------------------------------------------------
# CREATE DIRECTORY STRUCTURE
# -----------------------------------------------------------------------------
echo -e "\n${BLUE}[2/7] Creating directory structure...${NC}"

# Create all required directories with parent directories (-p flag)
# Directory structure:
#   ~/.claude/
#   ├── dashboard/
#   │   └── hooks/
#   ├── agents/
#   └── settings.json
mkdir -p "$INSTALL_DIR/hooks"
mkdir -p "$AGENTS_DIR"
mkdir -p "$BIN_DIR"

echo -e "  ${GREEN}[OK]${NC} $INSTALL_DIR"
echo -e "  ${GREEN}[OK]${NC} $INSTALL_DIR/hooks"
echo -e "  ${GREEN}[OK]${NC} $AGENTS_DIR"
echo -e "  ${GREEN}[OK]${NC} $BIN_DIR"

# -----------------------------------------------------------------------------
# INSTALL DASHBOARD FILES
# -----------------------------------------------------------------------------
echo -e "\n${BLUE}[3/7] Installing dashboard files...${NC}"

# Copy core Python modules to installation directory
# Each file serves a specific purpose in the dashboard system:

# agent_monitor.py - Terminal TUI dashboard using Rich library
# Provides: Real-time event timeline, session tracking, token visualization
cp "$SCRIPT_DIR/dashboard/agent_monitor.py" "$INSTALL_DIR/"
echo -e "  ${GREEN}[OK]${NC} agent_monitor.py (Terminal TUI dashboard)"

# web_server.py - Web dashboard server using aiohttp
# Provides: HTTP server, REST API, WebSocket updates, HTML dashboard
cp "$SCRIPT_DIR/src/web_server.py" "$INSTALL_DIR/"
echo -e "  ${GREEN}[OK]${NC} web_server.py (Web dashboard + REST API)"

# cli.py - Unified command-line interface
# Provides: Subcommands for web, terminal, test, status
cp "$SCRIPT_DIR/src/cli.py" "$INSTALL_DIR/"
echo -e "  ${GREEN}[OK]${NC} cli.py (CLI interface)"

# workflow_engine.py - Multi-agent orchestration engine
# Provides: Workflow phases, cost circuit breaker, validation stack
cp "$SCRIPT_DIR/src/workflow_engine.py" "$INSTALL_DIR/"
echo -e "  ${GREEN}[OK]${NC} workflow_engine.py (Workflow orchestration)"

# send_event.py - Event capture hook for Claude Code
# Provides: Token counting (tiktoken), cost estimation, event transmission
cp "$SCRIPT_DIR/hooks/send_event.py" "$INSTALL_DIR/hooks/"
echo -e "  ${GREEN}[OK]${NC} hooks/send_event.py (Event capture)"

# -----------------------------------------------------------------------------
# INSTALL AGENT DEFINITIONS
# -----------------------------------------------------------------------------
echo -e "\n${BLUE}[4/7] Installing agent definitions...${NC}"

# Copy all agent definition files (.md) to agents directory
# Each agent file contains:
#   - YAML frontmatter with name, description, model tier
#   - System prompt defining agent behavior
#   - Tool permissions and constraints
AGENT_COUNT=0
for agent_file in "$SCRIPT_DIR/agents/"*.md; do
    if [ -f "$agent_file" ]; then
        cp "$agent_file" "$AGENTS_DIR/"
        AGENT_COUNT=$((AGENT_COUNT + 1))
    fi
done
echo -e "  ${GREEN}[OK]${NC} Installed $AGENT_COUNT agent definitions"

# Display installed agents organized by tier
# Tier determines model (Opus/Sonnet/Haiku) and relative cost
echo ""
echo -e "  ${CYAN}Installed Agents by Tier:${NC}"
echo ""
echo -e "  ${MAGENTA}Tier 1 - Opus (Strategic/Quality) [\$\$\$]:${NC}"
echo -e "    [diamond] orchestrator    - Multi-agent workflow coordinator"
echo -e "    [diamond] synthesis       - Research output synthesizer"
echo -e "    [diamond] critic          - Quality assurance, devil's advocate"
echo -e "    [diamond] planner         - Strategic planner (PLAN MODE)"
echo ""
echo -e "  ${BLUE}Tier 2 - Sonnet (Analysis/Research) [\$\$]:${NC}"
echo -e "    [circle]  researcher          - Documentation-based research"
echo -e "    [circle]  perplexity-researcher - Real-time web search"
echo -e "    [circle]  research-judge      - Quality evaluation"
echo -e "    [circle]  claude-md-auditor   - Documentation auditing"
echo -e "    [circle]  implementer         - Code execution (IMPLEMENT MODE)"
echo ""
echo -e "  ${CYAN}Tier 3 - Haiku (Execution/Routine) [\$]:${NC}"
echo -e "    [ring]    web-search-researcher - Broad web searches"
echo -e "    [ring]    summarizer          - Output compression"
echo -e "    [ring]    test-writer         - Test generation"
echo -e "    [ring]    installer           - Setup and configuration"
echo -e "    [ring]    validator           - Four-layer validation (VALIDATE MODE)"

# -----------------------------------------------------------------------------
# CREATE CLI LAUNCHER SCRIPT
# -----------------------------------------------------------------------------
echo -e "\n${BLUE}[5/7] Creating CLI launcher script...${NC}"

# Create the 'agent-dashboard' command
# This script provides a user-friendly interface to launch the dashboard
# It handles argument parsing, dependency checking, and mode selection
cat > "$BIN_DIR/agent-dashboard" << 'LAUNCHER_EOF'
#!/usr/bin/env bash
# =============================================================================
# agent-dashboard - Launch the Agent Dashboard v2.1
# =============================================================================
#
# DESCRIPTION:
#   CLI launcher for the Agent Dashboard. Supports terminal TUI and web modes.
#
# USAGE:
#   agent-dashboard              # Launch terminal TUI dashboard
#   agent-dashboard --web        # Launch web dashboard (http://localhost:4200)
#   agent-dashboard --web -p 8080  # Launch on custom port
#   agent-dashboard status       # Show system status
#   agent-dashboard test         # Send a test event
#
# TERMINALS:
#   Works in: Bash, Zsh, Git Bash, WSL2
#   Does not work in: PowerShell, CMD.exe (use WSL2 instead)
#
# VS CODE USAGE:
#   1. Open integrated terminal (Ctrl+` or Cmd+`)
#   2. Ensure terminal type is Bash/Zsh (not PowerShell)
#   3. Run: agent-dashboard --web
#   4. Ctrl+Click the URL to open dashboard in browser
#
# =============================================================================

DASHBOARD_DIR="$HOME/.claude/dashboard"

# -----------------------------------------------------------------------------
# Argument Parsing
# -----------------------------------------------------------------------------
WEB_MODE=false
PORT=4200

while [[ $# -gt 0 ]]; do
    case $1 in
        --web|-w)
            # Web mode: Launch aiohttp server with HTML dashboard
            WEB_MODE=true
            shift
            ;;
        --port|-p)
            # Custom port for web server (default: 4200)
            PORT="$2"
            shift 2
            ;;
        status)
            # Display system status (running processes, database info)
            python3 "$DASHBOARD_DIR/cli.py" status
            exit 0
            ;;
        test)
            # Send a test event to verify connectivity
            python3 "$DASHBOARD_DIR/cli.py" test "${@:2}"
            exit 0
            ;;
        --help|-h)
            echo "Agent Dashboard v2.1 - Multi-Agent Workflow Monitor"
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
            echo "  status        Show system status"
            echo "  test          Send a test event to the dashboard"
            echo ""
            echo "EXAMPLES:"
            echo "  agent-dashboard              # Terminal TUI dashboard"
            echo "  agent-dashboard --web        # Web dashboard on port 4200"
            echo "  agent-dashboard --web -p 8080  # Web dashboard on port 8080"
            echo "  agent-dashboard status       # Check system status"
            echo "  agent-dashboard test         # Send test event"
            echo ""
            echo "TERMINAL SUPPORT:"
            echo "  Supported:     Bash, Zsh, Git Bash, WSL2"
            echo "  Not supported: PowerShell, CMD.exe"
            echo ""
            echo "VS CODE:"
            echo "  1. Open terminal with Ctrl+\` (backtick)"
            echo "  2. Select Bash/Zsh from terminal dropdown"
            echo "  3. Run: agent-dashboard --web"
            echo ""
            exit 0
            ;;
        *)
            # Unknown argument, skip
            shift
            ;;
    esac
done

# -----------------------------------------------------------------------------
# Dependency Check and Auto-Install
# -----------------------------------------------------------------------------
# Check and install required Python packages if missing

# rich - Required for terminal TUI dashboard
if ! python3 -c "import rich" 2>/dev/null; then
    echo "Installing rich (terminal UI library)..."
    pip3 install --quiet rich
fi

# tiktoken - Required for accurate token counting
# Falls back to character-based estimation if unavailable
if ! python3 -c "import tiktoken" 2>/dev/null; then
    echo "Installing tiktoken (token counting)..."
    pip3 install --quiet tiktoken
fi

# aiohttp - Required only for web mode
if $WEB_MODE; then
    if ! python3 -c "import aiohttp" 2>/dev/null; then
        echo "Installing aiohttp (web server)..."
        pip3 install --quiet aiohttp
    fi
fi

# -----------------------------------------------------------------------------
# Launch Dashboard
# -----------------------------------------------------------------------------
if $WEB_MODE; then
    echo ""
    echo "Starting Agent Dashboard v2.1 (Web Mode)"
    echo "==========================================="
    echo ""
    echo "  URL:  http://localhost:$PORT"
    echo ""
    echo "  Terminal: Open the URL above in your browser"
    echo "  VS Code:  Ctrl+Click (Cmd+Click on macOS) the URL"
    echo ""
    echo "  Press Ctrl+C to stop the server"
    echo ""
    python3 "$DASHBOARD_DIR/web_server.py" --port "$PORT"
else
    echo ""
    echo "Starting Agent Dashboard v2.1 (Terminal TUI Mode)"
    echo "==================================================="
    echo ""
    echo "  Press 'q' to quit"
    echo ""
    python3 "$DASHBOARD_DIR/agent_monitor.py" --port "$PORT"
fi
LAUNCHER_EOF

# Make the launcher executable
chmod +x "$BIN_DIR/agent-dashboard"
echo -e "  ${GREEN}[OK]${NC} Created $BIN_DIR/agent-dashboard"

# -----------------------------------------------------------------------------
# INSTALL PYTHON DEPENDENCIES
# -----------------------------------------------------------------------------
echo -e "\n${BLUE}[6/7] Installing Python dependencies...${NC}"

# Install required Python packages:
#   - rich: Terminal UI rendering (TUI dashboard)
#   - aiohttp: Async web server (web dashboard, WebSocket)
#   - tiktoken: Token counting using OpenAI's tiktoken (cost estimation)
echo -e "  Installing: rich, aiohttp, tiktoken"

if [ "$PKG_MANAGER" = "uv" ]; then
    # uv is 10-100x faster than pip
    # Try --system first (installs globally), fall back to user install
    uv pip install --system rich aiohttp tiktoken 2>/dev/null || \
    uv pip install rich aiohttp tiktoken 2>/dev/null || \
    pip3 install --user rich aiohttp tiktoken
else
    # Standard pip installation with --user flag (no sudo required)
    pip3 install --user rich aiohttp tiktoken
fi

echo -e "  ${GREEN}[OK]${NC} rich (terminal UI)"
echo -e "  ${GREEN}[OK]${NC} aiohttp (web server)"
echo -e "  ${GREEN}[OK]${NC} tiktoken (token counting)"

# -----------------------------------------------------------------------------
# UPDATE PATH (if needed)
# -----------------------------------------------------------------------------
# Ensure ~/.local/bin is in PATH so 'agent-dashboard' command works
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo -e "\n${YELLOW}[PATH]${NC} Adding $BIN_DIR to PATH..."

    # Detect shell configuration file
    SHELL_RC=""
    if [ -n "$ZSH_VERSION" ] || [ -f "$HOME/.zshrc" ]; then
        SHELL_RC="$HOME/.zshrc"
    elif [ -n "$BASH_VERSION" ] || [ -f "$HOME/.bashrc" ]; then
        SHELL_RC="$HOME/.bashrc"
    fi

    # Add PATH export to shell configuration
    if [ -n "$SHELL_RC" ]; then
        if ! grep -q "Agent Dashboard" "$SHELL_RC" 2>/dev/null; then
            echo "" >> "$SHELL_RC"
            echo "# Agent Dashboard v2.1 - Added by install.sh" >> "$SHELL_RC"
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
            echo -e "  ${GREEN}[OK]${NC} Added to $SHELL_RC"
            echo -e "  ${YELLOW}[NOTE]${NC} Run 'source $SHELL_RC' or open a new terminal"
        fi
    fi
fi

# -----------------------------------------------------------------------------
# CONFIGURE CLAUDE CODE HOOKS (Optional)
# -----------------------------------------------------------------------------
echo -e "\n${BLUE}[7/7] Configure Claude Code hooks?${NC}"
echo ""
echo "  This will update ~/.claude/settings.json to send events to the dashboard."
echo "  Events captured: PreToolUse, PostToolUse, UserPromptSubmit, Stop, SubagentStop"
echo ""
read -p "  Proceed with hook configuration? [y/N] " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    SETTINGS_FILE="$CONFIG_DIR/settings.json"

    # Backup existing settings if present
    if [ -f "$SETTINGS_FILE" ]; then
        BACKUP_FILE="$SETTINGS_FILE.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$SETTINGS_FILE" "$BACKUP_FILE"
        echo -e "  ${GREEN}[OK]${NC} Backed up existing settings to $BACKUP_FILE"
    fi

    # Create new settings.json with hook configuration
    # These hooks capture Claude Code events and send them to the dashboard
    cat > "$SETTINGS_FILE" << 'SETTINGS_EOF'
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/dashboard/hooks/send_event.py --event-type PreToolUse --agent-name ${AGENT_NAME:-claude} --model ${AGENT_MODEL:-sonnet}"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/dashboard/hooks/send_event.py --event-type PostToolUse --agent-name ${AGENT_NAME:-claude} --model ${AGENT_MODEL:-sonnet}"
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/dashboard/hooks/send_event.py --event-type UserPromptSubmit --agent-name ${AGENT_NAME:-claude}"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/dashboard/hooks/send_event.py --event-type Stop --agent-name ${AGENT_NAME:-claude}"
          }
        ]
      }
    ],
    "SubagentStop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/dashboard/hooks/send_event.py --event-type SubagentStop --agent-name ${AGENT_NAME:-claude}"
          }
        ]
      }
    ]
  }
}
SETTINGS_EOF
    echo -e "  ${GREEN}[OK]${NC} Configured hooks in $SETTINGS_FILE"
else
    echo -e "  ${YELLOW}[SKIP]${NC} Hook configuration skipped"
    echo -e "         See docs/IMPLEMENTATION.md for manual setup instructions"
fi

# =============================================================================
# INSTALLATION COMPLETE
# =============================================================================
echo ""
echo -e "${GREEN}=============================================================================${NC}"
echo -e "${GREEN}                    Installation Complete!                                   ${NC}"
echo -e "${GREEN}=============================================================================${NC}"
echo ""
echo -e "${CYAN}QUICK START${NC}"
echo -e "${CYAN}===========${NC}"
echo ""
echo "  1. Start the dashboard:"
echo ""
echo -e "     ${GREEN}agent-dashboard --web${NC}"
echo ""
echo "  2. Open in browser:"
echo ""
echo -e "     ${GREEN}http://localhost:4200${NC}"
echo ""
echo "  3. In a new terminal, use an agent:"
echo ""
echo -e "     ${GREEN}export AGENT_NAME=orchestrator${NC}"
echo -e "     ${GREEN}export AGENT_MODEL=opus${NC}"
echo -e "     ${GREEN}claude${NC}"
echo ""
echo -e "${CYAN}VS CODE INTEGRATION${NC}"
echo -e "${CYAN}===================${NC}"
echo ""
echo "  1. Open VS Code integrated terminal: Ctrl+\` (Cmd+\` on macOS)"
echo ""
echo "  2. Ensure terminal is Bash/Zsh (not PowerShell):"
echo "     Click dropdown arrow next to + in terminal panel"
echo "     Select 'Git Bash' or 'bash' or 'zsh'"
echo ""
echo "  3. Run the dashboard:"
echo -e "     ${GREEN}agent-dashboard --web${NC}"
echo ""
echo "  4. Ctrl+Click the URL to open in browser"
echo ""
echo "  5. Open another terminal (click +) for Claude:"
echo -e "     ${GREEN}export AGENT_NAME=orchestrator AGENT_MODEL=opus && claude${NC}"
echo ""
echo -e "${CYAN}AVAILABLE AGENTS (14 total)${NC}"
echo -e "${CYAN}============================${NC}"
echo ""
echo -e "  ${MAGENTA}Tier 1 - Opus (\$\$\$):${NC} orchestrator, synthesis, critic, planner"
echo -e "  ${BLUE}Tier 2 - Sonnet (\$\$):${NC} researcher, perplexity-researcher, research-judge,"
echo "                       claude-md-auditor, implementer"
echo -e "  ${CYAN}Tier 3 - Haiku (\$):${NC}  web-search-researcher, summarizer, test-writer,"
echo "                       installer, validator"
echo ""
echo -e "${CYAN}WORKFLOW MODES${NC}"
echo -e "${CYAN}==============${NC}"
echo ""
echo "  PLAN MODE      - Read-only exploration (planner agent)"
echo "  IMPLEMENT MODE - Execute approved plans (implementer agent)"
echo "  VALIDATE MODE  - Four-layer validation (validator agent)"
echo ""
echo -e "${CYAN}DOCUMENTATION${NC}"
echo -e "${CYAN}=============${NC}"
echo ""
echo "  README.md                  - Quick start guide"
echo "  docs/IMPLEMENTATION.md     - Detailed deployment guide"
echo "  docs/WORKFLOW_FRAMEWORK.md - Design patterns and governance"
echo ""
echo -e "${YELLOW}NOTE:${NC} You may need to run one of the following commands"
echo "      or open a new terminal for PATH changes to take effect:"
echo ""
echo -e "      ${GREEN}source ~/.bashrc${NC}   (Bash users)"
echo -e "      ${GREEN}source ~/.zshrc${NC}    (Zsh users)"
echo ""
