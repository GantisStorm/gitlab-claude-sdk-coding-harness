"""Agent package - Core agent logic for coding harness.

Structure:
    agent/
    ├── cli.py              # CLI entry point (python -m agent.cli)
    ├── core/               # Core agent logic
    │   ├── orchestrator.py # Main agent loop
    │   ├── client.py       # Claude SDK client
    │   └── hitl.py         # HITL checkpoints
    ├── daemon/             # Background daemon
    │   ├── server.py       # Daemon process
    │   └── client.py       # TUI client
    ├── prompts/            # Prompt templates
    │   ├── __init__.py     # Loader functions
    │   └── templates/      # Markdown templates
    └── skills/             # Agent skills

Public API:
- run_autonomous_agent: Main agent execution loop
- determine_session_type: Determine which phase to run
- create_client: Create configured Claude SDK client
"""

from .core import create_client, determine_session_type, run_autonomous_agent

__all__ = [
    "run_autonomous_agent",
    "determine_session_type",
    "create_client",
]
