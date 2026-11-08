---
name: code-review
description: Local diff review and verification guidelines.
alias: review
---
# Local Code Review Guidelines

Use this skill to perform a structured, end-to-end review of local diffs before committing or closing tasks.

## Review Protocol

### 1. Inspect Exact Changes

Examine the working copy diff against the base commit:
```bash
jj diff --git -r @
```
or with git:
```bash
git diff
```

### 2. Verification Checklist

1. **Invariants & Contracts**:
   - Are public API contracts preserved?
   - Are edge cases handled gracefully without hidden assumptions?
   - Are docstrings and comments accurate and updated?
2. **Mechanical Prerequisites**:
   - Run the project test suite (`uv run pytest` or `./scripts/check.sh`).
   - Check coverage reports (e.g. 100% statement coverage where required).
   - Run linters and type checkers (`ruff check`, `mypy`).
3. **Operator Perspective**:
   - Adopt the operator's shoes: does CLI output, transcript rendering, or error messaging fulfill instructions cleanly?
   - Is output self-describing and free from hallucination traps?
4. **Task Bookkeeping**:
   - Ensure the associated task file in `tasks/` is updated with outcome, evidence, and completed acceptance criteria.
