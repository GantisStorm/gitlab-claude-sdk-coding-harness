#!/bin/bash
# shellcheck shell=bash
#
# Docker entrypoint for Coding Harness
#
# Architecture:
#   1. Start agent daemon in background (manages agent processes)
#   2. Run TUI in foreground (connects to daemon)
#   3. TUI can exit/restart, daemon + agents keep running
#   4. Container exit stops everything
#

set -e

DAEMON_PID=""
SOCKET_PATH="/tmp/coding-harness-daemon.sock"
PID_FILE="/tmp/coding-harness-daemon.pid"

# =============================================================================
# Git Credential Configuration
# =============================================================================
# Configure git to use GITLAB_PERSONAL_ACCESS_TOKEN for HTTP(S) authentication.
# This enables git fetch/pull to work in non-interactive Docker environments.
# Sets up a credential helper that provides the token for any GitLab host.
configure_git_credentials() {
    if [[ -z "$GITLAB_PERSONAL_ACCESS_TOKEN" ]]; then
        return 0
    fi

    # Configure git to use credential helper that reads from environment
    # This works for any GitLab host (powerchat.gg, gitlab.com, self-hosted)
    git config --global credential.helper '!f() {
        if [ "$1" = "get" ]; then
            # Read host from stdin
            while read line; do
                case "$line" in
                    host=*) HOST="${line#host=}" ;;
                esac
            done
            # Return credentials
            echo "username=oauth2"
            echo "password=$GITLAB_PERSONAL_ACCESS_TOKEN"
        fi
    }; f'

    echo "Git credentials configured from GITLAB_PERSONAL_ACCESS_TOKEN"
}

configure_git_credentials

# Clean up daemon process on container exit.
# Called by trap on INT/TERM signals.
cleanup() {
    echo ""
    echo "Stopping daemon..."
    if [[ -n "$DAEMON_PID" ]] && kill -0 "$DAEMON_PID" 2>/dev/null; then
        kill "$DAEMON_PID" 2>/dev/null || true
        wait "$DAEMON_PID" 2>/dev/null || true
    fi
    echo "Container stopped."
    exit 0
}

trap cleanup INT TERM

# Display interactive menu for container control.
show_menu() {
    echo ""
    echo "╔═══════════════════════════════════════╗"
    echo "║       Coding Harness Container        ║"
    echo "╠═══════════════════════════════════════╣"
    echo "║  [Enter]     Start/Restart TUI        ║"
    echo "║  [Ctrl+C]    Stop container           ║"
    echo "║  [Ctrl+P,Q]  Detach (keep running)    ║"
    echo "╚═══════════════════════════════════════╝"
    echo ""
}

# Reset terminal to sane state after TUI exit or errors.
reset_terminal() {
    stty sane 2>/dev/null || true
    stty echo 2>/dev/null || true
    stty icanon 2>/dev/null || true
    tput reset 2>/dev/null || true
}

# Start the agent daemon process.
# Cleans up stale sockets and waits for daemon to be ready.
start_daemon() {
    local i
    # Clean up stale socket from previous container (socket persists via /tmp mount)
    if [[ -S "$SOCKET_PATH" ]]; then
        # Test if daemon is actually responding
        if ! python -c "import socket; s=socket.socket(socket.AF_UNIX); s.settimeout(1); s.connect('$SOCKET_PATH'); s.close()" 2>/dev/null; then
            echo "Removing stale daemon socket..."
            rm -f "$SOCKET_PATH"
            rm -f "$PID_FILE"
        else
            echo "Daemon already running."
            return 0
        fi
    fi

    echo "Starting agent daemon..."
    python -m agent.daemon &
    DAEMON_PID=$!

    # Wait for socket to appear
    for i in {1..10}; do
        if [[ -S "$SOCKET_PATH" ]]; then
            echo "Daemon started (PID: $DAEMON_PID)"
            return 0
        fi
        sleep 0.5
    done

    echo "Warning: Daemon socket not found after 5 seconds"
    return 1
}

# Start daemon on container start
start_daemon

# Main loop - TUI can exit and restart, daemon keeps running
while true; do
    reset_terminal
    show_menu

    # Wait for Enter (5 minute timeout to prevent indefinite hang)
    if read -r -t 300 </dev/tty 2>/dev/null; then
        reset_terminal
        echo "Starting TUI..."
        python -m tui.main "$@" </dev/tty || true
        reset_terminal
        echo ""
        echo "TUI exited. Agents continue running in daemon."
    else
        sleep 1
        reset_terminal
    fi
done
