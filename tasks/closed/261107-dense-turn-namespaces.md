Filed as: 261107-dense-turn-namespaces
FKA:
AKA: turn namespaces; dense turn indexing; human user turn detection; role partitioned turn handles
Legacy index:

keywords: transcript, turn-id, handle, telemetry, progression, namespaces, config, historical

Parent: `260825-visible-transcript-turn-ids`
Related: `261106-assistant-turn-handle-progression`; `261105-user-turn-and-result-telemetry-decorations`; `docs/notes/2026-10-04-transcript-decorators.md`

# Configurable Turn Namespaces and Dense Turn Progression

## Intent

Eliminate sparse gaps in transcript turn handle allocation by ensuring only
actual turns (and not intermediate tool result blocks or result containers)
consume turn names from the ordered handle namespace, and introduce
configuration allowing user turns and assistant turns to be drawn from
either a shared dense progression or distinct role namespaces.

## Context & Motivation

Visible turn telemetry (`## TOAS:ASSISTANT [alpha ...]`, `## TOAS:USER [bravo ...]`)
enables human operators and tooling to identify and cite turns cleanly. Tool
result blocks already receive hierarchical provenance IDs derived from their
parent assistant turn (e.g. `[india.p1.o1 ...]`, `[india.p1.o2 ...]`).

However, in multi-turn execution with tools, the turn index previously advanced
for *every* entry in `plan.history` or `events.jsonl`, including result nodes and
structural `## TOAS:USER` result containers. In practice, this caused assistant
turns to skip letters sparsely across the alphabet:

```text
## TOAS:ASSISTANT [india ...]
  ## RESULT [india.p1.o1 ...]  <-- consumed index 10 (juliet lost)
  ## RESULT [india.p1.o2 ...]  <-- consumed index 11 (kilo lost)
## TOAS:ASSISTANT [lima ...]
  ## RESULT [lima.p1.o1 ...]   <-- consumed index 13 (mike lost)
## TOAS:ASSISTANT [november ...]
```

Furthermore:
1. `is_human_user_turn` currently splits on `## RESULT` and inspects only the
   preceding block (`blocks[0]`), falsely dropping human user content placed after
   or outside of result fences.
2. Operators may want distinct namespace schemes for user turns (e.g. numeric
   `u1`, `u2`, ...) and assistant turns (e.g. NATO phonetic `alpha`, `bravo`, ...).

## In Scope

1. **Robust Human User Content Detection (`is_human_user_turn`)**:
   - Inspect the entire turn content outside of machine result blocks and fences.
   - Any substantive non-whitespace text before, between, or after result blocks/fences
     identifies a substantive human user turn.
   - Only pure machine result containers evaluate to `False`.

2. **Dense Actual-Turn Indexing**:
   - Define an actual turn filter (`is_actual_turn`):
     - `role == "assistant"`
     - `role == "user"` where `is_human_user_turn(node)` is `True`
     - `role in {"state", "state-diff"}`
     - Excludes `role == "result"` and result-only user containers.
   - Allocation counts only actual turns, ensuring unbroken progressions.

3. **Configurable Turn Namespaces (`SessionPolicy`)**:
   - `session.turn_namespace_mode`: `"shared_dense"` (default) or `"role_partitioned"`.
   - `session.turn_user_namespace`: `"numeric"` (e.g. `u1`, `u2`) or `"nato"`.
   - `session.turn_assistant_namespace`: `"nato"` (default) or `"numeric"` (e.g. `a1`, `a2`).
   - Dotted `/config set session.turn_namespace_mode ...` support in `config_parsing.py`.

4. **Namespace Handle Allocator (`allocate_turn_handle`)**:
   - Support `"nato"` (phonetic alphabet with `-2`, `-3` rollover).
   - Support `"numeric"` (`u1`, `u2`, ... / `a1`, `a2`, ...).

5. **Runtime Wiring & LCP / Selection Parity**:
   - Update `step_generation_runtime.py` and `step_runtime.py` to use the dense counter.
   - Verify `toas head <handle>` and reference lookups in `graph.py` resolve correctly.

## Out of Scope

- Changing canonical event storage (`events.jsonl`) IDs (`evt_...`).
- Modifying result hierarchical naming (`parent.p#.o#`).

## Acceptance Criteria

1. **Dense Shared Progression (Default)**: In multi-turn tool sessions, tool result
   blocks do not increment the turn counter; assistant turns progress contiguously
   (e.g. `india` -> results -> `juliet` -> results -> `kilo`).
2. **Human Content with Results Preserved**: A user turn containing a `## RESULT`
   block alongside substantive user prose (whether before, after, or outside fences)
   is identified as an actual human user turn and assigned a turn handle.
3. **Pure Result Containers Omitted**: A turn containing only machine result markers,
   status lines, fences, and truncation footers does not consume a turn handle.
4. **Role-Partitioned Namespaces**: When configured with `turn_namespace_mode = "role_partitioned"`:
   - User turns receive handles from `turn_user_namespace` (e.g. `u1`, `u2`).
   - Assistant turns receive handles from `turn_assistant_namespace` (e.g. `alpha`, `bravo`).
5. **Configurability**: `session.turn_namespace_mode`, `session.turn_user_namespace`,
   and `session.turn_assistant_namespace` can be inspected and updated via `/config set`.
6. **Verification & Coverage**: Passes `./scripts/check.sh` with 100.00% statement coverage.

## Implementation Plan

1. **Phase 1: Robust Human Turn Detection & Namespace Allocator**
   - Refactor `is_human_user_turn` to parse machine result fences and preserve human content outside fences.
   - Extend `allocate_turn_handle` with `namespace` and `role` parameters supporting `"nato"` and `"numeric"`.
   - Unit tests in `tests/test_turn_telemetry.py`.

2. **Phase 2: Configuration Policy**
   - Add `turn_namespace_mode`, `turn_user_namespace`, `turn_assistant_namespace` to `SessionPolicy` in `src/toas/config.py`.
   - Register validation and choices in `src/toas/config_parsing.py`.
   - Unit tests in `tests/test_config.py`.

3. **Phase 3: Dense Actual-Turn Counting in Runtimes**
   - Implement `count_actual_turns(history, role=None, mode="shared_dense")`.
   - Wire into `step_generation_runtime.py` for assistant turns and `step_runtime.py` for user turns.
   - Update `graph.py` fallback handle resolution.

4. **Phase 4: TDD & Operator Verification**
   - Multi-turn test with tool calls asserting dense progression (`india` -> `juliet` -> `kilo`).
   - Test human commentary after result block receiving handle.
   - Test `role_partitioned` mode (`u1`, `u2` alongside `alpha`, `bravo`).
   - Verify 100.00% statement coverage via `./scripts/check.sh`.

## Verification & Closure

- **Dense shared turn progression verified**: Multi-turn tool session test `test_run_step_multi_turn_dense_shared_with_tool_results_not_sparse` confirms that tool result blocks do not consume handles from the progression; assistant turns progress contiguously (`alpha` user -> `bravo` assistant [tool request] -> `bravo.p1.o1` result -> `charlie` assistant -> `delta` user -> `echo` assistant).
- **Human commentary with results preserved**: `extract_human_user_content` and `test_run_step_user_turn_with_result_and_commentary_gets_handle` verify that human prose positioned before, after, or outside of result code fences is recognized as human content and allocated turn handles.
- **Role-partitioned namespaces verified**: `test_run_step_role_partitioned_namespaces` validates that `turn_namespace_mode="role_partitioned"` assigns independent namespaces (e.g. `u1`, `u2` for user turns; `alpha`, `bravo` for assistant turns).
- **Full test suite pass**: `./scripts/check.sh` succeeded across 3,864 unit tests, 17 acceptance tests, mypy, and ruff, maintaining 100.00% statement coverage (25,937 / 25,937 statements).
