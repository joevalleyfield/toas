Filed as: 261107-bounded-step-context-fallbacks
FKA:
AKA: step n single step fallback; bounded multi-step launch failures; user consequence false quiescence; step count dropped
Legacy index:

keywords: runtime, operator, stepping, loop, cli, rpc, vim, quiescence, active

Related: `261106-bounded-step-quiescence`; `260509-multi-operator-orchestration`

# Multi-Context Bounded Step Launch Fallbacks and False Quiescence

## Intent

Diagnose, triage, and eliminate failure modes where bounded multi-step execution (`toas step [n]`, `/step [n]`, and editor `[count]ToasStep`) unexpectedly terminates or falls back to executing only a single step instead of the requested turn bound $n$.

## Context & Motivation

During interactive operator use, bounded multi-stepping is frequently observed to execute only a single turn and halt, even when several turns remain in the requested budget and executable consequences are actively expected.

Codebase investigation identifies five interacting factors across different invocation contexts:

1. **User / Operator Consequence False Quiescence (Primary Engine Factor)**:
   In `src/toas/cli_session_commands.py` (lines 362–370):
   ```python
   elif last_node.get("role") == "result":
       origin_role = last_node.get("origin_role")
       origin_kind = last_node.get("origin_kind")
       if origin_role == "assistant" or origin_kind == "tool_call":
           quiescent = False
           has_executable = False
       else:
           quiescent = True
           has_executable = False
   ```
   When a turn evaluates user-originated execution—such as user shell shorthand (`$ ls`), `/run ...`, `/shell ...`, or `/stage ...`—the result node has `origin_role == "user"`.
   The runner classifies this as `quiescent = True`.
   In `src/toas/operator_api.py` (`step_bounded`):
   ```python
   if outcome.quiescent:
       return StepOutcome(..., stop_reason="quiescent", turns_executed=turns_executed)
   ```
   `step_bounded` immediately halts after turn 1. When an operator runs `$ cmd` or `/run ...` with `toas step 3`, intending TOAS to execute the command on turn 1 and let the assistant analyze the result on turn 2, the loop aborts as "quiescent" after 1 step.

2. **CLI `step --async` Drops Count / Max Turns**:
   In `src/toas/cli_dispatch_ops.py`, `parse_step_async_options` parses only `--session` and `--surface`. Any positional count or `-n/--count/--max-turns` argument is rejected or dropped. Furthermore, `run_step_async` in `cli_async_commands.py` does not accept or pass `max_turns` in its payload.

3. **CLI Options Route Around RPC**:
   In `src/toas/cli.py` (`run_step`), line 257:
   ```python
   if max_turns is not None or preview or preview_request or preview_response or stdin_mode or control is not None or session_path is not None or surface_id is not None or infer_from is not None:
       return _run_step(**kwargs)
   ```
   Whenever `max_turns` (or any step option) is passed on the CLI, `run_step` immediately bypasses the daemon RPC transport (`_rpc_stdout`) and forces synchronous local execution, ignoring active daemon state.

4. **Frontier Extraction Role Constraint**:
   `extract_frontier_step_directive` in `step_context_runtime.py` strictly requires `frontier["role"] in {"user", "control"}`.
   If `/step [n]` is written at the transcript tail following an assistant turn (such as after an assistant question or tool failure without an explicit `## TOAS:USER` turn header), the directive is not recognized, falling back to 1.

5. **Editor / Vim Transport Timeouts & Non-Count Bindings**:
   In `vim/plugin/toas.vim`:
   - `s:toas_step_rpc` has a hardcoded 5.0s timeout (`s:toas_request('step', l:payload, 5.0)`). Multi-turn steps almost always exceed 5 seconds, triggering timeout exceptions and cascading into fallback lanes.
   - `ToasStepAsync` does not bind or accept a count.

## In Scope

- **Quiescence Model for User Consequences**:
  Re-evaluate quiescence semantics when consequence results originate from user intent: if an operator triggers user shell shorthand or `/run` inside a multi-step session (`toas step n` or `/step n`), determine whether the assistant should be prompted to respond to the consequence on the subsequent step rather than falsely halting as quiescent.
- **CLI Async & RPC Parity**:
  - Enable `toas step --async [n]` to accept and forward `max_turns`.
  - Harmonize CLI RPC dispatch so passing `max_turns` does not needlessly bypass the daemon when running in `TOAS_RPC_MODE=auto` or `on`.
- **Transcript Extraction Robustness**:
  Clarify and harden directive recognition so `/step [n]` at the transcript tail is not dropped when an operator enters it without a preceding `## TOAS:USER` header.
- **Editor / Vim Alignment**:
  Review timeout configuration for bounded RPC steps and ensure editor count prefixes map consistently to all step lanes.

## Out of Scope

- Unbounded stepping loops.
- Altering the fundamental stopping contract for pure assistant text turns (an assistant turn with no tool calls remains the authoritative definition of natural quiescence).
