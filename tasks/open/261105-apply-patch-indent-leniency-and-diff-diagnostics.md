Filed as: 261105-apply-patch-indent-leniency-and-diff-diagnostics
FKA: 261105-apply-patch-indent-leniency-and-diff-diagnostics
AKA: apply_patch unified diff; apply_patch indentation leniency; patch diagnostics
Legacy index: null

keywords: tooling, apply_patch, diagnostics, indentation, correctness

# apply_patch Indentation Leniency and Unified Diff Diagnostics

## Why

When patches are generated inside YAML literal scalar blocks (`|2`, `|4`) or by models with minor indentation offsets, `apply_patch` currently fails with an opaque pipe-separated chunk summary. Adding uniform indentation inference (matching `replace_block`) and a unified diff diagnostic for context mismatches makes patch application robust and failure triage immediate.

## In scope

- Infer uniform block indentation shift when exact chunk match fails and exactly one candidate site exists
- Replace pipe-delimited chunk preview on context mismatch with a multiline unified diff against the closest candidate window
- Preserve safety invariants: fail on ambiguous multiple candidate matches or context-free chunks
- Maintain backwards compatibility with error assertions (e.g. keeping `chunk:` marker in error output)
- Add comprehensive test coverage in `tests/test_tools.py`

## Out of scope

- Fuzzy/heuristic line editing beyond uniform indent offsets
- Redesign of the underlying patch protocol

## Acceptance Criteria

- [x] Patches with uniform indent offset apply cleanly when the target site is unique
- [x] Ambiguous indent matches fail with a clear diagnostic
- [x] Context mismatch errors render a unified diff comparing expected chunk against the closest target file region
- [x] Existing apply_patch error contracts remain compatible
- [x] All tests pass with full coverage (151 passed, 100.00% statement coverage in apply_patch_ops.py)

## Status

- Implementation complete in `src/toas/tools_cluster/apply_patch_ops.py`.
- Unit tests and diagnostic regressions added in `tests/test_tools.py` and `tests/test_tools_apply_patch_ops.py`.
