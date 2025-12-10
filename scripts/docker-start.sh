#!/usr/bin/env bash
# =============================================================================
# docker-start.sh - Quick Docker Deployment for Agent Dashboard
# =============================================================================
# This script builds and starts the Agent Dashboard in Docker.
#
# Usage:
#   ./scripts/docker-start.sh           # Start dashboard
#   ./scripts/docker-start.sh --build   # Force rebuild
#   ./scripts/docker-start.sh --stop    # Stop dashboard
#   ./scripts/docker-start.sh --logs    # View logs
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
echo "    Agent Dashboard - Docker Deployment      "
echo "=============================================="
echo -e "${NC}"

# Find script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

cd "$REPO_DIR"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}ERROR: Docker is not installed${NC}"
    echo ""
    echo "Install from: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if docker daemon is running
if ! docker info &> /dev/null; then
    echo -e "${RED}ERROR: Docker daemon is not running${NC}"
    echo ""
    echo "Start Docker Desktop or run: sudo systemctl start docker"
    exit 1
fi

# Check for docker-compose or docker compose
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
elif docker compose version &> /dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
else
    echo -e "${RED}ERROR: Docker Compose is not available${NC}"
    echo ""
    echo "Install from: https://docs.docker.com/compose/install/"
    exit 1
fi

# Parse arguments
ACTION="start"
FORCE_BUILD=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --build|-b)
            FORCE_BUILD=true
            shift
            ;;
        --stop|-s)
            ACTION="stop"
            shift
            ;;
        --logs|-l)
            ACTION="logs"
            shift
            ;;
        --restart|-r)
            ACTION="restart"
            shift
            ;;
        --status)
            ACTION="status"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "OPTIONS:"
            echo "  --build, -b    Force rebuild of Docker image"
            echo "  --stop, -s     Stop the dashboard"
            echo "  --logs, -l     View logs (follow mode)"
            echo "  --restart, -r  Restart the dashboard"
            echo "  --status       Show container status"
            echo "  --help, -h     Show this help"
            echo ""
            exit 0
            ;;
        *)
            shift
            ;;
    esac
done

case "$ACTION" in
    start)
        echo -e "${CYAN}Building and starting dashboard...${NC}"
        echo ""

        if [ "$FORCE_BUILD" = true ]; then
            echo "Forcing rebuild..."
            $COMPOSE_CMD build --no-cache
        else
            $COMPOSE_CMD build
        fi

        $COMPOSE_CMD up -d

        echo ""
        echo -e "${GREEN}=============================================="
        echo "         Dashboard is starting...             "
        echo "==============================================${NC}"
        echo ""
        echo "  Web Dashboard: http://localhost:4200"
        echo "  Health Check:  http://localhost:4200/health"
        echo ""
        echo "Commands:"
        echo "  View logs:     $COMPOSE_CMD logs -f"
        echo "  Stop:          $COMPOSE_CMD down"
        echo "  Restart:       $COMPOSE_CMD restart"
        echo ""

        # Wait for health check
        echo -n "Waiting for dashboard to be ready"
        for i in {1..30}; do
            if curl -sf http://localhost:4200/health > /dev/null 2>&1; then
                echo ""
                echo -e "${GREEN}Dashboard is ready!${NC}"
                break
            fi
            echo -n "."
            sleep 1
        done
        echo ""
        ;;

    stop)
        echo -e "${CYAN}Stopping dashboard...${NC}"
        $COMPOSE_CMD down
        echo -e "${GREEN}Dashboard stopped.${NC}"
        ;;

    logs)
        echo -e "${CYAN}Following logs (Ctrl+C to exit)...${NC}"
        $COMPOSE_CMD logs -f
        ;;

    restart)
        echo -e "${CYAN}Restarting dashboard...${NC}"
        $COMPOSE_CMD restart
        echo -e "${GREEN}Dashboard restarted.${NC}"
        ;;

    status)
        echo -e "${CYAN}Container status:${NC}"
        docker ps --filter "name=agent-dashboard" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

        echo ""
        if curl -sf http://localhost:4200/health > /dev/null 2>&1; then
            echo -e "${GREEN}Dashboard is healthy and responding${NC}"
        else
            echo -e "${YELLOW}Dashboard is not responding${NC}"
        fi
        ;;
esac
