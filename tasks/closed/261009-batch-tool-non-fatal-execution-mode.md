# Batch Tool Try-All and Non-Fatal Execution Mode

Filed as: 261009-batch-tool-non-fatal-execution-mode
FKA:
AKA: batch tool continue on error; non-fatal exploratory tool execution; batch try all; tool sequence error disposition
Legacy index:

keywords: tools, runtime, batch, execution, error-disposition, exploration

Parent: `260926-state-step-requirements`
Related: `261009-read-file-eof-truncation-and-soft-bounds`

Status: CLOSED; implemented batch tool continue_on_error mode across runtime, protocol, and projection

## Context

In state-step session runs (`session-20261007-1946-state-seed.md`, Turn 3), the model proposed a speculative reconnaissance batch:
```yaml
pending_tools:
- tool_name: shell
  args: {argv: ["ls", "-la"]}
- tool_name: read_file
  args: {path: "tasks.txt"}
- tool_name: read_file
  args: {path: "TODO.md"}
- tool_name: read_file
  args: {path: "todo.md"}
```
Because `tasks.txt` did not exist, `read_file` raised an error. The runtime (`execute_plan_calls` in `src/toas/tools_cluster/execution.py`) broke out of the execution loop immediately upon the first failure, dropping the remaining two `read_file` calls entirely.

While fail-fast is desirable for sequential dependency chains (acting as an ad-hoc script where step 2 relies on step 1), it penalizes independent or speculative reconnaissance batches. However, solving this must avoid causing instruction fatigue in the model through verbose per-call boilerplate.

## Objectives

1. **Design Low-Friction Batch Error Disposition**:
   - Provide a mechanism for exploratory batches to execute all calls, recording individual outcomes (success or failure) without cascading aborts.
   - Keep the model-facing affordance lightweight to prevent instruction fatigue (e.g. turn-level mode or clear, concise tool call flag).
2. **Runtime Execution Integration**:
   - Update `execute_plan_calls` to support continuing past raised or returned tool errors when non-fatal disposition is requested.
   - Ensure stdout / RESULT formatting projects individual failure messages alongside successes for all executed tools in the batch.
3. **Protocol and Prompt Alignment**:
   - Document the affordance in state protocol instructions.
4. **Validation and Coverage**:
   - Add unit tests for non-fatal batch execution across raised and returned failures.
   - Maintain 100.00% statement coverage.

## Outcome

- Added low-friction `continue_on_error: bool = False` support to `execute_plan_calls` in `src/toas/tools_cluster/execution.py`, accepting both batch-level disposition and per-call overrides across raised exceptions (`TimeoutError`, `ConnectionError`, `ChildProcessError`, `RuntimeError`, generic `Exception`) and returned failures (`ok: False`).
- Threaded `continue_on_error` through `execute_plan` (`src/toas/tools.py`), `_execute_plan` (`src/toas/step.py`), `step_state` (`src/toas/runtime/state_step.py`), `step_state_once` (`src/toas/operator_api.py`), and CLI session runner (`src/toas/cli_session_commands.py`).
- Updated `default_protocol()["schema"]` to accept optional `continue_on_error: "boolean (optional)"` at the batch level.
- Updated `parse_state_turn` and `render_state_turn` to parse, validate, and serialize `continue_on_error`.
- Updated state prompt instructions (`src/toas/assets/prompts/state/instructions_v1.txt`) to concisely document `continue_on_error: true` for speculative or exploratory batches without causing model instruction fatigue.
- Verified stdout and RESULT projections in session runner project both success blocks and failed outcome lines for non-fatal batches.
- Added comprehensive unit tests in `tests/test_tools_execution.py`, `tests/test_tools.py`, `tests/test_step.py`, `tests/test_state_step.py`, and `tests/test_cli_session_commands_state_step.py`.
- Conducted operator-perspective end-to-end artifact inspection (`toas prompt state/instructions_v1`).
- Passed full test suite and check script (`./scripts/check.sh`) at 100.00% statement coverage.
