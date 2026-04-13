## Goal

Reduce activation energy for weaker/local models by encoding agentic execution procedures and expressive action lanes without collapsing policy boundaries.

## Why Now

Current strict `shell.argv` lane is safe but can block practical agent flow for multiline/script-like operations, while prompt-only steering still leaves avoidable hesitation in repo-local task execution.

## Scope

- define a dual-lane execution model for strict argv vs rich shell scripts
- add recovery/auto-repair hints when models choose invalid shapes
- introduce invokable procedure assets for common agent loops (discover, triage, pick, execute)
- integrate progressive replay tooling so procedure behavior is testable and repeatable

## Subtasks

- `359`: explicit rich shell-script lane with preserved policy boundaries (implemented)
- `360`: tool-arg error auto-repair hints and corrective next-shape guidance
- `361`: procedure library and invokable procedure call surface
- `362`: replay runner integration for progressive procedure/prompt scripts
- `364`: shell-grant correctness in append-style transcripts (+ user-context parity for `shell_script`)

## Intended Behavior

- models can stay bias-to-action with minimal cognitive overhead
- strict and expressive lanes are explicit and non-ambiguous
- procedure-driven loops are reusable and measurable in replay tests

## Constraints

- preserve append-only durable history and record-type separation
- preserve user-intent vs model-addressable capability boundary
- avoid hidden runtime policy encoded only in implementation (document in assets/docs)

## Done When

- subtasks `359`-`362` are implemented and stitched to docs/tests
- dogfood replays demonstrate reduced hesitation and valid first actions on repo-local tasks
