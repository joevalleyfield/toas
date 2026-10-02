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

## Progress

- 2026-10-01: Added five small runtime modules after their explicit candidate
  check passed: `runtime/operator_command_context.py`,
  `runtime/presentation_edges.py`, `runtime/rpc_edges.py`,
  `runtime/rpc_payload_edges.py`, and `runtime/session_file_edges.py`. The
  configured set is now 32 of 151 modules. Explicit mypy passed for the five
  candidates and the full configured gate passed for all 32 files.
- 2026-10-01: Ran mypy across all 151 `src/toas` modules. It reported 39
  diagnostics in 11 modules; the other 140 passed unchanged. Expanded the
  configured gate from 32 to those 140 clean modules. At that scan, the modules
  with diagnostics were
  `cli.py`, `cli_commands.py`, `cli_dispatch.py`, `cli_runtime_commands.py`,
  `daemon/process_control.py`, `daemon/server_lifecycle.py`,
  `runtime/async_step_runtime_worker.py`, `runtime/request_handlers.py`,
  `runtime/step_result_runtime.py`, and `runtime/step_runtime.py`. An explicit
  combined check of the 140-file set passed before updating the configured
  gate.
- 2026-10-01: Fixed three low-friction platform/dynamic-typing edges without
  changing behavior: callable handler-map typing, reflective access to the
  multiprocessing exit hook, and reflective Windows `ctypes.windll` access.
  Added `cli_runtime_commands.py`, `daemon/process_control.py`, and
  `runtime/request_handlers.py`; the gate now covers 143 modules. The three-file
  check, Ruff on the edited files, and the 143-file configured gate passed.
- 2026-10-01: Corrected the persistence dependency return type to `list[dict]`
  and allowed the request error-response dependency's keyword arguments. This
  fixed the `step_result_runtime.py` and `request_dispatch.py` diagnostics;
  added `request_dispatch.py`, bringing the gate to 144 modules. Focused checks
  and the configured gate passed, as did Ruff on the touched modules.
- 2026-10-01: Added a structural protocol for the daemon's `serve_one()` loop
  and added `step_result_runtime.py` after its persistence dependency was
  narrowed to the actual list return type. The gate now covers 146 modules;
  focused mypy, configured mypy, and Ruff all passed.
- 2026-10-01: Replaced two CLI keyword dictionaries with explicit typed calls
  and annotated the prompt payload as a mixed-value mapping. Added `cli.py` and
  `cli_commands.py`; the gate now covers 148 modules. The configured mypy gate
  and Ruff passed.
