Filed as: 260622-staged-replay-trailing-edge-newline-healing
FKA:
AKA: staged replay trailing edge; search_indent newline sensitivity; CRLF heal fallback
Legacy index:

keywords: tooling, investigation, inception, correctness, search, patch, replay, whitespace

Related: `260621-staged-replay-healing-indent-only-mismatches`; `513`; `260621-search-block-first-line-indent-diff-fidelity`

# Staged Replay Trailing-Edge Newline Healing

## Current Reality

Staged replay healing for indent-only `replace_block` mismatches is broadly
working, but there appears to be a remaining edge case near the trailing edge
of the block where newline-style differences can prevent the indent-only path
from being recognized.

When that happens, a case that appears mechanically healable may fall back to
fuzzy mismatch diagnostics instead of staging `/heal ...`.

## Desired Reality

If indentation is still the only meaningful delta, staged replay healing should
remain available even when the final line or trailing newline style differs
between the `search_block` and the file content.

## Gap Analysis

- The current full-block indent detector may be too strict around final-line or
  trailing-newline shape.
- Newline-style mismatch reporting exists, but it may currently preempt or hide
  an otherwise safe indent-only healing classification.
- We do not yet have a pinned reproduction fixture for the trailing-edge case.

## Known Facts

- `replace_block_mismatch_diagnostics(...)` in
  `src/toas/tools_cluster/file_match_ops.py` already detects newline-style
  mismatch and separately short-circuits full-block indent-only matches.
- The reported dogfood failure seemed almost exactly like: newline mismatch
  prevented an otherwise indent-only case from staging `/heal`, causing fuzzy
  diagnostics instead.
- There is already an open CRLF-oriented task for `apply_patch` (`513`), but
  this seam is in `replace_block` mismatch classification and staged replay
  healing rather than patch application.

## Assumptions

- The important failure mode is classification, not execution: the healed
  replay likely would have been safe if it had been staged.
- The bug is probably at the interaction between indent-only detection and line
  ending / trailing-edge normalization, not at the broader staged replay
  command surface.

## Unknowns

- Whether the culprit is CRLF vs LF alone, missing trailing newline alone, or a
  combined final-line boundary case.
- Whether the safest fix belongs in `_full_block_indent_shift(...)`,
  `replace_block_mismatch_diagnostics(...)`, or earlier normalization.
- What the minimal reproducer looks like.

## Investigations

- Build focused fixtures that vary only:
  - LF vs CRLF
  - presence/absence of final trailing newline
  - indentation shift with otherwise identical block text
- Confirm whether the current path emits fuzzy diagnostics where `/heal` should
  be staged.
- Identify the narrowest normalization or comparison seam that restores the
  indent-only classification without broadening false positives.

## Evidence

Ready to leave inception when:

- a minimal trailing-edge repro exists
- the failure is localized to a specific comparison/classification seam
- safety constraints for the fix are explicit

## Next Actions

- Reproduce the trailing-edge newline-sensitive miss in a focused test.
- Decide whether to normalize for classification only or to adjust the
  full-block indent detector directly.
- Open a focused implementation slice once the repro is pinned down.
