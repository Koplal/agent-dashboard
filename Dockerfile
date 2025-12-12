# =============================================================================
# Agent Dashboard - Multi-Stage Dockerfile
# =============================================================================
# Build: docker build -t agent-dashboard .
# Run:   docker run -d -p 4200:4200 agent-dashboard
#
# This Dockerfile creates a minimal, secure container for the Agent Dashboard.

# -----------------------------------------------------------------------------
# Stage 1: Builder - Install dependencies
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies (needed for some pip packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# -----------------------------------------------------------------------------
# Stage 2: Runtime - Minimal production image
# -----------------------------------------------------------------------------
FROM python:3.11-slim

# Image metadata
LABEL org.opencontainers.image.title="Agent Dashboard"
LABEL org.opencontainers.image.description="Real-time monitoring for Claude Code multi-agent workflows"
LABEL org.opencontainers.image.version="2.2.1"
LABEL org.opencontainers.image.source="https://github.com/Koplal/agent-dashboard"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash appuser

# Copy installed packages from builder
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH

# Copy application code
COPY --chown=appuser:appuser dashboard/ ./dashboard/
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser hooks/ ./hooks/
COPY --chown=appuser:appuser agents/ ./agents/

# Create Claude directory structure (mimics local installation)
RUN mkdir -p /home/appuser/.claude/dashboard/hooks \
    && mkdir -p /home/appuser/.claude/agents \
    && mkdir -p /home/appuser/.claude/logs \
    && cp -r agents/* /home/appuser/.claude/agents/ \
    && cp dashboard/agent_monitor.py /home/appuser/.claude/dashboard/ \
    && cp src/web_server.py /home/appuser/.claude/dashboard/ \
    && cp src/cli.py /home/appuser/.claude/dashboard/ \
    && cp src/workflow_engine.py /home/appuser/.claude/dashboard/ \
    && cp hooks/send_event.py /home/appuser/.claude/dashboard/hooks/ \
    && chown -R appuser:appuser /home/appuser/.claude

# Switch to non-root user for security
USER appuser
WORKDIR /home/appuser

# Expose dashboard port
EXPOSE 4200

# Health check - verify server is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:4200/health || exit 1

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Default command - start web dashboard
CMD ["python", "/home/appuser/.claude/dashboard/web_server.py", "--port", "4200"]
