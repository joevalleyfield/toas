Filed as: 261107-bounded-step-context-fallbacks
FKA:
AKA: step n single step fallback; bounded multi-step launch failures; user consequence false quiescence; step count dropped
Legacy index:

keywords: runtime, operator, stepping, loop, cli, rpc, vim, quiescence, active, closed

Related: `261106-bounded-step-quiescence`; `260509-multi-operator-orchestration`

# Multi-Context Bounded Step Launch Fallbacks and False Quiescence

## Intent

Diagnose, triage, and eliminate failure modes where bounded multi-step execution (`toas step [n]`, `/step [n]`, and editor `[count]ToasStep`) unexpectedly terminates or falls back to executing only a single step instead of the requested turn bound $n$.

## Context & Motivation

During interactive operator use, bounded multi-stepping is frequently observed to execute only a single turn and halt, even when several turns remain in the requested budget and executable consequences are actively expected.

Codebase investigation identifies five interacting factors across different invocation contexts:

1. **User / Operator Consequence False Quiescence (Primary Engine Factor)**:
   In `src/toas/cli_session_commands.py`:
   When a turn evaluates user-originated execution—such as user shell shorthand (`$ ls`), `/run ...`, `/shell ...`, or `/stage ...`—the result node has `origin_role == "user"`.
   The runner previously classified this as `quiescent = True`.
   In `src/toas/operator_api.py` (`step_bounded`), `step_bounded` immediately halted after turn 1. When an operator ran `$ cmd` or `/run ...` with `toas step 3`, intending TOAS to execute the command on turn 1 and let the assistant analyze the result on turn 2, the loop aborted as "quiescent" after 1 step.

2. **CLI `step --async` Drops Count / Max Turns**:
   In `src/toas/cli_dispatch_ops.py`, `parse_step_async_options` parsed only `--session` and `--surface`. Any positional count or `-n/--count/--max-turns` argument was rejected or dropped. Furthermore, `run_step_async` in `cli_async_commands.py` did not accept or pass `max_turns` in its payload.

3. **CLI Options Route Around RPC**:
   In `src/toas/cli.py` (`run_step`):
   Whenever `max_turns` was passed on the CLI, `run_step` immediately bypassed the daemon RPC transport (`_rpc_stdout`) and forced synchronous local execution, ignoring active daemon state.

4. **Frontier Extraction Role Constraint**:
   `extract_frontier_step_directive` in `step_context_runtime.py` strictly required `frontier["role"] in {"user", "control"}`.
   If `/step [n]` was written at the transcript tail following an assistant turn (such as after an assistant question or tool failure without an explicit `## TOAS:USER` turn header), the directive was not recognized, falling back to 1.

5. **Editor / Vim Transport Timeouts & Non-Count Bindings**:
   In `vim/plugin/toas.vim`:
   - `s:toas_step_rpc` had a hardcoded 5.0s timeout (`s:toas_request('step', l:payload, 5.0)`). Multi-turn steps almost always exceeded 5 seconds, triggering timeout exceptions and cascading into fallback lanes.
   - `ToasStepAsync` did not bind or accept a count.

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

## Acceptance Criteria

1. **User Consequence Quiescence Correction**: When a bounded stepping turn produces a `result` node (regardless of whether `origin_role` is assistant or user), the turn is marked non-quiescent (`quiescent = False`), allowing subsequent turns in the budget to proceed to assistant evaluation. Pure assistant text turns without tool calls remain naturally quiescent.
2. **CLI Async Count Forwarding**: `toas step --async [N]`, `-n <N>`, `--count <N>`, and `--max-turns <N>` are recognized by the CLI parser, dispatched, and forward `max_turns` in the async step start payload across local and RPC backends.
3. **CLI RPC Dispatch Alignment**: Invoking `toas step [N]` with only turn-bound arguments forwards to the daemon RPC path (`_rpc_stdout("step", {"max_turns": N})`) when daemon RPC is available (`auto` or `on`), falling back to local execution on RPC failure or when `off`.
4. **Tail Directive Extraction**: `/step [N]` written at the tail of the transcript (e.g. following an assistant turn or tool result without an explicit `## TOAS:USER` turn header, or on a raw transcript) correctly extracts the bound $N$ and strips the directive from the frontier text.
5. **Vim Transport Timeouts & Async Count**: `s:toas_step_rpc` dynamically scales RPC request timeout based on turn count (`l:count * base_timeout`) with configurable `g:toas_step_timeout_s`, and `ToasStepAsync` accepts optional count argument and command prefix.
6. **Coverage & Checks**: Suite passes `./scripts/check.sh` with 100.00% statement coverage.

## Outcome & Evidence

- **User Consequence Quiescence Fix**:
  In `src/toas/cli_session_commands.py`, eliminated false quiescence on result nodes (`last_node.get("role") == "result"` now unconditionally sets `quiescent = False`). User shell shorthand (`$ cmd`) and `/run` executions now allow the assistant to analyze the results on turn 2 within the bounded budget.
- **CLI Async Count Support**:
  - In `src/toas/cli_usage.py`, updated `STEP_ASYNC_USAGE` to document `[N] [-n <N>|--count <N>|--max-turns <N>]`.
  - In `src/toas/cli_dispatch_ops.py`, updated `parse_step_async_options` to parse positional and option-based turn counts into `max_turns`.
  - In `src/toas/cli_dispatch.py`, forwarded `max_turns` from `parse_step_async_options` to `deps.run_step_async`.
  - In `src/toas/cli.py` and `src/toas/cli_async_commands.py`, updated `run_step_async` signatures to accept and include `max_turns` in the execution payload.
- **RPC Dispatch Alignment**:
  In `src/toas/cli.py` (`run_step`), aligned RPC routing so passing `max_turns` without local-only options (`--preview`, `--stdin`, `--control`, custom `--session`/`--surface`) dispatches via `_rpc_stdout("step", {"max_turns": max_turns})` rather than bypassing the daemon.
- **Transcript Directive Extraction**:
  In `src/toas/runtime/step_context_runtime.py` (`extract_frontier_step_directive`), hardened extraction to recognize `/step [n]` at the transcript tail across non-user/non-control turns (assistant, result) and headerless transcript inputs, stripping the tail directive and returning the extracted count.
- **Vim Timeouts and Async Count**:
  In `vim/plugin/toas.vim`, added `g:toas_step_timeout_s = 30.0` default, scaled `s:toas_step_rpc` timeout proportionally to requested turns (`l:count > 1 ? l:base_timeout * l:count : l:base_timeout`), updated `ToasStepAsync` to accept an optional count argument, and bound `command! -count=0 -nargs=? ToasStepAsync`.
- **Targeted Tests & Verification**:
  Added comprehensive tests in `tests/test_bounded_step.py`, `tests/test_cli.py`, `tests/test_cli_dispatch.py`, `tests/test_cli_dispatch_ops.py`, and `tests/test_cli_async_commands.py`.
- **Suite & Coverage**:
  Passed `./scripts/check.sh` with 3,908 tests passing, 0 failures, 100.00% statement coverage, and zero MyPy issues across 164 source files.
