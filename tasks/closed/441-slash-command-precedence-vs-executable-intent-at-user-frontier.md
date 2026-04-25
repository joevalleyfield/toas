## Summary
Slash commands can be ignored when executable intent is also present in the same user-frontier message.

## Why This Matters
User intent should be deterministic and explicit. When a user includes a slash command (for example `/extract` or `/replay`) in a turn, that operator command should not be silently bypassed because callable/executable content was also detected.

## Reproduction Shape
1. Construct a user frontier message that contains both:
   - callable executable intent (for example a YAML tool plan or shell shorthand), and
   - a trailing slash command.
2. Run `toas step`.
3. Observe executable path execution (`tool_request`/`tool_result`-like consequence path) while slash command handling is skipped.

## Recon Notes
- Current consequence routing in `src/toas/runtime/step_runtime.py` evaluates `plan` before `operator_command`:
  - `if ... plan is not None: ...`
  - `elif frontier["role"] == "user" and operator_command is not None: ...`
- `_collect_frontier_intents(...)` extracts both plan and operator command from the same frontier content.
- Because branch ordering prioritizes plan execution, slash command intent loses precedence whenever both are present.
- Existing tests cover slash command handling and executable intent handling independently, but there is no explicit mixed-frontier precedence contract test for this case.

## Scope
- Define and lock precedence semantics for mixed user-frontier content containing both slash commands and executable intent.
- Add regression tests for at least:
  - tool-plan + trailing slash command
  - shell shorthand + trailing slash command
- Implement behavior so slash command precedence is explicit (or emit deterministic error if mixed content is intentionally disallowed).
- Reuse durable queue semantics from `331` where relevant so multi-intent continuation is observable and controllable, not hidden in one-pass branching.
- Keep this task scoped to immediate regression containment; broader policy/authoring changes stay in `442`/`443`.

## Linkage
- Depends on behavioral precedent from `tasks/closed/331-queued-mixed-authorization-execution-controls.md`:
  - ordered continuation controls
  - durable queue state
  - explicit operator controls (`--resume`, `--approve`, `--skip`, `--cancel`)
- This task addresses immediate precedence regression; broader arbitration policy and intent-order controls are split into follow-on `442`.

## Acceptance
- A failing regression test is added first (or equivalent red-state proof), then behavior is updated.
- Mixed-content precedence is deterministic and documented in tests.
- Full test suite passes after the fix.
- Any queue-backed continuation behavior introduced by this fix follows the durability/visibility bar established in `331`.

## Progress
- 2026-04-24: Implemented precedence fix in `src/toas/runtime/step_runtime.py` so user-frontier slash operator commands execute before callable-plan execution when both are present.
- Added targeted regressions in:
  - `tests/test_runtime_step_runtime.py` (operator branch precedence over plan branch)
  - `tests/test_step.py` (end-to-end mixed user turn with callable YAML + trailing slash command)
- Full suite validation passed (`1033`/`1038` tests depending on branch point) with coverage gate intact.

## Status

Closed 2026-04-24.
