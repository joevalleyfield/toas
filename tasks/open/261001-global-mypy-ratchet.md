Filed as: 261001-global-mypy-ratchet
FKA:
AKA: global typing; mypy expansion; static typing ratchet
Legacy index:

keywords: tooling, hardening, active, maintainability, correctness

Related: `261001-mypy-recent-runtime-slice`; `504-coverage-missing-files-ratchet-gate`

# Expand Mypy Coverage Across The Project

Keep a standing task open to expand mypy coverage in small, verified steps,
using the same ratchet approach that grew the test-coverage gate. At opening,
the configured gate checks 27 of the 151 Python modules under `src/toas`.

## Intent

Make type checking a progressively broader project invariant without requiring
the whole codebase to become clean in one change. Each increment should leave
the checked set at least as broad as before and the configured mypy command
green.

## Ratchet Loop

- Choose a small coherent slice, favoring recently changed files or modules
  whose ownership boundary is already clear.
- Run mypy on the candidate slice to expose the real typing work.
- Fix typing at the owning code seam; avoid blanket ignores, broad suppressions,
  or weakening existing settings to make a slice pass.
- Add passing files to `[tool.mypy].files` and run the configured mypy gate.
- Run the full repository check when the slice changes production behavior or
  typing assumptions across module boundaries.
- Record the files added, any justified exceptions, and verification here so
  the next increment has a visible baseline.

## Acceptance Criteria

- Every maintained first-party Python module under `src/toas` is checked by
  mypy, either directly or through a verified package-wide target.
- The configured mypy gate passes without unexplained file omissions or broad
  error suppressions.
- Any maintained Python code outside `src/toas` is inventoried and either
  included in the gate or given a specific, documented reason to remain out of
  scope.
- Each ratchet step records its verified expansion and keeps the workboard
  current; close this task only after the project-wide inventory is covered.

## Baseline

- 2026-10-01: 27 of 151 Python modules under `src/toas` are in
  `[tool.mypy].files`; the configured mypy command passes.
- The preceding increment is recorded in
  `261001-mypy-recent-runtime-slice`, which added six recently touched modules.
