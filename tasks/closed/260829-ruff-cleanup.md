Filed as: 260829-ruff-cleanup
FKA:
AKA: lint cleanup; ruff check cleanup; import formatting
Legacy index:

keywords: tooling, implementation, active, maintainability, coverage

# Ruff Cleanup

Restore a clean `ruff check src tests` result after the repository check
reported import-formatting, style, and unused-variable violations.

## Acceptance Criteria

- [x] `ruff check src tests` passes.
- [x] Focused tests for touched runtime and Vim helper files pass.

Claimed for implementation on 2026-08-29: apply the reported Ruff fixes and
verify the lint and focused test surfaces.

## Implementation Evidence

- Applied Ruff's 14 safe import/style fixes and removed the unused
  `chunk_text` test assignment.
- `ruff check src tests`: clean.
- Focused tests: 9 passed, 210 deselected.
- Mypy was run after Ruff cleared and remains blocked by 12 existing typing
  errors in `src/toas/llm.py` and `src/toas/prompts.py`; no lint change caused
  those errors.

## Closure

Closed after restoring a clean repository Ruff check and verifying the touched
test surfaces.
