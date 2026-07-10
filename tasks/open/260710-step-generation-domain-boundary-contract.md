Filed as: 260710-step-generation-domain-boundary-contract
FKA:
AKA: step generation ownership split; generation runtime seam contract; step generation architecture follow-on
Legacy index:

keywords: runtime, investigation, inception, architecture, boundaries, generation, model, policy

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
