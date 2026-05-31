## Goal
keywords: tooling, explore, parked, contract, apply_patch, safety, weak-model, recovery

Explore and define a weak-model-safe `apply_patch` tool contract that improves first-pass correctness and guided recovery for lower-prior models.

## Why Now

Current tool ergonomics rely significantly on model priors. We want a tighter contract and response shape that remains reliable when priors are weaker.

## Scope

- investigate request/response contract options for `apply_patch`
- define structured error taxonomy and repair guidance payloads
- design deterministic validation/apply workflow (including `validate_only`)
- identify sequencing/state-handle patterns that reduce ambiguity across retries
- produce a candidate test/evaluation plan for first-pass success and bounded self-repair

## Intended Behavior

- tool responses are machine-checkable and repair-oriented
- failed calls return actionable, minimally sufficient retry guidance
- caller can distinguish no-op/success/partial-risk states deterministically

## Constraints

- keep compatibility path with current YAML envelope usage model
- preserve workspace/policy safety guarantees as runtime-enforced behavior
- avoid over-broad tool flexibility that increases ambiguous calls

## Done When

- exploratory design doc/checklist is drafted with concrete contract candidates
- tradeoffs and migration options are explicit
- follow-on implementation tasks are identified and sized

## Collaboration Plan

- refine this task collaboratively before implementation starts
- lock success metrics and acceptance checks before opening build tasks
