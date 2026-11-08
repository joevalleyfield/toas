Filed as: 261106-bounded-step-quiescence
FKA:
AKA: step n; bounded multi-step; step quiescence; autonomous turn loop; step count
Legacy index:

keywords: runtime, operator, stepping, loop, subagents, orchestration, quiescence, closed

Related: `260509-multi-operator-orchestration`; `260626-transcript-parallelism-design-pressures`

# Bounded Multi-Turn Stepping with Quiescence Termination

## Intent

Introduce bounded multi-turn stepping (`/step [n]`, `toas step [n]`, and RPC
`step(max_turns=n)`) that advances consequence layers sequentially until either
reaching $n$ turns or encountering an assistant turn with no executable content
(quiescence), enabling autonomous short-horizon tasking and subagent delegation
without violating TOAS durable history invariants.

## Context & Motivation

TOAS explicitly rejects hidden loops: `toas step` accepts transcript state,
synchronizes it into history, and resolves one layer of consequence.

While single-step granularity is ideal for an interactive operator pairing in
real-time, it creates friction when delegating bounded work to subagents,
parallel task lanes, or background scratch workspaces (as explored in
`260509-multi-operator-orchestration` / 488). An external driver or subagent
currently requires an external supervisor repeatedly invoking `toas step`
after every tool call.

External shell loops (e.g. `while ...; toas step; done`) are fragile:
1. They lack semantic stopping awareness and cannot tell whether the assistant
   is actively requesting tools, waiting for operator clarification, or done.
2. They risk runaway execution and token burn if not tightly bounded.
3. They introduce redundant CLI startup overhead per turn.

The natural stopping condition is **quiescence**: an assistant turn that has
completed without emitting any executable content. When the assistant emits
pure text (an explanation, an answer, a question, or a completion statement)
without tool calls, it has yielded back to the operator.

## In Scope

- **Bounded Turn Driver**:
  - Support specifying an upper bound $n \ge 1$ for consecutive consequence turns.
  - Default $n=1$ preserves existing single-step behavior unconditionally.
- **Quiescence Detection**:
  - Identify whether an assistant turn contains executable content:
    - Tool requests / CALL blocks (e.g. ````tool_request ... ```` or `CALL` blocks).
    - Model-generated or user-staged shell commands (`$ ...`).
    - Staged control / slash commands.
  - If no executable content is present on an assistant turn, halt immediately
    regardless of remaining turn budget.
- **CLI & Dispatch Surface**:
  - `toas step [N]` (positional count) or `toas step -n <N>` / `--count <N>`.
  - Report total turns executed and stopping reason (e.g. `quiescent`,
    `turn_limit_reached`, `error`).
- **Transcript Slash Command / Control**:
  - `/step [N]` (defaults to `1` when $N$ is omitted).
- **RPC & Daemon Interface**:
  - Extend the `step` request schema with optional `max_turns: int = 1`.
- **Durable History Invariants**:
  - Every turn must record canonical durable events to `events.jsonl`.
  - Every turn must project cleanly to the transcript surface.
  - No batching or flattening that elides intermediate tool requests/results
    from durable history.
- **Early Exit on Error**:
  - Halt stepping if a tool call fails (unless `continue_on_error` is active)
    or if LLM generation fails.

## Out of Scope

- Unbounded / infinite daemon execution loops without safety caps.
- Autonomous multi-agent blackboard coordination (this task provides the
  single-lane execution primitive).
- Modifying prompt templates or tool schemas.

## Proposed Design & Semantics

### In-Memory Transcript Continuity & Turn Boundary Flushing

1. **In-Flight Accumulator**:
   The multi-step runner maintains an in-memory transcript accumulator across
   iterations. Each consequence step's projection is appended to this in-flight
   view so subsequent iterations see updated frontier context even when stdout is
   not redirected back into `session.md`.
2. **Turn Boundary Flushing**:
   Each consequence step flushes its projection chunk to stdout as it completes,
   preserving live streaming and compatibility with `toas step >> session.md`.
3. **Precedence Contract**:
   Explicit CLI counts (`toas step [n]`, `toas step -n <n>`, `--count <n>`) take
   unconditional precedence over transcript directives. When CLI count is omitted
   (bare `toas step`), a frontier `/step [n]` directive sets the turn budget to $n$.
4. **Directive Semantics**:
   A `/step [n]` directive (in `CONTROL` or `USER`) does not consume a consequence
   turn itself; it configures the turn budget for the subsequent consequence sequence.

### Stepping Loop Logic

```python
turns_executed = 0
while turns_executed < max_turns:
    outcome = step_once(...)  # or step_state_once(...)
    turns_executed += 1
    
    # Flush output at turn boundary
    flush_turn_output()
    
    # Check for errors
    if not outcome.completed or outcome.error:
        break
        
    # Check for quiescence
    if outcome.quiescent:
        # Assistant produced pure text; yielded to operator
        break
```

### Stopping Reasons

1. `quiescent`: Assistant produced a turn with no executable content (natural yield).
2. `turn_limit`: Reached $n$ turns while executable content was still pending.
3. `error`: Halted on execution or model error.
4. `interrupted`: Operator cancelled execution.

## Acceptance Criteria

1. [x] **Default Preservation**: `toas step` (with no arguments and no `/step` directive)
   behaves identically to the current single-step implementation.
2. [x] **Quiescent Early Stop**: In a multi-step call (`toas step 5`), if the assistant
   returns a text-only turn on turn 1, the loop stops immediately after turn 1.
3. [x] **Multi-Turn Chaining**: If the assistant requests a tool on turn 1, the tool
   executes on turn 2, and the assistant responds with final text on turn 3,
   `toas step 5` executes exactly 3 turns and terminates cleanly with `quiescent`.
4. [x] **Safety Cap**: If the assistant repeatedly requests tools on every turn,
   `toas step 3` halts after turn 3 with `turn_limit` status.
5. [x] **Durable Parity**: The resulting `events.jsonl` contains the exact same
   sequence of events as if the operator had manually executed `toas step` $k$ times.
6. [x] **Slash Command & CLI Parity**: `/step 3` in session transcript or via `--control`
   sets the turn budget to 3 when no explicit CLI count is provided, exhibiting
   identical stopping behavior.
7. [x] **In-Flight Transcript Parity**: Multi-stepping advances properly and chains
   consecutive turns even when `toas step` is invoked without shell redirection.

## Resolution & Verification

- Added `step_bounded(max_turns, ...)` and updated `step_once` in `src/toas/operator_api.py`.
- Added in-memory accumulator and turn-boundary stdout flushing (`sys.stdout.flush()`) in `src/toas/cli_session_commands.py`.
- Extended CLI parsing in `src/toas/cli_dispatch_ops.py` and `src/toas/cli.py` for `toas step [N]`, `-n`, `--count`, `--max-turns`.
- Registered `/step [N]` slash command and control handler.
- All 3,816 tests pass with 100.00% statement coverage across all 161 project modules.
- End-to-end CLI inspection verified against `toas step --help` and integration scenarios.
