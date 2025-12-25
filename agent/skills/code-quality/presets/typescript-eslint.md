---
description: Code quality checks for TypeScript/JavaScript projects using ESLint and Prettier
language: typescript
---

# Code Quality Skill - TypeScript/JavaScript (ESLint + Prettier)

This skill runs code quality checks for TypeScript/JavaScript projects using ESLint for linting and Prettier for formatting.

---

## SECTION 1: Project Configuration

### Language/Framework
- **Language:** TypeScript / JavaScript
- **Package Manager:** npm / pnpm / yarn
- **Runtime:** Node.js

### Quality Tools
- **Linter:** ESLint
- **Formatter:** Prettier
- **Type Checker:** TypeScript (tsc)
- **Test Runner:** Jest / Vitest

### Commands

```bash
# Linting (check for errors and code smells)
npm run lint

# Formatting (auto-format code)
npm run format

# Type Checking (static type analysis)
npm run typecheck

# All-in-One Quality Check (run before commits)
npm run lint && npm run typecheck

# Tests (run test suite)
npm test
```

---

## SECTION 2: Check Environment Status

Before running checks, verify the development environment is ready:

```bash
# Check if node_modules exists
ls node_modules/.bin/eslint && ls node_modules/.bin/tsc
```

**If tools are NOT available:**
- Run `npm install` to install dependencies
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
- `package.json` - Scripts and dependencies
- `.eslintrc.*` or `eslint.config.js` - Linting configuration
- `tsconfig.json` - TypeScript configuration

---

## SECTION 4: Run Code Quality Checks

Run the quality commands defined in Section 1. Execute in this order:

### 4.1 Linting
```bash
# Run ESLint to find errors
npm run lint

# Or directly:
npx eslint . --ext .ts,.tsx,.js,.jsx
```

### 4.2 Formatting
```bash
# Auto-format code with Prettier
npm run format

# Or directly:
npx prettier --write .
```

### 4.3 Type Checking
```bash
# Run TypeScript compiler for type checking
npm run typecheck

# Or directly:
npx tsc --noEmit
```

### 4.4 Dead Code Detection

Scan for unused code before proceeding:

```bash
# Check for unused variables with ESLint
npx eslint . --rule 'no-unused-vars: error' --rule '@typescript-eslint/no-unused-vars: error'
```

**Interpreting results:**
- `no-unused-vars`: Remove unused variables or prefix with `_`
- `@typescript-eslint/no-unused-vars`: Same for TypeScript-specific cases
- Unused imports: Remove the import statement

---

## SECTION 5: Fix Errors

### Auto-fixable errors

```bash
# Auto-fix ESLint issues
npm run lint -- --fix

# Or directly:
npx eslint . --fix

# Format with Prettier
npx prettier --write .
```

### Manual fixes

| Error Type | Fix |
|------------|-----|
| Missing imports | Add the required import statement |
| Type mismatches | Check interface/type definitions, fix types |
| Unused variables | Remove or prefix with `_unusedVar` |
| Unused imports | Remove the import |
| Missing type annotations | Add explicit types to function parameters/returns |

### Common ESLint rules

| Rule | Description |
|------|-------------|
| no-unused-vars | Disallow unused variables |
| no-console | Disallow console statements |
| prefer-const | Prefer const over let |
| @typescript-eslint/no-explicit-any | Disallow `any` type |
| @typescript-eslint/explicit-function-return-type | Require return types |

---

## SECTION 6: Verify All Checks Pass

After fixing errors, re-run the full quality check:

```bash
npm run lint && npm run typecheck
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
npm test
```

**For watch mode:**
```bash
npm test -- --watch
```

**For coverage:**
```bash
npm test -- --coverage
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
  - ESLint: No errors
  - Prettier: Formatted
  - TypeScript: No type errors
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

### package.json scripts
```json
{
  "scripts": {
    "lint": "eslint . --ext .ts,.tsx,.js,.jsx",
    "lint:fix": "eslint . --ext .ts,.tsx,.js,.jsx --fix",
    "format": "prettier --write .",
    "typecheck": "tsc --noEmit",
    "test": "jest"
  }
}
```

### .eslintrc.js
```javascript
module.exports = {
  parser: '@typescript-eslint/parser',
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'prettier'
  ],
  rules: {
    'no-unused-vars': 'off',
    '@typescript-eslint/no-unused-vars': 'error'
  }
};
```

### tsconfig.json
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules"]
}
```
