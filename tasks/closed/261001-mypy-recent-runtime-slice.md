Filed as: 261001-mypy-recent-runtime-slice
FKA:
AKA: mypy expansion; recent runtime typing
Legacy index:

keywords: tooling, hardening, historical, maintainability, correctness, coverage

Related: `261001-tool-failure-visibility`

# Add Recent Runtime Files To The Mypy Gate

Extend the configured mypy file set with recently changed runtime and tool
modules. The five session/tool modules passed without changes. The latest
`state_step.py` slice exposed six typing diagnostics, so fix those at the
ownership site and add the module to the gate as well.

## Acceptance Criteria

- All six files appear in `[tool.mypy].files`: `cli_session_commands.py`,
  `tools_cluster/basic_ops.py`, `tools_cluster/execution.py`,
  `tools_cluster/rendering.py`, `tools_cluster/survey_ops.py`, and
  `runtime/state_step.py`.
- `uv run mypy` and `scripts/check.sh` pass without adding suppressions.
- The task records the verified result and closes with the configuration change.

## Verification

- Explicit pre-change mypy check passed for all five session/tool files.
- `runtime/state_step.py` initially had six diagnostics: an `Any`/`dict`
  assignment conflict, a local redefinition, and four dynamic-value arguments
  inferred as `object`. Narrow annotations at the relevant construction points
  resolved them without suppressions.

## Outcome

Closed on 2026-10-01. Added all six recent files to the configured mypy gate.
The state-step typing cleanup uses an `Any` annotation where the observation
shape is intentionally dynamic and a dedicated typed name for user-tool
outcomes.

Verification: `uvt run mypy` passed for 27 source files. The full
`scripts/check.sh` run passed: 3,403 tests, 17 acceptance checks, Ruff, mypy,
and 100% statement coverage.
