#!/usr/bin/env bash
# =============================================================================
# uninstall.sh - Agent Dashboard Uninstaller
# =============================================================================
# Safely removes all Agent Dashboard components from your system.
#
# Usage:
#   ./scripts/uninstall.sh
#   agent-dashboard uninstall
#
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "=============================================="
echo "      Agent Dashboard Uninstaller            "
echo "=============================================="
echo -e "${NC}"

# Directories and files to remove
DASHBOARD_DIR="$HOME/.claude/dashboard"
AGENTS_DIR="$HOME/.claude/agents"
LOGS_DIR="$HOME/.claude/logs"
BIN_FILE="$HOME/.local/bin/agent-dashboard"
DB_FILE="$HOME/.claude/agent_dashboard.db"
SETTINGS_FILE="$HOME/.claude/settings.json"

echo "This will remove the following:"
echo ""
echo "  Directories:"
[ -d "$DASHBOARD_DIR" ] && echo "    - $DASHBOARD_DIR"
[ -d "$AGENTS_DIR" ] && echo "    - $AGENTS_DIR"
[ -d "$LOGS_DIR" ] && echo "    - $LOGS_DIR"
echo ""
echo "  Files:"
[ -f "$BIN_FILE" ] && echo "    - $BIN_FILE"
[ -f "$DB_FILE" ] && echo "    - $DB_FILE"
echo ""

read -p "Proceed with uninstallation? [y/N] " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo -e "${CYAN}Removing files...${NC}"

# Remove dashboard directory
if [ -d "$DASHBOARD_DIR" ]; then
    rm -rf "$DASHBOARD_DIR"
    echo -e "  ${GREEN}[OK]${NC} Removed $DASHBOARD_DIR"
else
    echo -e "  ${YELLOW}[SKIP]${NC} $DASHBOARD_DIR (not found)"
fi

# Remove agents directory
if [ -d "$AGENTS_DIR" ]; then
    rm -rf "$AGENTS_DIR"
    echo -e "  ${GREEN}[OK]${NC} Removed $AGENTS_DIR"
else
    echo -e "  ${YELLOW}[SKIP]${NC} $AGENTS_DIR (not found)"
fi

# Remove logs directory
if [ -d "$LOGS_DIR" ]; then
    rm -rf "$LOGS_DIR"
    echo -e "  ${GREEN}[OK]${NC} Removed $LOGS_DIR"
else
    echo -e "  ${YELLOW}[SKIP]${NC} $LOGS_DIR (not found)"
fi

# Remove CLI command
if [ -f "$BIN_FILE" ]; then
    rm -f "$BIN_FILE"
    echo -e "  ${GREEN}[OK]${NC} Removed $BIN_FILE"
else
    echo -e "  ${YELLOW}[SKIP]${NC} $BIN_FILE (not found)"
fi

# Remove database
if [ -f "$DB_FILE" ]; then
    rm -f "$DB_FILE"
    echo -e "  ${GREEN}[OK]${NC} Removed $DB_FILE"
else
    echo -e "  ${YELLOW}[SKIP]${NC} $DB_FILE (not found)"
fi

# Ask about settings.json (contains hooks config that user might want to keep)
echo ""
if [ -f "$SETTINGS_FILE" ]; then
    echo "The settings.json file contains Claude Code hooks configuration."
    read -p "Remove Claude Code settings ($SETTINGS_FILE)? [y/N] " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -f "$SETTINGS_FILE"
        echo -e "  ${GREEN}[OK]${NC} Removed $SETTINGS_FILE"
    else
        echo -e "  ${YELLOW}[KEEP]${NC} $SETTINGS_FILE"
    fi
fi

# Clean up PATH addition from shell rc files
echo ""
echo -e "${CYAN}Cleaning shell configuration...${NC}"

for rc_file in "$HOME/.bashrc" "$HOME/.zshrc"; do
    if [ -f "$rc_file" ]; then
        if grep -q "Agent Dashboard" "$rc_file" 2>/dev/null; then
            # Create backup
            cp "$rc_file" "$rc_file.bak"
            # Remove the Agent Dashboard lines (the comment and the PATH export)
            grep -v "Agent Dashboard" "$rc_file.bak" | grep -v '# Agent Dashboard' > "$rc_file.tmp" || true
            mv "$rc_file.tmp" "$rc_file"
            echo -e "  ${GREEN}[OK]${NC} Cleaned $rc_file (backup: $rc_file.bak)"
        fi
    fi
done

# Check for Docker containers
if command -v docker &> /dev/null; then
    if docker ps -a --filter "name=agent-dashboard" --format "{{.Names}}" 2>/dev/null | grep -q "agent-dashboard"; then
        echo ""
        echo -e "${YELLOW}Docker container found.${NC}"
        read -p "Remove Docker container and image? [y/N] " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker stop agent-dashboard 2>/dev/null || true
            docker rm agent-dashboard 2>/dev/null || true
            docker rmi agent-dashboard:latest 2>/dev/null || true
            docker volume rm agent-dashboard-data 2>/dev/null || true
            echo -e "  ${GREEN}[OK]${NC} Removed Docker resources"
        fi
    fi
fi

echo ""
echo -e "${GREEN}=============================================="
echo "         Uninstallation Complete!             "
echo "==============================================${NC}"
echo ""
echo "To reinstall, run:"
echo "  git clone https://github.com/Koplal/agent-dashboard.git"
echo "  cd agent-dashboard && ./scripts/install.sh"
echo ""
