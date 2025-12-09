#!/usr/bin/env bash
#
# install.sh - Agent Dashboard v2.0 Installation Script
#
# Installs the Agent Dashboard and 11-agent framework for Claude Code.
#
# Usage:
#   ./install.sh
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="$HOME/.claude/dashboard"
AGENTS_DIR="$HOME/.claude/agents"
CONFIG_DIR="$HOME/.claude"
BIN_DIR="$HOME/.local/bin"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${MAGENTA}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║           🤖 Agent Dashboard v2.0 Installer                   ║"
echo "║     Multi-Agent Framework with Tiered Model Architecture      ║"
echo "╠═══════════════════════════════════════════════════════════════╣"
echo "║  Tier 1 (Opus):   orchestrator, synthesis, critic             ║"
echo "║  Tier 2 (Sonnet): researcher, perplexity, judge, auditor      ║"
echo "║  Tier 3 (Haiku):  web-search, summarizer, test-writer, etc    ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check dependencies
echo -e "${BLUE}Checking dependencies...${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is required but not installed.${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "  ${GREEN}✓${NC} Python $PYTHON_VERSION"

# Check Python version >= 3.9
PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]); then
    echo -e "${RED}Error: Python 3.9+ required, found $PYTHON_VERSION${NC}"
    exit 1
fi

# Check uv (preferred) or pip
if command -v uv &> /dev/null; then
    PKG_MANAGER="uv"
    echo -e "  ${GREEN}✓${NC} uv (Astral)"
elif command -v pip3 &> /dev/null; then
    PKG_MANAGER="pip"
    echo -e "  ${YELLOW}!${NC} pip3 (recommend installing uv: curl -LsSf https://astral.sh/uv/install.sh | sh)"
else
    echo -e "${RED}Error: Neither uv nor pip found.${NC}"
    exit 1
fi

# Check Claude Code
if command -v claude &> /dev/null; then
    echo -e "  ${GREEN}✓${NC} Claude Code CLI"
else
    echo -e "  ${YELLOW}!${NC} Claude Code CLI not found (install from anthropic.com/claude-code)"
fi

# Create directories
echo -e "\n${BLUE}Creating directories...${NC}"
mkdir -p "$INSTALL_DIR/hooks"
mkdir -p "$AGENTS_DIR"
mkdir -p "$BIN_DIR"
echo -e "  ${GREEN}✓${NC} $INSTALL_DIR"
echo -e "  ${GREEN}✓${NC} $AGENTS_DIR"
echo -e "  ${GREEN}✓${NC} $BIN_DIR"

# Copy dashboard files
echo -e "\n${BLUE}Installing dashboard files...${NC}"
cp "$SCRIPT_DIR/dashboard/agent_monitor.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/src/web_server.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/src/cli.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/hooks/send_event.py" "$INSTALL_DIR/hooks/"
echo -e "  ${GREEN}✓${NC} Dashboard files installed"

# Copy agent definitions
echo -e "\n${BLUE}Installing agent definitions...${NC}"
AGENT_COUNT=0
for agent_file in "$SCRIPT_DIR/agents/"*.md; do
    if [ -f "$agent_file" ]; then
        cp "$agent_file" "$AGENTS_DIR/"
        agent_name=$(basename "$agent_file" .md)
        AGENT_COUNT=$((AGENT_COUNT + 1))
    fi
done
echo -e "  ${GREEN}✓${NC} Installed $AGENT_COUNT agents"

# List agents by tier
echo -e "\n${CYAN}Agents installed:${NC}"
echo -e "  ${MAGENTA}Tier 1 (Opus):${NC}"
echo -e "    ◆ orchestrator - Strategic coordinator"
echo -e "    ◆ synthesis - Research synthesizer"
echo -e "    ◆ critic - Devil's advocate"
echo -e "  ${BLUE}Tier 2 (Sonnet):${NC}"
echo -e "    ● researcher - Documentation research"
echo -e "    ● perplexity-researcher - Real-time search"
echo -e "    ● research-judge - Quality evaluation"
echo -e "    ● claude-md-auditor - Doc auditing"
echo -e "  ${CYAN}Tier 3 (Haiku):${NC}"
echo -e "    ○ web-search-researcher - Web searches"
echo -e "    ○ summarizer - Compression"
echo -e "    ○ test-writer - Test generation"
echo -e "    ○ installer - Setup tasks"

# Create launcher script
echo -e "\n${BLUE}Creating launcher script...${NC}"
cat > "$BIN_DIR/agent-dashboard" << 'EOF'
#!/usr/bin/env bash
#
# agent-dashboard - Launch the Agent Dashboard v2.0
#

DASHBOARD_DIR="$HOME/.claude/dashboard"

# Parse arguments
WEB_MODE=false
PORT=4200

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
        status)
            python3 "$DASHBOARD_DIR/cli.py" status
            exit 0
            ;;
        test)
            python3 "$DASHBOARD_DIR/cli.py" test "${@:2}"
            exit 0
            ;;
        --help|-h)
            echo "Agent Dashboard v2.0 - Multi-Agent Workflow Monitor"
            echo ""
            echo "Usage: agent-dashboard [OPTIONS] [COMMAND]"
            echo ""
            echo "Options:"
            echo "  --web, -w     Launch web dashboard (default: terminal TUI)"
            echo "  --port, -p    Server port (default: 4200)"
            echo "  --help, -h    Show this help"
            echo ""
            echo "Commands:"
            echo "  status        Show system status"
            echo "  test          Send a test event"
            echo ""
            echo "Examples:"
            echo "  agent-dashboard              # Terminal TUI"
            echo "  agent-dashboard --web        # Web dashboard"
            echo "  agent-dashboard status       # Check status"
            exit 0
            ;;
        *)
            shift
            ;;
    esac
done

# Check dependencies
if ! python3 -c "import rich" 2>/dev/null; then
    echo "Installing rich..."
    pip3 install --quiet rich
fi

if ! python3 -c "import tiktoken" 2>/dev/null; then
    echo "Installing tiktoken..."
    pip3 install --quiet tiktoken
fi

if $WEB_MODE; then
    if ! python3 -c "import aiohttp" 2>/dev/null; then
        echo "Installing aiohttp..."
        pip3 install --quiet aiohttp
    fi
fi

# Launch dashboard
if $WEB_MODE; then
    echo "🌐 Starting web dashboard on port $PORT..."
    echo "   Open http://localhost:$PORT in your browser"
    echo ""
    python3 "$DASHBOARD_DIR/web_server.py" --port "$PORT"
else
    python3 "$DASHBOARD_DIR/agent_monitor.py" --port "$PORT"
fi
EOF

chmod +x "$BIN_DIR/agent-dashboard"
echo -e "  ${GREEN}✓${NC} Created $BIN_DIR/agent-dashboard"

# Install Python dependencies
echo -e "\n${BLUE}Installing Python dependencies...${NC}"
if [ "$PKG_MANAGER" = "uv" ]; then
    uv pip install --system rich aiohttp tiktoken 2>/dev/null || \
    uv pip install rich aiohttp tiktoken 2>/dev/null || \
    pip3 install --user rich aiohttp tiktoken
else
    pip3 install --user rich aiohttp tiktoken
fi
echo -e "  ${GREEN}✓${NC} Dependencies installed (rich, aiohttp, tiktoken)"

# Update PATH if needed
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo -e "\n${YELLOW}Adding $BIN_DIR to PATH...${NC}"
    
    SHELL_RC=""
    if [ -n "$ZSH_VERSION" ] || [ -f "$HOME/.zshrc" ]; then
        SHELL_RC="$HOME/.zshrc"
    elif [ -n "$BASH_VERSION" ] || [ -f "$HOME/.bashrc" ]; then
        SHELL_RC="$HOME/.bashrc"
    fi
    
    if [ -n "$SHELL_RC" ]; then
        if ! grep -q "Agent Dashboard" "$SHELL_RC" 2>/dev/null; then
            echo "" >> "$SHELL_RC"
            echo "# Agent Dashboard" >> "$SHELL_RC"
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
            echo -e "  ${GREEN}✓${NC} Added to $SHELL_RC"
        fi
    fi
fi

# Configure hooks (optional - ask user)
echo -e "\n${BLUE}Configure Claude Code hooks?${NC}"
echo -e "This will update ~/.claude/settings.json to send events to the dashboard."
read -p "Proceed? [y/N] " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    SETTINGS_FILE="$CONFIG_DIR/settings.json"
    
    # Backup existing settings
    if [ -f "$SETTINGS_FILE" ]; then
        cp "$SETTINGS_FILE" "$SETTINGS_FILE.backup"
        echo -e "  ${GREEN}✓${NC} Backed up existing settings"
    fi
    
    # Create new settings with hooks
    cat > "$SETTINGS_FILE" << 'EOF'
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
EOF
    echo -e "  ${GREEN}✓${NC} Configured hooks in $SETTINGS_FILE"
else
    echo -e "  ${YELLOW}!${NC} Skipped hook configuration"
    echo -e "      See docs/IMPLEMENTATION.md for manual setup"
fi

# Print success message
echo -e "\n${GREEN}╔═══════════════════════════════════════════════════════════════╗"
echo "║               ✅ Installation Complete!                        ║"
echo "╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Quick Start:${NC}"
echo ""
echo -e "  1. ${YELLOW}Start the dashboard:${NC}"
echo -e "     ${GREEN}agent-dashboard --web${NC}"
echo ""
echo -e "  2. ${YELLOW}Use an agent:${NC}"
echo -e "     ${GREEN}export AGENT_NAME=orchestrator AGENT_MODEL=opus${NC}"
echo -e "     ${GREEN}claude${NC}"
echo ""
echo -e "  3. ${YELLOW}Open the dashboard:${NC}"
echo -e "     ${GREEN}http://localhost:4200${NC}"
echo ""
echo -e "${CYAN}Available agents:${NC}"
echo -e "  ${MAGENTA}◆ Opus:${NC}   orchestrator, synthesis, critic"
echo -e "  ${BLUE}● Sonnet:${NC} researcher, perplexity-researcher, research-judge, claude-md-auditor"
echo -e "  ${CYAN}○ Haiku:${NC}  web-search-researcher, summarizer, test-writer, installer"
echo ""
echo -e "${YELLOW}Note:${NC} You may need to run ${GREEN}source ~/.bashrc${NC} or ${GREEN}source ~/.zshrc${NC}"
echo -e "      or open a new terminal for PATH changes to take effect."
echo ""
