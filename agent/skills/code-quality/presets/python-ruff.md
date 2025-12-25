---
description: Code quality checks for Python projects using ruff and pyright
language: python
---

# Code Quality Skill - Python (ruff + pyright)

This skill runs code quality checks for Python projects using ruff for linting/formatting and pyright for type checking.

---

## SECTION 1: Project Configuration

### Language/Framework
- **Language:** Python
- **Package Manager:** pip / uv / poetry
- **Virtual Environment:** .venv (standard) or venv

### Quality Tools
- **Linter:** ruff
- **Formatter:** ruff format
- **Type Checker:** pyright
- **Test Runner:** pytest

### Commands

```bash
# Linting (check for errors and code smells)
.venv/bin/ruff check .

# Formatting (auto-format code)
.venv/bin/ruff format .

# Type Checking (static type analysis)
.venv/bin/pyright

# All-in-One Quality Check (run before commits)
.venv/bin/ruff check . --fix && .venv/bin/ruff format . && .venv/bin/pyright

# Tests (run test suite)
.venv/bin/pytest
```

---

## SECTION 2: Check Environment Status

Before running checks, verify the development environment is ready:

```bash
# Check if ruff and pyright are available
.venv/bin/ruff --version && .venv/bin/pyright --version
```

**If tools are NOT available:**
- Report the missing tools to the user
- **STOP** - wait for human to install dependencies
- Do not proceed with code quality checks

**If tools are available:**
- Proceed to Section 3

---

## SECTION 3: Understand the Environment

Read the project's documentation to understand:
- How to access the application (URLs, ports)
- What services are running
- How to run tests

Check for:
- `CLAUDE.md` - Project-specific agent instructions
- `README.md` - Setup and development info
- `pyproject.toml` or `ruff.toml` - Linting configuration
- `pyrightconfig.json` - Type checking configuration

---

## SECTION 4: Run Code Quality Checks

Run the quality commands defined in Section 1. Execute in this order:

### 4.1 Linting
```bash
# Run ruff to find errors
.venv/bin/ruff check .
```

### 4.2 Formatting
```bash
# Auto-format code with ruff
.venv/bin/ruff format .
```

### 4.3 Type Checking
```bash
# Run pyright for static type analysis
.venv/bin/pyright
```

### 4.4 Dead Code Detection

Scan for unused code before proceeding:

```bash
# Check for unused imports (F401), unused variables (F841), and unused arguments (ARG)
.venv/bin/ruff check . --select F401,F841,ARG

# Auto-fix unused imports (safe to auto-fix)
.venv/bin/ruff check . --select F401 --fix
```

**Optional deeper analysis with vulture:**
```bash
# Only if vulture is installed
.venv/bin/vulture . --min-confidence 80 2>/dev/null || echo "vulture not installed, skipping"
```

**Interpreting results:**
- F401 (unused imports): Auto-fix with `--fix` - safe to remove
- F841 (unused variables): Review manually - may indicate incomplete implementation
- ARG (unused arguments): Review manually - may be intentional for API compatibility

---

## SECTION 5: Fix Errors

### Auto-fixable errors

```bash
# Auto-fix linting issues
.venv/bin/ruff check . --fix

# Format code
.venv/bin/ruff format .
```

### Manual fixes

| Error Type | Fix |
|------------|-----|
| Missing imports | Add the required import statement |
| Type mismatches | Check type hints, fix return types or parameter types |
| Unused variables | Remove or prefix with `_unused_var` |
| Unused imports | Remove the import (auto-fixable) |
| Missing type hints | Add type annotations to function signatures |

### Common ruff rules

| Rule | Description |
|------|-------------|
| E | pycodestyle errors |
| W | pycodestyle warnings |
| F | pyflakes (unused imports, variables) |
| I | isort (import sorting) |
| UP | pyupgrade (Python version upgrades) |
| B | flake8-bugbear (common bugs) |
| SIM | flake8-simplify (code simplification) |

---

## SECTION 6: Verify All Checks Pass

After fixing errors, re-run the full quality check:

```bash
.venv/bin/ruff check . --fix && .venv/bin/ruff format . && .venv/bin/pyright
```

**Expected output:** All checks pass with no errors.

**If checks still fail:**
1. Read error messages carefully
2. Fix remaining issues
3. Re-run checks
4. Repeat until all pass

---

## SECTION 7: Run Tests

```bash
.venv/bin/pytest
```

**For verbose output:**
```bash
.venv/bin/pytest -v --tb=short
```

**For specific test files:**
```bash
.venv/bin/pytest tests/test_specific.py
```

**If tests fail:**
1. Identify which tests are failing
2. Determine if failure is related to your changes
3. Fix test failures before proceeding

---

## SECTION 8: Report Results

Report to the calling agent:

**If all checks pass:**
```
Code quality checks PASSED
  - Ruff linting: No errors
  - Ruff formatting: Applied
  - Pyright type checking: No errors
  - Ready to proceed
```

**If checks fail:**
```
Code quality checks FAILED
  - [List specific errors]
  - [What was attempted to fix]
  - [What still needs fixing]
```

---

## When This Skill Is Invoked

The coding agent should invoke this skill:

1. **After implementing a feature** - Before testing
2. **After fixing bugs** - Before creating checkpoint
3. **After any code changes** - Before committing
4. **Before issue_closure checkpoint** - MUST pass all checks

**DO NOT request issue closure approval if code quality checks are failing.**

---

## Configuration Files

This preset expects the following configuration files:

### ruff.toml (or pyproject.toml [tool.ruff])
```toml
line-length = 120
target-version = "py311"

[lint]
select = ["E", "W", "F", "I", "UP", "B", "SIM"]
ignore = ["E501"]  # Line too long (handled by formatter)

[format]
quote-style = "double"
indent-style = "space"
```

### pyrightconfig.json
```json
{
  "include": ["src", "tests"],
  "exclude": ["**/__pycache__", ".venv"],
  "typeCheckingMode": "basic",
  "reportMissingImports": true,
  "reportMissingTypeStubs": false
}
```
