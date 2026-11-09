# Verify recent changes on native Windows

Filed as: 261109-recent-windows-regressions
FKA:
AKA:
Legacy index:
keywords: tooling, hardening, historical, compatibility, windows

Status: CLOSED — 2026-11-09

## Scope

Update the clean Windows checkout from October 30 to current main
(`526afa92`, release `0.0.5.0`), reproduce platform regressions introduced
since that baseline, and fix concrete failures without changing runtime contracts.

## Acceptance

- Run the routine unit, acceptance, lint, and typing checks on native Windows.
- Add focused regression coverage for any production fixes.
- Inspect actual command output for changed user-facing behavior.
- Record tested environments and unresolved limitations.

## Progress

- Fetched origin and rebased the empty working copy onto current main.
- Reviewed roadmap and manual workboard triage; strategic direction remains
  applicable. Historical platform results do not establish this release's status.
- Sandbox uv cache restrictions required running verification with normal
  local access.
- Initial full run: 12 failed, 4030 passed, 8 skipped. Failures were test
  portability defects: direct Unix command dependencies, normalized-path
  expectations, unescaped Windows paths in generated Python fixtures, and a
  CLI assertion requiring Unix separators. Production behavior needed no change.
- Replaced external Unix commands with the current Python interpreter,
  preserving real subprocess, stdin, environment, telemetry, and host snapshot
  execution. Snapshot output explicitly emits UTF-8 to retain the café probe.
- Fixed generated fixture path quoting using Python repr and native path
  expectations. Closed the real stdin handle before injecting a failing writer.
- Focused verification also exposed a bundled-catalog test relying on the
  caller's current directory; isolated workspace/home discovery explicitly.
- Acceptance: 17 passed. Ruff and mypy pass (179 source files).
- Affected-module verification: 264 passed, including an independent bundled
  skill catalog run (9 passed) after removing its working-directory assumption.
- Inspected actual `toas skills` output: workspace task recorder correctly
  shadows the bundled recorder with explicit source/status. Inspected recorder
  CLI dry-run output: native Windows relative path is clear and accurate.
- Final complete unit/coverage run: 4042 passed, 8 skipped, 17 deselected in
  230.99 seconds; all 27402 statements covered (100.00%).
- This verifies native Windows with Python 3.12.13; no fresh Linux, macOS,
  or interactive editor result is claimed.
