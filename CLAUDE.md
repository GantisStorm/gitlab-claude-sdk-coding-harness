# Code Quality Workflow

**After making code changes, run code quality checks.**

## Quick Command

```bash
# Run this after every code edit
.venv/bin/ruff check . --fix && .venv/bin/ruff format . && .venv/bin/pyright
```

This auto-fixes linting issues, formats code, and checks types.

## Skills Reference

For detailed commands and usage:

- **Code Quality Commands:** See `.claude/skills/code-quality.md`
  - All linting, formatting, and type checking commands
  - Troubleshooting and configuration info
  - Pre-commit workflow

## Configuration Files

- `ruff.toml` - Linting and formatting rules (120 char line limit)
- `pyrightconfig.json` - Type checking rules
- `.pylintrc` - IDE warnings configuration

**Don't modify these** unless necessary - they affect the entire team.

## IDE + CLI Integration

Your IDE (Cursor) and CLI use the **same configuration files**:
- **Pyright** (`pyrightconfig.json`) - Type checking in both IDE and CLI
- **Pylint** (`.pylintrc`) - IDE warnings only
- **Ruff** (`ruff.toml`) - CLI only (no IDE extension available)

This means:
- Red squiggles (IDE) = Type errors from Pyright → **Must fix**
- Yellow squiggles (IDE) = Warnings from Pylint → Should fix
- CLI checks = Same errors as IDE

## Before Committing

Always run the quick command above before committing. All checks must pass.

```bash
# If checks pass, commit
git add .
git commit -m "Your message"
```

---

For detailed instructions, troubleshooting, and all available commands, see the skills files in `.claude/skills/`.
