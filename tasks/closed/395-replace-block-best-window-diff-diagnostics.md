## Goal

Improve `replace_block` no-match diagnostics by comparing the best same-length file window against `search_block`, with a similarity metric and conditional diff output.

## Why Now

Current overlap diagnostics are useful but can be hard to action quickly. A best-window comparison with a readable diff should shorten repair loops when matches almost line up.

## Scope

- compute best same-length candidate region in file content for failed `search_block` matches
- report similarity ratio for that candidate
- include unified diff when similarity is high enough to be actionable
- keep existing diagnostics and error contracts intact
- add tests for high-similarity and low-similarity branches

## Done When

- no-match diagnostics include best-window similarity information
- actionable diffs appear only when similarity threshold is met
- tests cover both behavior paths
- roadmap/task state are stitched

## Completed

- added best equal-length region selection for failed `replace_block` matches
- diagnostics now include best-window file span and similarity ratio
- added similarity gate (`0.55`) for diff rendering:
  - high similarity: includes unified diff (`search_block` vs `file_window`)
  - low similarity: emits omission message instead of noisy diff
- preserved existing overlap/context diagnostics
- added tests for both high-similarity diff and low-similarity omit paths
- verification: `uv run pytest -q` passes
