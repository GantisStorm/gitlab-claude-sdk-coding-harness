"""Core agent logic - orchestration, client, and HITL checkpoints.

Exports:
    Client:
        create_client: Create configured Claude SDK client

    Orchestrator:
        determine_session_type: Determine which session phase to run
        run_autonomous_agent: Main agent execution loop

    HITL Checkpoints:
        approve_checkpoint: Approve a pending checkpoint
        reject_checkpoint: Reject a pending checkpoint
        resolve_checkpoint: Resolve checkpoint with custom data
        load_pending_checkpoint: Load most recent pending checkpoint
        is_checkpoint_pending: Check if checkpoint is pending
        get_pending_checkpoint_type: Get type of pending checkpoint
        is_checkpoint_type_approved: Check if checkpoint type was approved
        get_milestone_state_path: Get path to milestone state file
"""

from .client import create_client
from .hitl import (
    approve_checkpoint,
    get_milestone_state_path,
    get_pending_checkpoint_type,
    is_checkpoint_pending,
    is_checkpoint_type_approved,
    load_pending_checkpoint,
    reject_checkpoint,
    resolve_checkpoint,
)
from .orchestrator import determine_session_type, run_autonomous_agent

__all__ = [
    "create_client",
    "determine_session_type",
    "run_autonomous_agent",
    "approve_checkpoint",
    "reject_checkpoint",
    "resolve_checkpoint",
    "load_pending_checkpoint",
    "is_checkpoint_pending",
    "get_pending_checkpoint_type",
    "is_checkpoint_type_approved",
    "get_milestone_state_path",
]
