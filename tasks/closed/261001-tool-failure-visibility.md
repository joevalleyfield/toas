Filed as: 261001-tool-failure-visibility
FKA:
AKA: tool error visibility; unmask tool errors; tool failure provenance; error bubbling
Legacy index:

keywords: tooling, runtime, active, correctness, usability, provenance, projection

Parent: `260926-state-step-requirements`
Related: `260930-paged-inert-tool-spillover`; `260927-state-step-response-shapes`

# Tool Failure Visibility And Error Bubbling

Ensure tool execution failures bubble up with the exact source, offending target, tool name, and full error description before deciding on graceful degradation policies.

## Context

In `.toas/session-20261001-1859-bounded-reads-state.md`, a state-step execution failed with:

```text
## RESULT

[FAILED] tool 0: invalid syntax (<unknown>, line 3)
```

This error concealed critical diagnostic information across multiple layers:
1. **Parser anonymity**: `collect_python_structure` called `ast.parse(content)` without passing `filename=str(path)`, causing Python to report `<unknown>` instead of the offending file path.
2. **Context loss during traversal**: Directory traversals (e.g., `run_get_structure` scanning `.`) let exceptions escape without attaching which candidate file caused the failure.
3. **Anonymous batch execution outcomes**: `step_state` in `state_step.py` caught tool exceptions and recorded only `{"index": index, "status": "failed", "error": str(exc), "source": call_source}`, discarding the tool name, arguments, and exception class.
4. **Opaque CLI outcome rendering**: `cli_session_commands.py` rendered `[FAILED] tool {idx}: {summary}` without the tool name (`get_structure`) or target arguments (`path: .`), making it impossible for the operator or model to discern what ran or where it choked.
5. **Missing execution stack trace**: When tools crash with unexpected exceptions, tracebacks are discarded without logging to `.toas/error.log` or persisting in event records, leaving operators with no post-mortem visibility into the execution failure path.

Before implementing graceful recovery (such as skipping unparseable files or ignoring virtualenv trees), tool errors must bubble up cleanly and transparently so failures are immediately intelligible.

## Desired Reality

1. **Explicit Source in Parsers**:
   - `ast.parse` calls in tool implementations provide `filename=str(path)` (or relative workspace path), ensuring syntax errors identify the file.
   - Exceptions during file processing (syntax errors, decode errors, IO errors) retain or wrap the specific file path being operated on.

2. **Rich Tool Outcome Records**:
   - Batch tool execution outcomes and `state_tool_result` event records preserve `tool_name`, relevant arguments/target, and structured error details (exception type, message).

3. **Informative Failure Projections**:
   - Failure outcome lines and result projections in transcripts explicitly display the tool name, index, and full error description (e.g. `[FAILED] tool 0 (get_structure): SyntaxError: invalid syntax (.venv/.../count_symbols_py2.py, line 3)`).

4. **Stack Trace Accessibility and Logging**:
   - Tool execution crashes capture full TOAS stack traces and write them to `.toas/error.log` (and/or structured event metadata), ensuring complete post-mortem diagnostics are accessible even if suppressed from the compact UI outcome lines.

5. **Clean Diagnostic Foundation**:
   - Both operators and inference models receive actionable error descriptions in their observations rather than opaque `<unknown>` messages.

## Acceptance Criteria

- `collect_python_structure` and related AST utilities pass the file path to `ast.parse`, surfacing the exact file in syntax error messages.
- Tool failure outcomes in `state_step.py` retain `tool_name` alongside `index`, `status`, and `error`.
- Outcome rendering in `cli_session_commands.py` outputs tool name and clear diagnostic detail for failed tools.
- Unexpected tool execution exceptions log the full TOAS stack trace to `.toas/error.log` (and preserve traceback detail in event/outcome records).
- Unit tests verify that syntax errors and unhandled tool exceptions in batch execution surface the tool name, target path, error details, and accessible tracebacks without concealment.
- Full test suite passes without regressions.

## Completion Log

- **2026-10-01**: Implemented tool failure visibility and error bubbling:
  - Updated `collect_python_structure` (`src/toas/tools_cluster/basic_ops.py`) and `collect_code_survey_entries` (`src/toas/tools_cluster/survey_ops.py`) to pass `filename=str(path)` to `ast.parse` and wrap `SyntaxError` and `(UnicodeDecodeError, OSError)` so the offending file path and line number are surfaced directly in error messages instead of `<unknown>`.
  - Added optional `tool_name` and `traceback` attributes to `ToolOutcomeError` in `src/toas/runtime/state_step.py`.
  - Added `_log_tool_failure` logging to `.toas/error.log` in `src/toas/runtime/state_step.py` for both batch tool execution and user tool execution loops, persisting `tool_name` and `traceback` on outcome dictionaries and durable `state_tool_result` event records.
  - Enhanced tool execution in `src/toas/tools_cluster/execution.py` to capture unexpected tool exceptions with full tracebacks.
  - Updated CLI outcome rendering in `src/toas/cli_session_commands.py` to format failure lines as `[FAILED] tool {idx} ({tool_name}): {summary}` and render failure lines even alongside partial successful results.
  - Added comprehensive test coverage in `tests/test_tools_basic_ops.py`, `tests/test_state_step.py`, `tests/test_cli_session_commands_state_step.py`, and `tests/test_tools_execution.py`.
  - Verified 100% targeted coverage on affected modules and clean `ruff` and `mypy` checks.

