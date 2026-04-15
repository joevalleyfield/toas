## Goal

Raise `src/toas/shell_grants.py` from `91%` to `100%` coverage and remove it from missing-lines report noise.

## Why Now

This module is small and branch-light; closing it out is a fast, high-signal elimination.

## Scope

- add deterministic tests for remaining grant-parse/normalization/segmentation edge branches
- preserve shell grant semantics

## Done When

- `shell_grants.py` reports `100%` in full-suite coverage output

## Outcome

- added branch-complete tests for empty/invalid grant parsing, exact-match allow checks, non-string normalization skip/de-dupe, and empty/comment-only script segmentation
- verified `shell_grants.py` now reports `100%` and drops from missing-lines output

## Coverage Notes

- some edge tests rely on parser/tokenizer corner shapes (for example comment-only script segmentation and mixed-type normalization inputs) to hit mechanically uncovered branches
- this achieved report quieting, but the branch-driven input shaping is a signal that parser flow could be more explicit; follow-on simplification is tracked under `386`
