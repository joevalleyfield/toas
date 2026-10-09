# Batch Tool Try-All and Non-Fatal Execution Mode

Filed as: 261009-batch-tool-non-fatal-execution-mode
FKA:
AKA: batch tool continue on error; non-fatal exploratory tool execution; batch try all; tool sequence error disposition
Legacy index:

keywords: tools, runtime, batch, execution, error-disposition, exploration

Parent: `260926-state-step-requirements`
Related: `261009-read-file-eof-truncation-and-soft-bounds`

Status: OPEN; support non-fatal exploratory batch tool execution without model instruction fatigue

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
