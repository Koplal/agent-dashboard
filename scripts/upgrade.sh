#!/usr/bin/env bash
# =============================================================================
# upgrade.sh - Agent Dashboard Upgrader
# =============================================================================
# Updates the Agent Dashboard to the latest version from git.
#
# Usage:
#   ./scripts/upgrade.sh
#   agent-dashboard upgrade
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
echo "       Agent Dashboard Upgrader              "
echo "=============================================="
echo -e "${NC}"

# Find the repository directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

# Check if we're in a git repository
if [ ! -d "$REPO_DIR/.git" ]; then
    echo -e "${YELLOW}[WARN]${NC} Not a git repository. Cannot auto-upgrade."
    echo ""
    echo "To upgrade manually:"
    echo "  1. Download the latest version from GitHub"
    echo "  2. Run: ./scripts/install.sh"
    echo ""
    echo "Or clone fresh:"
    echo "  git clone https://github.com/Koplal/agent-dashboard.git"
    echo "  cd agent-dashboard && ./scripts/install.sh"
    exit 1
fi

cd "$REPO_DIR"

# Check for uncommitted changes
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    echo -e "${YELLOW}[WARN]${NC} You have uncommitted changes"
    echo ""
    git status --short
    echo ""
    read -p "Stash changes and continue? [y/N] " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git stash
        STASHED=true
        echo -e "  ${GREEN}[OK]${NC} Changes stashed"
    else
        echo "Upgrade cancelled."
        exit 0
    fi
else
    STASHED=false
fi

# Get current version
CURRENT_COMMIT=$(git rev-parse --short HEAD)
echo -e "${CYAN}[1/4] Current version: $CURRENT_COMMIT${NC}"

# Fetch latest changes
echo -e "\n${CYAN}[2/4] Fetching latest version...${NC}"
git fetch origin

# Check for updates
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main 2>/dev/null || git rev-parse origin/master 2>/dev/null)

if [ "$LOCAL" = "$REMOTE" ]; then
    echo -e "${GREEN}[OK]${NC} Already up to date!"

    if [ "$STASHED" = true ]; then
        git stash pop
        echo -e "  ${GREEN}[OK]${NC} Restored stashed changes"
    fi
    exit 0
fi

# Show what will be updated
echo ""
echo "Changes to be applied:"
git log --oneline HEAD..origin/main 2>/dev/null || git log --oneline HEAD..origin/master 2>/dev/null | head -10
echo ""

read -p "Apply these updates? [y/N] " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Upgrade cancelled."
    if [ "$STASHED" = true ]; then
        git stash pop
    fi
    exit 0
fi

# Pull updates
echo -e "\n${CYAN}[3/4] Pulling updates...${NC}"
git pull origin main 2>/dev/null || git pull origin master

NEW_COMMIT=$(git rev-parse --short HEAD)
echo -e "  ${GREEN}[OK]${NC} Updated from $CURRENT_COMMIT to $NEW_COMMIT"

# Restore stashed changes
if [ "$STASHED" = true ]; then
    echo ""
    echo "Restoring stashed changes..."
    if git stash pop; then
        echo -e "  ${GREEN}[OK]${NC} Restored stashed changes"
    else
        echo -e "  ${YELLOW}[WARN]${NC} Conflict restoring changes. Run: git stash pop"
    fi
fi

# Re-run installer
echo -e "\n${CYAN}[4/4] Re-installing...${NC}"
./scripts/install.sh

echo ""
echo -e "${GREEN}=============================================="
echo "           Upgrade Complete!                  "
echo "==============================================${NC}"
echo ""
echo "Updated from $CURRENT_COMMIT to $NEW_COMMIT"
echo ""
