Filed as: 260710-step-generation-domain-boundary-contract
FKA:
AKA: step generation ownership split; generation runtime seam contract; step generation architecture follow-on
Legacy index:

keywords: runtime, investigation, historical, contract, architecture, boundaries, generation, model, policy

Parent: `260614-architecture-follow-through-coordination`
Related: `260615-runtime-package-growth-boundary-audit`

# Step Generation Domain Boundary Contract

## Current Reality

`src/toas/runtime/step_generation_runtime.py` currently reads as a partial
owner for step-time model invocation, but it also exposes a large
dependency-assembly seam through `StepCliDeps`.

That object is doing useful transition work, but it also signals that the
current boundary is not yet architecturally settled. The seam presently mixes
forces from several domains:

- Model Invocation: provider request preparation, retry policy, response
  normalization, model-call audit
- Effective Policy And Authority: backend/model selection, config-derived
  settings, secret resolution, provenance of chosen endpoint/model/api key
- Transcript Reconciliation / Operator Semantics handoff: prepared working
  context for one generation consequence
- Projection And Rendering: streamed answer/progress presentation and rendered
  consequence output
- Surface Adapters and session glue: session file IO, newline handling, stdout
  conventions, transcript mutation side effects

The recent `step_generation_cli_edges.py` split reduced file-level noise, but
it did not settle which of those forces should own the workflow shape.

## Desired Reality

The step-generation path should have an explicit ownership story that matches
the architecture documents:

- dependency injection should cross real environmental or domain boundaries
- callback assembly should not stand in for missing workflow owners
- `step_generation_runtime.py` should not be a catch-all composition zone for
  policy, projection, session glue, and model invocation at once

The next implementation slice should be able to name:

- which domain owns the generation workflow itself
- which collaborators are true ports versus internal implementation steps
- which handoff object crosses from transcript/operator context into model
  invocation
- which surface responsibilities remain adapter-owned rather than becoming part
  of generation semantics

## Scope

- reconcile the current step-generation path against:
  - `docs/architecture-masterplan.md`
  - `docs/runtime-direction.md`
  - `docs/runtime-ownership.md`
- identify the minimum set of domain owners participating in one
  generation-backed `step`
- describe the intended boundary between:
  - generation workflow ownership
  - policy/settings resolution
  - projection/rendering
  - session/CLI side effects
- name the follow-on implementation slice that would reduce `StepCliDeps`
  because the ownership split is clearer, not just because the object is
  mechanically smaller

## Non-Goals

- broad package reshuffle inside `src/toas/runtime/`
- opportunistic renaming without a stronger ownership story
- replacing the current seam with a different large service locator
- landing the implementation refactor in the same task

## Evidence To Leave Inception

- a short written boundary proposal exists for the step-generation path
- the proposal uses architecture-domain language rather than file-habit
  language
- at least one concrete implementation follow-on can be named with a likely
  owner and test story
- the proposal explains why `StepCliDeps` is transition scaffolding rather than
  a target architecture

## Boundary Proposal

One generation-backed `step` should cross the architecture domains through
three explicit values rather than through a shared dependency bag.

1. Operator Semantics produces a `GenerationIntent` from the reconciled
   frontier. It identifies the working message frontier and any explicit
   backend/model selections that are meaningful operator intent. It does not
   contain provider settings, secrets, files, renderers, or callbacks.
2. Effective Policy And Authority resolves that intent into a
   `ResolvedModelInvocation`. This value contains the shaped provider messages,
   effective provider settings, retry policy, and observable provenance for the
   chosen endpoint, model, API key source, transport, and policy. Secret values
   may be carried only as invocation credentials; their provenance remains
   separately observable and they never return in results or presentation.
3. Model Invocation executes the resolved invocation and returns a
   `GenerationOutcome`. The outcome contains the normalized assistant message
   and the model-call facts required for durable audit, including attempts,
   response metadata, usage, reasoning content where supported, and a typed
   failure when no response is produced.

Durable State appends the model-call facts and resulting message after the
invocation boundary. Projection And Rendering may observe typed stream events
and render the final consequence, but presentation state is not part of any of
the three semantic handoffs. Session file IO, newline preservation, transcript
redaction, stdout, and post-result side effects remain Surface Adapter/session
edge responsibilities.

The intended flow is therefore:

```text
reconciled frontier
  -> Operator Semantics: GenerationIntent
  -> Effective Policy: ResolvedModelInvocation
  -> Model Invocation: GenerationOutcome + stream events
  -> Durable State: append message and model-call facts
  -> Projection/Surface: render consequence and maintain session surface
```

`StepCliDeps` is transition scaffolding because it currently allows all five
owners to reach through one object and invoke one another's implementation
steps. The target does not replace it with smaller callback collections. Each
owner should use its normal internal functions and expose only the typed
handoff or environmental port at its boundary.

## Available Seams

- `step_runtime.py` already owns frontier classification and accepts a
  generation callable, so the callable can narrow from `working -> dict` to an
  explicit generation-intent handoff without moving step meaning.
- `GenerationRunner.prepare_request()` already approximates the Effective
  Policy boundary, but currently combines context projection, transcript
  directives, secret resolution, and provider settings. It can become a pure
  resolver with explicit inputs and output provenance.
- `GenerationRunner.execute_with_retry()` and `_call_model_once()` already
  approximate Model Invocation. Their true environmental seams are the
  provider call, model-call audit append, retry clock, and stream-event sink.
- `build_artifacts()` already identifies the facts that must cross from Model
  Invocation to Durable State; those facts should become an outcome value
  rather than private keys added to a message dictionary.
- `step_result_runtime.py` already forms the downstream persistence boundary.
  Its broad session-side dependency set is a separate cleanup after the
  generation outcome contract exists.

## First Implementation Slice

Open `260710-model-invocation-contract-extraction` as the first follow-on. It
should introduce the resolved invocation and outcome contracts, move request
resolution behind an explicit function, and reduce `GenerationRunner` to model
execution concerns. Compatibility assembly may remain while callers migrate.

Do not combine the first slice with session persistence or rendering cleanup.
Those concerns become easier to remove from `StepCliDeps` once generation no
longer shares the same dependency namespace, but they have distinct owners and
test stories.

## Disposition

The ownership question is decomposed far enough to implement. Further design
decomposition now would split named types rather than independent uncertainty.
Revisit the boundary only if the first follow-on shows that context shaping is
Operator Semantics rather than Effective Policy, or that model-call audit
cannot remain an output fact consumed by Durable State.

Completed 2026-07-10. The boundary proposal and first executable follow-on now
provide the evidence required to leave inception.
