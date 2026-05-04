# 475 Expanded Edit-Mode Guidance And Indent-Safe Replacement Rules

## Objective
Add an expanded guidance profile that is activated for edit-heavy phases, including explicit indentation rules for block replacement shapes.

## Why
- Compact startup guidance is good for first-turn usability.
- Edit-mode needs deeper, precise rules (especially indentation-sensitive replacement) to avoid malformed operations.

## Scope
In scope:
- Define expanded edit-mode guidance content.
- Include explicit rules for YAML literal indentation markers (`|2`, `|4`, etc.).
- Include explicit guidance for search-indent controls when parent indentation obscures intent.
- Add tests for guidance rendering and inclusion triggers.

Out of scope:
- Bootstrap seeding mechanism and base shared tools guidance source (covered by task 474).

## Tracking
- Status: completed
- Opened: 2026-05-03
- Completed: 2026-05-04
- Notes:
  - Expanded `tools-guidance-full` with edit-mode replacement rules.
  - Added explicit YAML literal indent marker guidance (`|2`, `|4`) and `search_indent` usage rules.
  - Included explicit note that `intent`/`intention` is optional callable metadata in operation shape.
  - Added coverage in `tests/test_prompts.py` for new guidance text.
