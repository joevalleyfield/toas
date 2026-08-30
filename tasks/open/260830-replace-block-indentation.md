Filed as: 260830-replace-block-indentation
FKA:
AKA: replace block inferred indent; indentation-retaining replacement; no-indent block edit
Legacy index:

keywords: tooling, implementation, active, usability, correctness, patch, defaults

Related: `334`; `393`; `394`; `260621-staged-replay-healing-indent-only-mismatches`

# Infer And Retain `replace_block` Indentation By Default

Make the ordinary no-indent `replace_block` call robust when its YAML-decoded
`search_block` has lost the leading indentation present in the file. Match a
block across one uniform leading-indent difference and carry the matched
indentation onto the replacement unless the caller supplied explicit indent
controls.

## Source

Workspace inbox triage (`Documents/Journal/inbox.md`). Discovered 2026-08-29
during a tool audit.

## Current Contract

- `search_indent` and `replacement_indent` accept explicit indentation.
- omitted `replacement_indent` inherits explicit `search_indent`.
- `match_mode=default` tolerates blank-line whitespace but keeps nonblank line
  indentation exact.
- `match_mode=lax` can find broad whitespace variants, but replacement text
  does not inherit the matched region's leading indentation.
- prior task `334` deliberately excluded automatic inference when both indent
  arguments are omitted, so this is a new contract rather than a duplicate.

## Scope

- Add a bounded default-mode path that recognizes a search block differing
  from a file region only by one uniform leading indentation prefix.
- Capture that prefix from the unique matched region and apply it to the
  replacement when `replacement_indent` is omitted.
- Preserve relative indentation within both the search and replacement blocks.
- Keep `expected_count` and zero/ambiguous-match failures authoritative after
  inferred matching.
- Keep explicit `search_indent` and `replacement_indent` authoritative.
- Keep `match_mode=strict` byte-oriented and avoid broadening `lax` into a
  second, conflicting indentation-inference contract.
- Update callable/help text if users need to know the new default or how to
  opt into explicit behavior.

## Acceptance Criteria

- A default call with no indent arguments can replace a uniquely matched
  indented Python-style block using an unindented `search_block`.
- The replacement receives the matched block's leading prefix and preserves
  its own nested relative indentation.
- A block already at column zero still behaves as before.
- Explicit `search_indent` controls matching and explicit
  `replacement_indent` controls output without inference overriding either.
- `match_mode=strict` still requires exact indentation.
- Multiple indentation-compatible matches still fail unless
  `expected_count` explicitly permits that count; no arbitrary candidate is
  selected.
- Blank lines, trailing-newline behavior, and LF/CRLF write policy retain
  their current contracts.
- Focused regressions and the repository's required check set pass with the
  coverage gate intact.

## Allowed Write Surfaces

- `src/toas/tools_cluster/file_ops.py`
- `src/toas/tools_cluster/file_match_ops.py`
- the `replace_block` registry/capability guidance needed to expose the final
  contract
- focused `replace_block` tests
- this task file and mechanically generated `tasks/WORKBOARD.md` sections

## Required Completion Evidence

- focused tests for unique inference, nested indentation, explicit overrides,
  strict-mode preservation, ambiguity, newline edges, and CRLF parity;
- targeted coverage for changed tool modules;
- the full required check result;
- a progress note naming the final inference boundary and closing commit.
