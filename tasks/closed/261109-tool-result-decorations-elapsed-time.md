Filed as: 261109-tool-result-decorations-elapsed-time
FKA:
AKA: tool result decorations should want to have elapsed time; tool result elapsed time; tool duration telemetry; result marker duration; tool result timestamp; result marker timestamp
Legacy index:

keywords: historical, feature, surface, projection, runtime, usability, contract, transcript, telemetry

Related: `260825-visible-transcript-turn-ids`; `260811-activity-health-telemetry`

# Tool Result Decorations Should Have Elapsed Time and Timestamp

Status: CLOSED (implemented)

## Intent

Tool result decorations should capture and display elapsed execution time and execution timestamp across transcript projections and turn telemetry, aligning with assistant turn decoration parity.

## Context & Motivation

Transcript turn telemetry formatting (`turn_telemetry.py:decorate_result_node` and `format_turn_telemetry`) supports rendering timestamps and elapsed durations in decorations (e.g. compact `[alpha.p1.o1 OK shell 10:18:20 120ms]`, inline `[id=... target=shell t=10:18:20 duration=120ms status=OK]`, or comment styles).

Assistant turns already supply both execution duration and timestamp to `format_turn_telemetry` (`step_generation_runtime.py`), producing rich, informative telemetry headers.

In contrast, tool result nodes during step execution (`step_runtime.py:1800`) only supply `turn_id` and token counts to `decorate_result_node`, omitting both `duration_ms` and `timestamp`. Furthermore, tool execution runners (`execute_plan_calls`, user shell execution) do not consistently record wall-clock duration or completed timestamps on tool result payloads.

In operator workflows, seeing when a tool executed and how long it took provides immediate tactile feedback about tool responsiveness, network/disk latency, and execution cadence directly in the transcript without having to inspect external logs.

## In Scope

- [x] Measure wall-clock elapsed time (`duration_ms`) and record execution timestamp during plan tool execution and user shell shorthand execution.
- [x] Ensure result payloads and decorated result nodes retain `duration_ms` and timestamp metadata.
- [x] Result decoration reads timing fields from the payload, so the existing `step_runtime.py` public decoration call receives them without a duplicate argument path.
- [x] Verify decoration formatting across all telemetry decoration styles (`compact`, `inline`, `comment`) and ensure `off` remains clean and unaffected.
- [x] Add targeted unit and integration tests covering elapsed time and timestamp decoration on tool results while maintaining 100.00% statement coverage.

## Progress Evidence

- Added monotonic wall-clock duration and UTC completion timestamp to `execute_plan_calls` results, including raised failures, and `_execute_user_shell` results.
- `decorate_result_node` now reads the payload timestamp as well as duration and retains both values on the transient result node and its metadata while formatting through the shared telemetry formatter.
- Updated result execution assertions to account for the new fields, and added timestamp checks to compact, inline, and comment result decoration tests. The `off` case still returns its input node unchanged.
- Focused verification passed: 631 tests across step/runtime telemetry and tool execution/rendering coverage sources.
- Full `pytest -q` passed: 4,087 passed, 9 skipped, 17 deselected; 100.00% statement coverage.
- Real CLI inspection verified plan execution and durable result payload timing, and readable timestamp/duration output in all four decoration settings (`compact`, `inline`, `comment`, `off`).
- Bound each loop iteration's start time into its result timing closure to keep lint's loop-variable capture check satisfied.

## Out of Scope

- Modifying model-facing prompt projection (decorations remain transcript/operator-facing).
- Adding background profiling or CPU timing instrumentation beyond wall-clock duration and timestamp.
- Altering canonical message event invariants.

## Acceptance Criteria

1. Tool invocations executed via plan execution measure wall-clock duration and record execution timestamp, attaching both to result payloads/nodes.
2. Result nodes decorated under `session.telemetry_decorations` (`compact`, `inline`, `comment`) reflect elapsed time and timestamp like assistant turns do.
3. All existing and new tests pass with 100.00% statement coverage.
4. End-to-end command/transcript output is verified for readability and ergonomic formatting across all decoration styles.
