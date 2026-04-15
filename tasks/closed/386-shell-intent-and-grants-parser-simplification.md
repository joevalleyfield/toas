## Goal

Refactor shell intent/grant parsing paths to reduce fallback contortions, make behavior easier to reason about, and improve testability with explicit stage boundaries.

## Why Now

Coverage work surfaced design signal: several edge-branch tests for `shell_intent` and `shell_grants` require awkward, parser-dependent inputs that indicate brittle control flow rather than meaningful user behavior.

## Scope

- split shell-intent extraction into explicit stages (block discovery, parse attempt, recovery scan)
- make fallback entry/exit conditions explicit and narrow
- document intended behavior for malformed YAML and command-key recovery
- review shell-grants parse/segment edges for simplification opportunities discovered during 100% push
- add tests around explicit stage behavior instead of incidental parser quirks

## Intended Behavior

- easier-to-read parser/recovery flow with fewer implicit branches
- tests target behavior intent rather than synthetic parser failure tricks

## Constraints

- preserve external caller contracts and output semantics unless intentionally changed and documented
- no broad shell-policy redesign in this task

## Done When

- shell intent/grant parser flow is simplified with explicit stage boundaries
- contortion-heavy tests are replaced or reduced while preserving behavior coverage intent
- follow-up coverage outcomes are documented (whether or not strict 100% is pursued)

## Outcome

- refactored `shell_intent` extraction into explicit staged flow using callable extractor helpers:
  - block discovery
  - parse attempt
  - structured mapping extraction
  - textual recovery scan
- refactored `shell_grants` parsing/segmentation into explicit callable classes:
  - `ShellGrantParser`
  - `ShellScriptCommandSegmenter`
- preserved external function contracts and behavior while reducing closure-like fallback opacity
- added tests exercising callable parser/segmenter surfaces and staged intent behavior
- verification: full suite passes; shell intent remains at `99%` with one residual branch, but parser/recovery logic is now explicit and maintainable
