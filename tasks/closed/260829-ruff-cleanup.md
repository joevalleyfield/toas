Filed as: 260829-ruff-cleanup
FKA:
AKA: lint cleanup; ruff check cleanup; import formatting
Legacy index:

keywords: tooling, implementation, active, maintainability, coverage

# Ruff and Mypy Cleanup

Restore clean Ruff and mypy results after the repository check reported
import-formatting, style, unused-variable, and typing violations.

## Acceptance Criteria

- [x] `ruff check src tests` passes.
- [x] `mypy` passes.
- [x] Focused tests for touched runtime and Vim helper files pass.

Claimed for implementation on 2026-08-29: apply the reported Ruff and mypy
fixes and verify the static-check and focused test surfaces.

## Implementation Evidence

- Applied Ruff's 14 safe import/style fixes and removed the unused
  `chunk_text` test assignment.
- `ruff check src tests`: clean.
- Narrowed optional prompt assets and the dynamic renderer in `prompts.py`, and
  typed the OpenAI client keyword boundary in `llm.py`.
- `mypy`: success with no issues in 18 source files.
- Focused tests: 9 passed, 210 deselected.
- Covered the renderer validation boundary after the mypy cleanup; targeted
  prompt coverage remains 100%.

## Closure

Closed after restoring clean repository Ruff and mypy checks and verifying the
touched test surfaces.
