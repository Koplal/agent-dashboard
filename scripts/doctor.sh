#!/usr/bin/env bash
# =============================================================================
# doctor.sh - Agent Dashboard Diagnostic Tool
# =============================================================================
# Checks the installation and identifies common issues.
#
# Usage:
#   ./scripts/doctor.sh
#   agent-dashboard doctor
#
# =============================================================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "=============================================="
echo "      Agent Dashboard Doctor                 "
echo "=============================================="
echo -e "${NC}"

ISSUES=0
WARNINGS=0

# -----------------------------------------------------------------------------
# Check 1: Python
# -----------------------------------------------------------------------------
echo -e "${CYAN}[1/9] Python${NC}"

# Find Python using the same logic as installer
PYTHON_CMD=""
for cmd in python3 python python3.11 python3.10 python3.9; do
    if command -v "$cmd" &> /dev/null; then
        version=$("$cmd" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null)
        major=$("$cmd" -c 'import sys; print(sys.version_info.major)' 2>/dev/null)
        minor=$("$cmd" -c 'import sys; print(sys.version_info.minor)' 2>/dev/null)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 9 ]; then
            PYTHON_CMD="$cmd"
            break
        fi
    fi
done

if [ -n "$PYTHON_CMD" ]; then
    version=$($PYTHON_CMD --version 2>&1)
    echo -e "  ${GREEN}[OK]${NC} $version (command: $PYTHON_CMD)"
else
    echo -e "  ${RED}[FAIL]${NC} Python 3.9+ not found"
    echo "        Install from https://python.org"
    ISSUES=$((ISSUES + 1))
fi

# -----------------------------------------------------------------------------
# Check 2: Dependencies
# -----------------------------------------------------------------------------
echo -e "\n${CYAN}[2/9] Python Dependencies${NC}"

if [ -n "$PYTHON_CMD" ]; then
    for pkg in rich aiohttp; do
        if $PYTHON_CMD -c "import $pkg" 2>/dev/null; then
            version=$($PYTHON_CMD -c "import $pkg; print(getattr($pkg, '__version__', 'installed'))" 2>/dev/null)
            echo -e "  ${GREEN}[OK]${NC} $pkg ($version)"
        else
            echo -e "  ${RED}[FAIL]${NC} $pkg not installed"
            echo "        Fix: $PYTHON_CMD -m pip install $pkg"
            ISSUES=$((ISSUES + 1))
        fi
    done

    # Check tokenizers (in order of preference)
    echo ""
    echo -e "  ${CYAN}Token Counting:${NC}"
    if $PYTHON_CMD -c "from transformers import GPT2TokenizerFast" 2>/dev/null; then
        echo -e "  ${GREEN}[OK]${NC} transformers (Claude tokenizer, ~95% accuracy)"
    elif $PYTHON_CMD -c "import tiktoken" 2>/dev/null; then
        echo -e "  ${YELLOW}[WARN]${NC} tiktoken only (legacy, ~70-85% accuracy)"
        echo "        Consider: pip install transformers tokenizers"
        WARNINGS=$((WARNINGS + 1))
    else
        echo -e "  ${YELLOW}[WARN]${NC} No tokenizer installed (using character estimation)"
        echo "        Run: pip install transformers tokenizers"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo -e "  ${YELLOW}[SKIP]${NC} Cannot check (Python not found)"
fi

# -----------------------------------------------------------------------------
# Check 3: Installation Directories
# -----------------------------------------------------------------------------
echo -e "\n${CYAN}[3/9] Installation${NC}"

DASHBOARD_DIR="$HOME/.claude/dashboard"
AGENTS_DIR="$HOME/.claude/agents"
BIN_FILE="$HOME/.local/bin/agent-dashboard"

if [ -d "$DASHBOARD_DIR" ]; then
    file_count=$(find "$DASHBOARD_DIR" -name "*.py" 2>/dev/null | wc -l)
    echo -e "  ${GREEN}[OK]${NC} Dashboard directory ($file_count Python files)"
else
    echo -e "  ${RED}[FAIL]${NC} Dashboard directory not found: $DASHBOARD_DIR"
    ISSUES=$((ISSUES + 1))
fi

if [ -d "$AGENTS_DIR" ]; then
    agent_count=$(ls -1 "$AGENTS_DIR"/*.md 2>/dev/null | wc -l)
    if [ "$agent_count" -ge 14 ]; then
        echo -e "  ${GREEN}[OK]${NC} Agents directory ($agent_count agents)"
    else
        echo -e "  ${YELLOW}[WARN]${NC} Agents directory ($agent_count/14 agents)"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo -e "  ${RED}[FAIL]${NC} Agents directory not found: $AGENTS_DIR"
    ISSUES=$((ISSUES + 1))
fi

if [ -x "$BIN_FILE" ]; then
    echo -e "  ${GREEN}[OK]${NC} CLI command installed"
else
    echo -e "  ${RED}[FAIL]${NC} CLI command not found: $BIN_FILE"
    ISSUES=$((ISSUES + 1))
fi

# -----------------------------------------------------------------------------
# Check 4: PATH
# -----------------------------------------------------------------------------
echo -e "\n${CYAN}[4/9] PATH Configuration${NC}"

if command -v agent-dashboard &> /dev/null; then
    echo -e "  ${GREEN}[OK]${NC} agent-dashboard in PATH"
else
    if [ -x "$BIN_FILE" ]; then
        echo -e "  ${YELLOW}[WARN]${NC} agent-dashboard not in PATH"
        echo "        Fix: Add to ~/.bashrc or ~/.zshrc:"
        echo "             export PATH=\"\$HOME/.local/bin:\$PATH\""
        WARNINGS=$((WARNINGS + 1))
    else
        echo -e "  ${RED}[FAIL]${NC} agent-dashboard not installed"
        ISSUES=$((ISSUES + 1))
    fi
fi

# -----------------------------------------------------------------------------
# Check 5: Claude Code CLI
# -----------------------------------------------------------------------------
echo -e "\n${CYAN}[5/9] Claude Code CLI${NC}"

if command -v claude &> /dev/null; then
    echo -e "  ${GREEN}[OK]${NC} Claude Code CLI installed"
else
    echo -e "  ${YELLOW}[INFO]${NC} Claude Code CLI not found (optional)"
    echo "        Install from: https://docs.anthropic.com/claude-code"
fi

# -----------------------------------------------------------------------------
# Check 6: Hooks Configuration
# -----------------------------------------------------------------------------
echo -e "\n${CYAN}[6/9] Hooks Configuration${NC}"

SETTINGS_FILE="$HOME/.claude/settings.json"
if [ -f "$SETTINGS_FILE" ]; then
    if grep -q "run_hook.sh\|send_event.py" "$SETTINGS_FILE" 2>/dev/null; then
        echo -e "  ${GREEN}[OK]${NC} Hooks configured in settings.json"
    else
        echo -e "  ${YELLOW}[WARN]${NC} settings.json exists but hooks not configured"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo -e "  ${YELLOW}[INFO]${NC} settings.json not found (hooks not configured)"
fi

# -----------------------------------------------------------------------------
# Check 7: Port 4200
# -----------------------------------------------------------------------------
echo -e "\n${CYAN}[7/9] Dashboard Server${NC}"

if command -v curl &> /dev/null; then
    if curl -sf http://localhost:4200/health > /dev/null 2>&1; then
        echo -e "  ${GREEN}[OK]${NC} Dashboard is running on port 4200"
    else
        echo -e "  ${CYAN}[INFO]${NC} Dashboard not running"
        echo "        Start with: agent-dashboard --web"
    fi
elif command -v nc &> /dev/null; then
    if nc -z localhost 4200 2>/dev/null; then
        echo -e "  ${GREEN}[OK]${NC} Port 4200 is in use (dashboard likely running)"
    else
        echo -e "  ${CYAN}[INFO]${NC} Port 4200 is available"
    fi
else
    echo -e "  ${YELLOW}[SKIP]${NC} Cannot check (curl/nc not available)"
fi

# -----------------------------------------------------------------------------
# Check 8: Database
# -----------------------------------------------------------------------------
echo -e "\n${CYAN}[8/9] Database${NC}"

DB_FILE="$HOME/.claude/agent_dashboard.db"
if [ -f "$DB_FILE" ]; then
    size=$(du -h "$DB_FILE" 2>/dev/null | cut -f1)
    echo -e "  ${GREEN}[OK]${NC} Database exists ($size)"
else
    echo -e "  ${CYAN}[INFO]${NC} No database yet (created on first event)"
fi

# -----------------------------------------------------------------------------
# Check 9: Tokenizer Status
# -----------------------------------------------------------------------------
echo -e "\n${CYAN}[9/9] Tokenizer${NC}"

if [ -n "$PYTHON_CMD" ]; then
    if $PYTHON_CMD -c "from transformers import GPT2TokenizerFast; GPT2TokenizerFast.from_pretrained('Xenova/claude-tokenizer')" 2>/dev/null; then
        echo -e "  ${GREEN}[OK]${NC} Claude tokenizer (HuggingFace): Available (~95% accuracy)"
    elif $PYTHON_CMD -c "import tiktoken" 2>/dev/null; then
        echo -e "  ${YELLOW}[WARN]${NC} tiktoken fallback: Available (~70-85% accuracy)"
        echo "        Consider installing transformers for better accuracy:"
        echo "        pip install transformers tokenizers"
        WARNINGS=$((WARNINGS + 1))
    else
        echo -e "  ${YELLOW}[WARN]${NC} No tokenizer installed (using character estimation)"
        echo "        Run: pip install transformers tokenizers"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo -e "  ${YELLOW}[SKIP]${NC} Cannot check (Python not found)"
fi

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
echo ""
echo "=============================================="
if [ $ISSUES -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}All checks passed!${NC}"
elif [ $ISSUES -eq 0 ]; then
    echo -e "${YELLOW}$WARNINGS warning(s), but installation is functional${NC}"
else
    echo -e "${RED}Found $ISSUES issue(s) and $WARNINGS warning(s)${NC}"
    echo ""
    echo "To fix issues, run:"
    echo "  ./scripts/install.sh"
fi
echo "=============================================="
echo ""

exit $ISSUES
