#!/usr/bin/env python3
"""
Agent Daemon
============

Background daemon that manages agent lifecycle independently of the TUI.
Agents run as subprocesses of the daemon, with output written to log files.
TUI connects via Unix socket to control agents and tail logs.

Usage:
    python -m agent.daemon              # Start daemon (foreground)
    python -m agent.daemon --background # Start daemon (background)

Socket: /tmp/coding-harness-daemon.sock
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import signal
import subprocess
import sys
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypedDict


class AgentConfig(TypedDict, total=False):
    """Configuration for an agent process."""

    spec_file: str
    project_dir: str
    target_branch: str
    max_iterations: int
    auto_accept: bool
    spec_slug: str
    spec_hash: str


# Harness root directory
HARNESS_ROOT = Path(__file__).parent.parent.parent.resolve()

# Detect Docker mode: /app/.data exists (created by Dockerfile) or HARNESS_DOCKER env var
IN_DOCKER = Path("/app/.data").exists() or os.environ.get("HARNESS_DOCKER") == "1"

# Data directory for daemon state
# - Docker: /app/.data (ephemeral per container, or use named volume)
# - Native: .data/ in harness directory (persists locally)
DATA_DIR = Path("/app/.data") if IN_DOCKER else HARNESS_ROOT / ".data"

# Daemon paths
# - Socket/PID in /tmp (ephemeral)
# - State in DATA_DIR (see above)
# - Logs in project's .claude-agent/ directory (project-scoped, persisted via $HOME mount)
SOCKET_PATH = Path("/tmp/coding-harness-daemon.sock")
STATE_FILE = DATA_DIR / "daemon_state.json"
PID_FILE = Path("/tmp/coding-harness-daemon.pid")


@dataclass
class AgentProcess:
    """Tracks a running agent process."""

    agent_id: str
    config: AgentConfig
    process: subprocess.Popen | None = None
    log_file: Path | None = None
    status: str = "starting"  # starting, running, stopped, failed
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    stopped_at: str | None = None
    exit_code: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "agent_id": self.agent_id,
            "config": self.config,
            "status": self.status,
            "log_file": str(self.log_file) if self.log_file else None,
            "started_at": self.started_at,
            "stopped_at": self.stopped_at,
            "exit_code": self.exit_code,
            "pid": self.process.pid if self.process else None,
        }


class AgentDaemon:
    """Daemon that manages agent processes."""

    def __init__(self) -> None:
        self._agents: dict[str, AgentProcess] = {}
        self._server: asyncio.Server | None = None
        self._shutdown = False
        self._monitor_tasks: dict[str, asyncio.Task[None]] = {}

    def _append_to_log(self, log_file: Path | None, message: str) -> None:
        """Append a message to the agent's log file."""
        if log_file and log_file.exists():
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(message)

    def _save_state(self) -> None:
        """Save agent state to disk for persistence across daemon restarts."""
        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            state = {
                "agents": {
                    agent_id: {
                        "agent_id": agent.agent_id,
                        "config": agent.config,
                        "status": agent.status,
                        "log_file": str(agent.log_file) if agent.log_file else None,
                        "started_at": agent.started_at,
                        "stopped_at": agent.stopped_at,
                        "exit_code": agent.exit_code,
                    }
                    for agent_id, agent in self._agents.items()
                }
            }
            STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
        except (OSError, json.JSONDecodeError) as e:
            print(f"Warning: Failed to save state: {e}")

    def _load_state(self) -> None:
        """Load agent state from disk on daemon startup."""
        if not STATE_FILE.exists():
            return

        try:
            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            skipped = 0
            for agent_id, agent_data in state.get("agents", {}).items():
                # Validate spec file still exists before restoring
                config = agent_data.get("config", {})
                spec_file = config.get("spec_file")
                if spec_file and not Path(spec_file).exists():
                    print(f"Skipping agent {agent_id}: spec file no longer exists: {spec_file}")
                    skipped += 1
                    continue

                # Restore agent (process is gone, so mark as stopped if was running)
                status = agent_data.get("status", "stopped")
                if status == "running":
                    status = "stopped"  # Process died with daemon

                self._agents[agent_id] = AgentProcess(
                    agent_id=agent_data["agent_id"],
                    config=config,
                    log_file=Path(agent_data["log_file"]) if agent_data.get("log_file") else None,
                    status=status,
                    started_at=agent_data.get("started_at", datetime.now(UTC).isoformat()),
                    stopped_at=agent_data.get("stopped_at"),
                    exit_code=agent_data.get("exit_code"),
                    process=None,  # Process is gone
                )
            if self._agents:
                print(f"Restored {len(self._agents)} agent(s) from state file")
            if skipped:
                print(f"Skipped {skipped} agent(s) with missing spec files")
                self._save_state()  # Save cleaned state
        except (OSError, json.JSONDecodeError) as e:
            print(f"Warning: Failed to load state file: {e}")
        except KeyError as e:
            print(f"Warning: Invalid state file structure, missing key: {e}")

    async def start(self) -> None:
        """Start the daemon server."""
        # Clean up old socket
        if SOCKET_PATH.exists():
            SOCKET_PATH.unlink()

        # Load persisted state from previous daemon run
        self._load_state()

        # Write PID file
        PID_FILE.write_text(str(os.getpid()), encoding="utf-8")

        # Start Unix socket server
        self._server = await asyncio.start_unix_server(self._handle_client, path=str(SOCKET_PATH))

        # Set socket permissions (readable/writable by all)
        SOCKET_PATH.chmod(0o666)

        print(f"Agent daemon started on {SOCKET_PATH}")
        print(f"PID: {os.getpid()}")

        # Handle shutdown signals
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))

        async with self._server:
            await self._server.serve_forever()

    async def shutdown(self) -> None:
        """Gracefully shutdown the daemon."""
        if self._shutdown:
            return
        self._shutdown = True

        print("\nShutting down daemon...")

        # Stop all agents
        for agent_id in list(self._agents.keys()):
            await self._stop_agent(agent_id)

        # Cancel monitor tasks
        for task in self._monitor_tasks.values():
            task.cancel()

        # Stop server
        if self._server:
            self._server.close()
            await self._server.wait_closed()

        # Clean up
        if SOCKET_PATH.exists():
            SOCKET_PATH.unlink()
        if PID_FILE.exists():
            PID_FILE.unlink()

        print("Daemon stopped.")

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Handle a client connection."""
        try:
            while True:
                data = await reader.readline()
                if not data:
                    break

                try:
                    request = json.loads(data.decode())
                    response = await self._process_command(request)
                except json.JSONDecodeError:
                    response = {"error": "Invalid JSON"}

                writer.write(json.dumps(response).encode() + b"\n")
                await writer.drain()
        except (ConnectionResetError, BrokenPipeError):
            pass
        finally:
            writer.close()
            await writer.wait_closed()

    async def _process_command(self, request: dict[str, Any]) -> dict[str, Any]:
        """Process a command from the client using command dispatch."""
        cmd = request.get("cmd")
        if not isinstance(cmd, str):
            return {"status": "error", "message": "Command must be a string"}
        handlers: dict[str, Callable[[dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]] = {
            "ping": self._cmd_ping,
            "list": self._cmd_list,
            "register": self._cmd_register,
            "start": self._cmd_start,
            "stop": self._cmd_stop,
            "status": self._cmd_status,
            "remove": self._cmd_remove,
            "shutdown": self._cmd_shutdown,
        }
        handler = handlers.get(cmd)
        if handler:
            return await handler(request)
        return {"status": "error", "message": f"Unknown command: {cmd}"}

    def _validate_agent_id(
        self, request: dict[str, Any], must_exist: bool = True
    ) -> tuple[str | None, dict[str, Any] | None]:
        """Validate agent_id from request.

        Args:
            request: The request dict containing agent_id
            must_exist: If True, agent must already exist in self._agents

        Returns:
            Tuple of (agent_id, error_response). If validation passes, error_response is None.
            If validation fails, agent_id is None and error_response contains the error.
        """
        agent_id = request.get("agent_id")
        if not agent_id:
            return None, {"status": "error", "message": "agent_id required"}
        if must_exist and agent_id not in self._agents:
            return None, {"status": "error", "message": f"Agent {agent_id} not found"}
        if not must_exist and agent_id in self._agents:
            return None, {"status": "error", "message": f"Agent {agent_id} already exists"}
        return agent_id, None

    async def _cmd_ping(self, _request: dict[str, Any]) -> dict[str, Any]:
        """Handle ping command."""
        return {"status": "ok", "message": "pong"}

    async def _cmd_list(self, _request: dict[str, Any]) -> dict[str, Any]:
        """Handle list command."""
        return {
            "status": "ok",
            "agents": [agent.to_dict() for agent in self._agents.values()],
        }

    async def _cmd_register(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle register command - register agent without starting it."""
        config: AgentConfig = request.get("config", {})
        agent_id = request.get("agent_id")
        if not agent_id:
            return {"status": "error", "message": "agent_id required"}
        if agent_id in self._agents:
            return {"status": "error", "message": f"Agent {agent_id} already exists"}

        agent = AgentProcess(
            agent_id=agent_id,
            config=config,
            status="ready",
        )
        self._agents[agent_id] = agent
        self._save_state()
        return {"status": "ok", "agent": agent.to_dict()}

    async def _cmd_start(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle start command."""
        config: AgentConfig = request.get("config", {})
        agent_id = request.get("agent_id")
        if not agent_id:
            return {"status": "error", "message": "agent_id required"}

        # If agent exists and is stopped/ready, start it
        if agent_id in self._agents:
            existing = self._agents[agent_id]
            if existing.status == "running":
                return {"status": "error", "message": f"Agent {agent_id} already running"}
            # Update config and start
            existing.config = config
            return await self._start_existing_agent(agent_id, config)
        return await self._start_agent(agent_id, config)

    async def _cmd_stop(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle stop command."""
        agent_id, error = self._validate_agent_id(request)
        if error:
            return error
        assert agent_id is not None  # For type checker
        return await self._stop_agent(agent_id)

    async def _cmd_status(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle status command."""
        agent_id, error = self._validate_agent_id(request)
        if error:
            return error
        assert agent_id is not None  # For type checker
        return {"status": "ok", "agent": self._agents[agent_id].to_dict()}

    async def _cmd_remove(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle remove command."""
        agent_id, error = self._validate_agent_id(request)
        if error:
            return error
        assert agent_id is not None  # For type checker

        agent = self._agents[agent_id]
        if agent.status == "running":
            await self._stop_agent(agent_id)

        del self._agents[agent_id]
        self._save_state()
        return {"status": "ok", "message": f"Agent {agent_id} removed"}

    async def _cmd_shutdown(self, _request: dict[str, Any]) -> dict[str, Any]:
        """Handle shutdown command."""
        asyncio.create_task(self.shutdown())
        return {"status": "ok", "message": "Shutting down"}

    async def _start_existing_agent(self, agent_id: str, config: AgentConfig) -> dict[str, Any]:
        """Start an existing (registered) agent process."""
        agent = self._agents[agent_id]
        return await self._do_start_agent(agent, config)

    async def _start_agent(self, agent_id: str, config: AgentConfig) -> dict[str, Any]:
        """Start a new agent process (registers and starts)."""
        agent = AgentProcess(
            agent_id=agent_id,
            config=config,
            status="starting",
        )
        self._agents[agent_id] = agent
        return await self._do_start_agent(agent, config)

    async def _do_start_agent(self, agent: AgentProcess, config: AgentConfig) -> dict[str, Any]:  # pylint: disable=too-many-locals
        """Actually start an agent process."""
        agent_id = agent.agent_id

        # Extract config
        spec_file = config.get("spec_file")
        project_dir = config.get("project_dir")
        target_branch = config.get("target_branch", "main")
        max_iterations = config.get("max_iterations")
        auto_accept = config.get("auto_accept", False)

        if not spec_file or not project_dir:
            return {"status": "error", "message": "spec_file and project_dir required"}

        # Create log file in project's agent directory (project-scoped, persisted)
        spec_slug = config.get("spec_slug", "unknown")
        spec_hash = config.get("spec_hash", "00000")
        agent_dir = Path(project_dir) / ".claude-agent" / f"{spec_slug}-{spec_hash}"
        log_dir = agent_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        log_file = log_dir / f"{agent_id}-{timestamp}.log"

        # Build command
        cmd = [
            sys.executable,
            "-m",
            "agent.cli",
            "--spec-file",
            spec_file,
            "--project-dir",
            project_dir,
            "--target-branch",
            target_branch,
        ]

        if max_iterations:
            cmd.extend(["--max-iterations", str(max_iterations)])

        # Set up environment
        env = os.environ.copy()
        # Add harness directory to PYTHONPATH so agent.cli can be found
        harness_dir = str(Path(__file__).parent.parent.parent)
        env["PYTHONPATH"] = harness_dir + os.pathsep + env.get("PYTHONPATH", "")
        if auto_accept:
            env["CODING_HARNESS_AUTO_ACCEPT"] = "1"

        # Update agent record
        agent.log_file = log_file
        agent.status = "starting"
        agent.started_at = datetime.now(UTC).isoformat()

        try:
            # Start process with output redirected to log file
            with open(log_file, "w", encoding="utf-8") as log_f:
                log_f.write(f"=== Agent {agent_id} started at {agent.started_at} ===\n")
                log_f.write(f"Command: {' '.join(cmd)}\n")
                log_f.write(f"Working directory: {project_dir}\n")
                log_f.write("=" * 60 + "\n\n")
                log_f.flush()

                process = subprocess.Popen(
                    cmd,
                    stdout=log_f,
                    stderr=subprocess.STDOUT,
                    cwd=project_dir,
                    env=env,
                    start_new_session=True,  # Detach from terminal
                )

            agent.process = process
            agent.status = "running"

            # Start monitor task
            self._monitor_tasks[agent_id] = asyncio.create_task(self._monitor_agent(agent_id))

            # Persist state
            self._save_state()

            return {
                "status": "ok",
                "agent": agent.to_dict(),
                "message": f"Agent {agent_id} started",
            }

        except (OSError, subprocess.SubprocessError) as e:
            agent.status = "failed"
            self._save_state()
            return {"status": "error", "message": f"Failed to start agent: {e}"}

    async def _stop_agent(self, agent_id: str) -> dict[str, Any]:
        """Stop an agent process."""
        agent = self._agents.get(agent_id)
        if not agent:
            return {"status": "error", "message": f"Agent {agent_id} not found"}

        if agent.process and agent.process.poll() is None:
            # Process is running, terminate it
            agent.process.terminate()
            try:
                # Wait up to 5 seconds for graceful shutdown
                await asyncio.wait_for(
                    asyncio.create_task(asyncio.to_thread(agent.process.wait)),
                    timeout=5.0,
                )
            except TimeoutError:
                # Force kill
                agent.process.kill()
                agent.process.wait()

            agent.exit_code = agent.process.returncode

        agent.status = "stopped"
        agent.stopped_at = datetime.now(UTC).isoformat()

        # Append to log
        self._append_to_log(
            agent.log_file,
            f"\n=== Agent stopped at {agent.stopped_at} ===\nExit code: {agent.exit_code}\n",
        )

        # Cancel monitor task
        if agent_id in self._monitor_tasks:
            self._monitor_tasks[agent_id].cancel()
            del self._monitor_tasks[agent_id]

        # Persist state
        self._save_state()

        return {"status": "ok", "agent": agent.to_dict()}

    async def _monitor_agent(self, agent_id: str) -> None:
        """Monitor an agent process for completion."""
        agent = self._agents.get(agent_id)
        if not agent or not agent.process:
            return

        try:
            while agent.process.poll() is None:
                await asyncio.sleep(1.0)

            # Process has exited
            agent.exit_code = agent.process.returncode
            agent.status = "stopped"
            agent.stopped_at = datetime.now(UTC).isoformat()

            # Append to log
            self._append_to_log(
                agent.log_file,
                f"\n=== Agent exited at {agent.stopped_at} ===\nExit code: {agent.exit_code}\n",
            )

            # Persist state
            self._save_state()

        except asyncio.CancelledError:
            pass


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Coding Harness Agent Daemon")
    parser.add_argument("--background", action="store_true", help="Run in background")
    args = parser.parse_args()

    if args.background:
        # Fork and run in background
        pid = os.fork()
        if pid > 0:
            # Parent exits
            print(f"Daemon started in background (PID: {pid})")
            sys.exit(0)
        # Child continues
        os.setsid()

    daemon = AgentDaemon()
    with contextlib.suppress(KeyboardInterrupt, asyncio.CancelledError):
        asyncio.run(daemon.start())


if __name__ == "__main__":
    main()
