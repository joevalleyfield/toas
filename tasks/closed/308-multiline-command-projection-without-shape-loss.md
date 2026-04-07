## Goal

Preserve multiline loose-command shape when converting assistant proposals into user-ready execution text, while keeping single-line `$ ...` shorthand for fast path ergonomics.

## Why Now

Current loose-command projection canonicalizes every assistant `command:` proposal into a single `$ ...` user line. That is lossy for multiline commands and forces users to reconstruct structure manually.

## Scope

- update assistant loose-command projection in `step.py`:
  - single-line command -> `$ ...`
  - multiline command -> preserve multiline bytes (no flattening)
- keep extraction candidate listing clear and faithful for multiline proposals
- ensure `/extract <n>` adopts the same projected content used for execution intent (not an alternate lossy rendering)
- preserve current user-shell shorthand behavior for explicit frontier `$ ...` execution

## Intended Inputs

- loose-command detection and projection in `src/toas/step.py`
- extraction candidate rendering/adoption flow in `src/toas/step.py`
- behavioral tests in `tests/test_step.py`

## Intended Outputs

- no multiline shape loss during assistant->user loose-command projection
- stable single-line shorthand behavior unchanged
- deterministic extraction preview/adoption behavior for multiline commands

## Constraints

- no hidden command rewriting beyond projection formatting
- no by-reference indirection for user execution intent
- preserve existing explicit user `$ ...` execution semantics

## Non-Goals

- no new command language or reference-token execution mode
- no shell quote normalization or automatic syntax repair
- no change to bounded model-addressable `shell` tool policy

## Done When

- assistant multiline `command:` proposals project to user content without flattening to one line
- single-line `command:` proposals still project as `$ ...`
- `/extract` listing/adoption reflects multiline shape faithfully
- tests cover single-line and multiline projection/adoption paths
