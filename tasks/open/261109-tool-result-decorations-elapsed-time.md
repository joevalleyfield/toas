Filed as: 261109-tool-result-decorations-elapsed-time
FKA:
AKA: tool result decorations should want to have elapsed time; tool result elapsed time; tool duration telemetry; result marker duration; tool result timestamp; result marker timestamp
Legacy index:

keywords: active, feature, surface, projection, runtime, usability, contract, transcript, telemetry

Related: `260825-visible-transcript-turn-ids`; `260811-activity-health-telemetry`

# Tool Result Decorations Should Have Elapsed Time and Timestamp

## Intent

Tool result decorations should capture and display elapsed execution time and execution timestamp across transcript projections and turn telemetry, aligning with assistant turn decoration parity.

## Context & Motivation

Transcript turn telemetry formatting (`turn_telemetry.py:decorate_result_node` and `format_turn_telemetry`) supports rendering timestamps and elapsed durations in decorations (e.g. compact `[alpha.p1.o1 OK shell 10:18:20 120ms]`, inline `[id=... target=shell t=10:18:20 duration=120ms status=OK]`, or comment styles).

Assistant turns already supply both execution duration and timestamp to `format_turn_telemetry` (`step_generation_runtime.py`), producing rich, informative telemetry headers.

In contrast, tool result nodes during step execution (`step_runtime.py:1800`) only supply `turn_id` and token counts to `decorate_result_node`, omitting both `duration_ms` and `timestamp`. Furthermore, tool execution runners (`execute_plan_calls`, user shell execution) do not consistently record wall-clock duration or completed timestamps on tool result payloads.

In operator workflows, seeing when a tool executed and how long it took provides immediate tactile feedback about tool responsiveness, network/disk latency, and execution cadence directly in the transcript without having to inspect external logs.

## In Scope

- [ ] Measure wall-clock elapsed time (`duration_ms`) and record execution timestamp during tool invocation across tool execution paths (`execute_plan_calls`, user shell shorthand execution, and related tool runners).
- [ ] Ensure result payloads and result nodes retain `duration_ms` and timestamp metadata.
- [ ] Update `step_runtime.py` to supply `duration_ms` and `timestamp` when calling `decorate_result_node`.
- [ ] Verify decoration formatting across all telemetry decoration styles (`compact`, `inline`, `comment`) and ensure `off` remains clean and unaffected.
- [ ] Add targeted unit and integration tests covering elapsed time and timestamp decoration on tool results while maintaining 100.00% statement coverage.

## Out of Scope

- Modifying model-facing prompt projection (decorations remain transcript/operator-facing).
- Adding background profiling or CPU timing instrumentation beyond wall-clock duration and timestamp.
- Altering canonical message event invariants.

## Acceptance Criteria

1. Tool invocations executed via plan execution measure wall-clock duration and record execution timestamp, attaching both to result payloads/nodes.
2. Result nodes decorated under `session.telemetry_decorations` (`compact`, `inline`, `comment`) reflect elapsed time and timestamp like assistant turns do.
3. All existing and new tests pass with 100.00% statement coverage.
4. End-to-end command/transcript output is verified for readability and ergonomic formatting across all decoration styles.
