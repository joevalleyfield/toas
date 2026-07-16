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

## Progress Notes

- 2026-07-16: Claimed for a focused fixture investigation. The matrix includes
  LF and CRLF files plus present and absent final newlines (`noeol`) on both
  the searched block and file tail; it will distinguish diagnostic
  classification from an actually replayable staged repair.
- 2026-07-16: Pinned the failure with an end-to-end four-case matrix: LF/CRLF
  file style crossed with LF/CRLF search-block style, all at a `noeol` file
  tail. The initial call correctly offered `search_indent=4`, but replaying
  that repair failed because default matching required the search block's
  final newline and preserved CRLF tokens despite normalized file reads.
- 2026-07-16: Resolved the replay seam in
  `blankline_tolerant_pattern(...)`. Default-mode line separators now accept
  LF or CRLF, and only a final search-block separator may be absent at EOF.
  Strict mode remains byte-exact; `ensure_trailing_newline` continues to own
  whether a successful replacement writes a final newline.
- 2026-07-16: The inverse EOF direction is also explicit: a no-EOL search
  block can repair a file that has a final newline. The unmatched delimiter is
  retained, so `ensure_trailing_newline=False` never silently removes a file
  newline that the search did not include.

## Evidence

Ready to leave inception when:

- [x] a minimal trailing-edge repro exists
- [x] the failure is localized to a specific comparison/classification seam
- [x] safety constraints for the fix are explicit

## Completion

The focused implementation landed in this task because the reproduction
localized the behavior to one default-mode matcher helper and the contract is
bounded: line separators are equivalent only in `default` mode, a final search
separator may be absent at EOF, and unsearched delimiters remain untouched.
