"""
Prompt Loading & Configuration Utilities
=========================================

Functions for loading prompt templates and multi-spec configuration support.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from common.utils import generate_spec_hash, spec_filename_to_slug

__all__ = [
    "get_initializer_prompt",
    "get_coding_prompt",
    "get_mr_creation_prompt",
    "initialize_agent_workspace",
    "TEMPLATES_DIR",
]

TEMPLATES_DIR = Path(__file__).parent / "templates"
SKILLS_DIR = Path(__file__).parent.parent / "skills"


def _validate_non_empty_string(value: str, name: str) -> None:
    """Validate that a string parameter is non-empty.

    Args:
        value: The string value to validate
        name: Parameter name for error messages

    Raises:
        ValueError: If value is empty or whitespace-only
    """
    if not value or not value.strip():
        raise ValueError(f"{name} cannot be empty")


def get_initializer_prompt(target_branch: str, spec_slug: str, spec_hash: str) -> str:
    """Load the initializer prompt with variables substituted.

    Template substitution approach:
    - Uses simple string replacement for {{TARGET_BRANCH}} and {{SPEC_SLUG}} markers
    - These markers should NOT appear in code examples within the prompt files
    - Limitation: String replacement doesn't distinguish between template markers
      and literal text in examples, so avoid using these patterns in examples

    Args:
        target_branch: The branch to target for merge requests
        spec_slug: The spec slug for the agent state directory
        spec_hash: The spec hash for the agent state directory

    Raises:
        ValueError: If any parameter is empty or invalid
    """
    _validate_non_empty_string(target_branch, "target_branch")
    _validate_non_empty_string(spec_slug, "spec_slug")
    _validate_non_empty_string(spec_hash, "spec_hash")

    prompt = _load_prompt("initializer_prompt")
    prompt = prompt.replace("{{TARGET_BRANCH}}", target_branch)
    prompt = prompt.replace("{{SPEC_SLUG}}", f"{spec_slug}-{spec_hash}")
    return prompt


def get_coding_prompt(spec_slug: str, spec_hash: str) -> str:
    """Load the coding agent prompt.

    Template substitution approach:
    - Uses simple string replacement for {{SPEC_SLUG}} markers
    - These markers should NOT appear in code examples within the prompt files
    - See get_initializer_prompt() for details on substitution limitations

    Args:
        spec_slug: The spec slug for finding state files
        spec_hash: The spec hash for finding state files

    Raises:
        ValueError: If any parameter is empty or invalid
    """
    _validate_non_empty_string(spec_slug, "spec_slug")
    _validate_non_empty_string(spec_hash, "spec_hash")

    prompt = _load_prompt("coding_prompt")
    prompt = prompt.replace("{{SPEC_SLUG}}", f"{spec_slug}-{spec_hash}")
    return prompt


def get_mr_creation_prompt(spec_slug: str, spec_hash: str, target_branch: str = "main") -> str:
    """Load the MR creation prompt.

    Template substitution approach:
    - Uses simple string replacement for {{SPEC_SLUG}} and {{TARGET_BRANCH}} markers
    - These markers should NOT appear in code examples within the prompt files
    - See get_initializer_prompt() for details on substitution limitations

    Args:
        spec_slug: The spec slug for finding state files
        spec_hash: The spec hash for finding state files
        target_branch: The target branch for the merge request

    Raises:
        ValueError: If any parameter is empty or invalid
    """
    _validate_non_empty_string(spec_slug, "spec_slug")
    _validate_non_empty_string(spec_hash, "spec_hash")
    _validate_non_empty_string(target_branch, "target_branch")

    prompt = _load_prompt("mr_creation_prompt")
    prompt = prompt.replace("{{SPEC_SLUG}}", f"{spec_slug}-{spec_hash}")
    prompt = prompt.replace("{{TARGET_BRANCH}}", target_branch)
    return prompt


def initialize_agent_workspace(
    project_dir: Path,
    spec_source: Path,
    target_branch: str,
    code_quality_skill: Path | None = None,
) -> tuple[Path, str, str]:
    """Initialize the agent workspace before Claude Code starts.

    Creates the isolated directory structure, copies the spec file,
    and copies skills to the project's .claude/skills/ directory.
    This is called BEFORE the agent runs so Claude doesn't have to create directories.

    Args:
        project_dir: The project root directory
        spec_source: Path to the source spec file
        target_branch: Target branch for merge request
        code_quality_skill: Optional path to a code quality skill preset file

    Returns:
        Tuple of (agent_dir, spec_slug, spec_hash) where:
        - agent_dir: Path to .claude-agent/<slug>-<hash>
        - spec_slug: Unique spec identifier (without hash)
        - spec_hash: 5-character spec content hash

    Creates:
        - .claude-agent/<slug>-<hash>/ directory
        - .claude-agent/<slug>-<hash>/app_spec.txt (copied from spec_source)
        - .claude-agent/<slug>-<hash>/.workspace_info.json (minimal metadata)
        - .claude-agent/<slug>-<hash>/.hitl_checkpoint_log.json (checkpoint history, created on first checkpoint)
        - .claude-agent/<slug>-<hash>/.gitlab_milestone.json (milestone state, created during initialization)
        - .claude/<slug>-<hash>/skills/ (copied from harness)
    """
    # Generate slug from spec filename
    spec_slug = spec_filename_to_slug(spec_source)
    spec_hash = generate_spec_hash(spec_source)

    # Create isolated directory structure
    agent_dir = project_dir / ".claude-agent" / f"{spec_slug}-{spec_hash}"
    agent_dir.mkdir(parents=True, exist_ok=True)

    # Copy spec file
    spec_dest = agent_dir / "app_spec.txt"
    shutil.copy(spec_source, spec_dest)

    # Create initial workspace info file (helps agent understand context)
    workspace_info = agent_dir / ".workspace_info.json"

    info = {
        "spec_slug": spec_slug,
        "spec_hash": spec_hash,
        "target_branch": target_branch,
        "feature_branch": f"feature/{spec_slug}-{spec_hash}",
        "spec_file": "app_spec.txt",
        "initialized": True,
        "auto_accept": False,
        "code_quality_skill": str(code_quality_skill) if code_quality_skill else None,
    }
    workspace_info.write_text(json.dumps(info, indent=2), encoding="utf-8")

    # Copy skills to project's .claude/skills/ directory (if not already present)
    _copy_skills_to_project(project_dir, code_quality_skill)

    return agent_dir, spec_slug, spec_hash


# ============================================================================
# Private Helper Functions
# ============================================================================


def _load_prompt(name: str) -> str:
    """Load a prompt template from the templates directory."""
    prompt_path = TEMPLATES_DIR / f"{name}.md"
    try:
        return prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Prompt template not found: {prompt_path}") from e
    except (OSError, UnicodeDecodeError) as e:
        raise OSError(f"Failed to read prompt template {prompt_path}: {e}") from e


def _copy_skills_to_project(project_dir: Path, code_quality_skill: Path | None = None) -> None:
    """Copy harness skills to agent workspace for Claude Code integration.

    Copies the .claude/skills directory from the harness installation
    to the agent workspace so the agent can use harness-specific skills.
    Only copies skills that don't already exist in the project, allowing
    projects to customize skills while getting defaults from the harness.

    If a code_quality_skill preset is provided, it will be used instead of
    the default template for the code-quality skill.

    Args:
        project_dir: Agent workspace directory (.claude-agent/<slug>-<hash>)
        code_quality_skill: Optional path to a code quality skill preset file
    """
    if not SKILLS_DIR.exists():
        print(f"   - Skills directory not found: {SKILLS_DIR}")
        return

    project_skills_dir = project_dir / ".claude" / "skills"

    # Copy each skill directory
    for skill_dir in SKILLS_DIR.iterdir():
        if not skill_dir.is_dir():
            continue

        skill_name = skill_dir.name
        dest_skill_dir = project_skills_dir / skill_name

        # Only copy if skill doesn't exist in project (don't overwrite customizations)
        if not dest_skill_dir.exists():
            dest_skill_dir.mkdir(parents=True, exist_ok=True)

            # Special handling for code-quality skill with preset
            if skill_name == "code-quality" and code_quality_skill and code_quality_skill.exists():
                # Copy the selected preset as SKILL.md
                shutil.copy(code_quality_skill, dest_skill_dir / "SKILL.md")
                print(f"   - Copied skill: {skill_name} (preset: {code_quality_skill.stem})")
            else:
                # Copy all files in the skill directory (except presets subdirectory)
                for file in skill_dir.iterdir():
                    if file.is_file():
                        shutil.copy(file, dest_skill_dir / file.name)
                print(f"   - Copied skill: {skill_name}")
        else:
            print(f"   - Skill exists (not overwriting): {skill_name}")
