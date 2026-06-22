Filed as: 260621-search-block-first-line-indent-diff-fidelity
FKA:
AKA: search_block diff indentation; first-line indent mismatch; diff whitespace stripping
Legacy index:

keywords: tooling, hardening, active, correctness, search, patch, whitespace

Related: `566`; `260621-staged-replay-healing-indent-only-mismatches`

# Search Block First-Line Indent Diff Fidelity

## Current Reality

`replace_block` near-match diagnostics can produce a unified diff that shows
odd first-line indentation behavior. The likely cause is whitespace stripping or
normalization around diagnostic diff rendering rather than the actual file
window content.

## Desired Reality

When mismatch diagnostics show a `best-window diff`, the first line should
preserve indentation exactly so the diff is trustworthy for replay or manual
repair.

## Gap Analysis

- We need to identify where indentation is being stripped or normalized before
  diff rendering.
- We need focused regression coverage for first-line indentation fidelity.
- We should keep the fix local to diagnostics so the matching contract does not
  drift.

## Known Facts

- The current near-match path lives in `src/toas/tools_cluster/file_match_ops.py`.
- The odd behavior appears in diff output, not necessarily in the underlying
  selected candidate window.
- Misrendered indentation weakens the usefulness of the diagnostic diff as a
  replay aid.

## Unknowns

- Whether the issue is caused by line splitting, `.strip()`, diff assembly, or
  surrounding projection/rendering.
- Whether only the first line is affected or whether other leading-whitespace
  cases also drift.

## Investigations

- Reproduce the current first-line indentation drift with a focused fixture.
- Trace the diagnostic diff path from selected candidate window to final error
  text.
- Verify whether preserving exact leading whitespace is enough or whether the
  presentation layer also needs escaping/marking help.

## Evidence

Ready to close when:

- a regression test reproduces the old first-line indentation drift
- the diagnostic diff preserves first-line indentation exactly
- the fix stays local to diagnostics and does not perturb matching behavior

## Risks

- Over-normalizing output for readability could keep obscuring meaningful
  whitespace deltas.
- A rendering-only fix could hide a deeper candidate-window slicing problem if
  we do not verify the raw selected text.

## Next Actions

- Add a focused failing test for first-line indentation drift in `best-window diff`.
- Patch the diagnostic rendering path to preserve exact leading whitespace.
- Re-run targeted file-op coverage.
