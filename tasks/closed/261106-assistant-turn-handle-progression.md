Filed as: 261106-assistant-turn-handle-progression
FKA:
AKA: assistant turn progression; working history plumbing; model invocation history; telemetry token progression
Legacy index:

keywords: transcript, turn-id, handle, telemetry, progression, generation, history, working-lineage

Parent: `260825-visible-transcript-turn-ids`
Related: `261104-visible-turn-ids-and-compact-headers`; `261105-user-turn-and-result-telemetry-decorations`; `261106-adaptive-token-estimator`

# Assistant Turn Handle Progression And History Plumbing

## Intent

Ensure assistant turns advance monotonically along the NATO phonetic progression
(`alpha` -> `bravo` -> `charlie` -> `delta` ...) rather than collapsing to `alpha`
on every turn, by plumbing working transcript history through `ResolvedModelInvocation`
into `GenerationRunner.build_artifacts`.

## Motivation

Visible turn handles (`[alpha]`, `[bravo]`, ...) allow operators to identify and cite turns
cleanly in `session.md` using `[[handle]]` syntax.

Currently, [`GenerationRunner.build_artifacts`](src/toas/runtime/step_generation_runtime.py)
attempts to read `history_items = getattr(plan, "history", None) or []` to allocate the turn
handle via `allocate_turn_handle(len(history_items))`. However, `plan` is an instance of
`ResolvedModelInvocation`, which previously did not contain a `history` attribute. Consequently:
1. `history_items` was always empty (`[]`), causing `len(history_items)` to evaluate to `0`.
2. `allocate_turn_handle(0)` assigned `"alpha"` to every generated assistant turn.
3. User turns (which count from durable events in `events.jsonl`) stepped `alpha`, `charlie`, `echo`,
   skipping the slots intended for assistant turns (`bravo`, `delta`, `foxtrot`).
4. Tool result blocks derived from assistant turns inherited the faulty handle (`[alpha.p1.o1 ...]`).
5. Cumulative token estimation on assistant turns failed to accumulate history because `history_items` was empty.

High-level functional testing must verify that multi-turn interactions show proper progression
from the user/operator's perspective.

## Acceptance Criteria

1. Plumb `history: tuple[dict, ...] = ()` into `ResolvedModelInvocation` and pass `tuple(working)` from `resolve_model_invocation` (and events/turns from state-packet generation).
2. Update `GenerationRunner.build_artifacts` to use `plan.history` for both turn handle allocation and cumulative token count calculation.
3. Verify that assistant turns follow the proper phonetic progression across multiple turns (`bravo`, `delta`, `foxtrot`, ...), while user turns take `alpha`, `charlie`, `echo`.
4. Verify that tool results derive correct hierarchical provenance IDs (`bravo.p1.o1`, etc.).
5. Add high-level end-to-end multi-turn tests verifying turn progression and cumulative token accumulation from the operator's perspective.
6. Achieve 100.00% statement coverage under `./scripts/check.sh`.

## Resolution

1. Added `history: tuple[dict, ...] = ()` to `ResolvedModelInvocation` in `src/toas/runtime/model_invocation_contracts.py`.
2. Populated `history=tuple(working)` in `resolve_model_invocation` and plumbed `working` from `prepare_state_request` in `src/toas/runtime/step_generation_runtime.py`.
3. Updated `GenerationRunner.build_artifacts` to safely convert `plan.history` to a list (`history_items = list(getattr(plan, "history", None) or [])`), enabling accurate turn handle allocation (`allocate_turn_handle(len(history_items))`) and multi-turn cumulative token estimation.
4. Added high-level end-to-end multi-turn progression test in `tests/test_runtime_step_runtime.py` verifying full 3-turn sequence:
   - Turn 1: `user [alpha 5 tok]` -> `assistant [bravo 11 tok]`
   - Turn 2: `user [charlie 15 tok]` -> `assistant [delta 21 tok]`
   - Turn 3: `user [echo 26 tok]` -> `assistant [foxtrot 32 tok]`
5. Added unit tests in `tests/test_cli_session_commands.py` and `tests/test_model_invocation_contracts.py` verifying plan history propagation and allocation behavior.
6. Conducted mandatory end-to-end artifact inspection from the operator's perspective, verifying unbroken phonetic turn alternation and monotonically increasing cumulative token counts.
7. Verified full suite pass and 100.00% statement coverage across all 161 source files (3,795 passed) with `./scripts/check.sh`.
