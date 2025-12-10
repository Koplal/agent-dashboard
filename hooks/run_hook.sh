#!/usr/bin/env bash
# =============================================================================
# run_hook.sh - Cross-Platform Hook Wrapper
# =============================================================================
# Finds the correct Python command and executes send_event.py
# Works on: Windows Git Bash, macOS, Linux, WSL2
#
# Note: The installer (scripts/install.sh) generates this file during setup.
#       This copy is for reference and manual installations.
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Find Python 3.9+ (cross-platform)
find_python() {
    for cmd in python3 python python3.12 python3.11 python3.10 python3.9; do
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
[ -z "$PYTHON_CMD" ] && exit 0

# Execute the hook
exec "$PYTHON_CMD" "$SCRIPT_DIR/send_event.py" "$@"
