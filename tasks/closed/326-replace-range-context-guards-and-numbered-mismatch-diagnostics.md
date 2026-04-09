## Goal

Add optional context guard checks to `replace_range` so replacements can verify expected surrounding text, with clear numbered-line diagnostics on mismatch.

## Why Now

`replace_range` is fast but can be brittle when line mappings drift. Lightweight context checks at replacement boundaries reduce accidental edits and make failures easier to debug.

## Scope

- extend `replace_range` arguments with optional boundary checks:
  - begin/start context check (required shape to be finalized)
  - optional end context check
- on guard mismatch, fail with diagnostics that include:
  - numbered lines from the actual file around the replacement span
  - clear indication of expected vs actual context
- preserve existing `replace_range` behavior when no context checks are provided

## Intended Behavior

- default behavior remains unchanged (no checks => replace by line range)
- when checks are provided:
  - replacement proceeds only if file context matches expectations
  - failure message points to exact divergence with line numbers
- diagnostics are concise but actionable for immediate correction

## Intended Inputs

- `src/toas/tools.py` (`_run_replace_range`)
- `tests/test_tools.py`
- optional capability prompt/docs updates (`README.md`)

## Intended Outputs

- safer structural edits with optimistic concurrency-style guardrails
- faster repair loop when target file drift causes mismatch

## Constraints

- keep backward compatibility for existing `replace_range` callers
- avoid regex complexity for first pass unless explicitly needed
- failure messages must remain deterministic for testing

## Non-Goals

- no full semantic/AST match requirement
- no automatic retry or fuzzy patching in first pass

## Done When

- optional start/end context checks are implemented and tested
- mismatch diagnostics include numbered original lines
- existing `replace_range` tests still pass unchanged
