Filed as: 260804-typed-answer-completion-recovery
FKA:
AKA: projection answer recovery removal; typed completion reconciliation; answer lane purity
Legacy index:

keywords: runtime, implementation, active, correctness, async, stream, projection, provenance, boundaries

Related: `260620-host-stdio-reasoning-terminality-ux`; `260530-shell-lane-spawn-semantics`

# Recover Missing Answer Delivery From Typed Completion State

## Status

Completed on 2026-08-04.

## Objective

Remove rendered transcript projection as a semantic source for synthetic LLM
answer events. Reconcile streamed answer deltas with the typed final generation
completion instead, and preserve reasoning-only recovery from typed reasoning
state.

## Failure Evidence

A successful explicit user shell command printed transcript text containing an
embedded `## TOAS:ASSISTANT` marker. The async worker treated that marker as a
missing model answer, emitted tool stdout on the `llm_answer` lane, truncated
the result projection, and appended an answer-recovery warning even though no
LLM generation occurred.

The canonical `tool_result` remained correct. Host wire logs proved the bogus
`llm_delta` and truncated `projection_delta` were emitted before Vim received
them.

## Contract

- Projection callbacks never create or mutate LLM answer or reasoning events.
- Tool/control-only runs accept arbitrary projected text, including transcript
  marker strings, without acquiring LLM activity.
- Final typed generation content is reconciled with already-streamed answer
  deltas before transcript projection.
- Reasoning-only promotion is based only on typed reasoning state and explicit
  completion provenance.
- A final answer that neither equals nor extends the streamed answer fails
  closed instead of guessing or concatenating attempts.
- Cancellation and terminal guards continue to reject late recovery events.
- Sync CLI behavior and transport replay/deduplication remain unchanged.

## Acceptance Criteria

- [x] Tool stdout containing `## TOAS:ASSISTANT` remains complete in the
  projection and emits no `llm_delta`.
- [x] Projection processing leaves answer byte counts and LLM activity state
  unchanged.
- [x] A typed final answer with no streamed deltas is delivered on the answer
  lane without parsing projection text.
- [x] A typed final answer extending a streamed prefix emits only the missing
  suffix.
- [x] Divergent streamed and final answer content fails an explicit invariant.
- [x] Visible and hidden reasoning-only completions preserve their settled
  recovery policy using typed reasoning provenance.
- [x] Focused async/runtime tests and the full suite pass.

## Allowed Write Surfaces

- `src/toas/llm.py`
- `src/toas/operator_api.py`
- `src/toas/cli_session_commands.py`
- `src/toas/runtime/step_generation_runtime.py`
- `src/toas/runtime/async_step_runtime_worker.py`
- focused LLM, runtime, daemon, and host-stdio tests under `tests/`
- this task file and mechanically generated `tasks/WORKBOARD.md`

## State Gate

The pre-edit state table covers tool-only projection, normal streamed answers,
buffered/salvaged final answers, reasoning-only visible and hidden completion,
empty completion, cancellation, projection ordering, retries, transport modes,
and sync CLI isolation. Machine-checkable assertions require projection purity,
typed prefix reconciliation, typed reasoning provenance, and fail-closed
divergence.

## Completion Evidence

- Removed the rendered-transcript block extractor and projection-to-answer
  synthesis path from the async worker.
- Added `GenerationCompletion`, including final content, typed reasoning,
  content origin, and attempt identity, at the model invocation boundary.
- Added a typed projection-node callback so reasoning-only command tails retain
  their established semantics without parsing rendered Markdown.
- Added the observed regression fixture: tool stdout containing an embedded
  `## TOAS:ASSISTANT` marker remains byte-complete, emits no `llm_delta`, and
  does not acquire LLM activity.
- Added prefix, suffix, divergence, reasoning provenance, terminality, and
  completion-origin assertions.
- Targeted coverage: `async_step_runtime_worker` 61 passed at 100%;
  `step_generation_runtime` 23 passed at 100%; `toas.llm` 105 passed at 100%.
- Full suite: 2,814 passed, 9 deselected, 100% coverage.
