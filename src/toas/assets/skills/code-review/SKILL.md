---
name: code-review
description: Local diff review and verification guidelines.
alias: review
---

# Code Review and Verification Guidelines

Use this skill to review local working copy diffs, enforce verification discipline,
critique operator-facing artifacts, and ensure task continuity before committing.

## Review Workflow

### 1. Inspect Working Copy & Diffs

Always inspect the concrete changes in the working copy:

```bash
# In Jujutsu repositories
jj status
jj diff --git

# In Git repositories
git status
git diff
```

Check:
- Are there unexpected untracked files or unintentional deletions?
- Are code comments, docstrings, and existing license/type annotations preserved?
- Are imports organized and module boundaries respected according to `docs/runtime-ownership.md`?

### 2. Mechanical Verification

Execute the mechanical test and coverage gates:

```bash
# Fast targeted coverage check on changed modules:
uv run python scripts/targeted_coverage.py --cov <module_name> -- tests/<test_file> -q

# Full test suite and lint verification:
./scripts/check.sh
```

Ensure:
- 100.00% statement coverage gate is achieved.
- Ruff and Mypy pass with zero warnings or errors.

### 3. Mandatory End-to-End Artifact Inspection

Do not rely solely on unit tests, synthetic fixtures, or mocks:
- Run concrete user-facing commands directly (e.g., `toas prompt ...`, `toas skills`, `toas step`, transcript projection).
- Inspect the actual stdout/markdown rendered output.

### 4. Adopt the Operator's Perspective

Step into the operator's shoes and critically evaluate the concrete generated artifacts:
- Does this output fulfill the promises made in its instructions, schemas, and docs?
- Is it completely self-describing, or does it leave hidden assumptions or hallucination traps for models and human operators?
- Are contracts and schemas explicit, cohesive, and ergonomically sound?

### 5. Task Continuity & Commit Discipline

- Ensure any repository-modifying work is stitched to an active task file in `tasks/open/`.
- Verify Acceptance Criteria in the task file are met and checked off.
- Format commit descriptions following conventional style:
  `type(scope): summary`
  (e.g., `feat(skills): add standard agent skills discovery and activation`).
