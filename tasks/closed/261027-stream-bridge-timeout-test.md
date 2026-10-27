Filed as: 261027-stream-bridge-timeout-test
FKA:
AKA: github windows timing failure
Legacy index:

keywords: transport, hardening, historical, correctness, stream, coverage

Related: `261021-cross-platform-github-ci`

# Make the upstream timeout test independent of wall-clock scheduling

Status: CLOSED; retained hung-read semantics with a controlled clock.

Latest main: `f5be94f7`. GitHub Actions run `39861774250`, Windows job
`120113983851`, failed only because the mocked hung-thread path took 15 ms
instead of the asserted zero milliseconds. Transport loss and incomplete
activity semantics matched the expected response.

Retain the test: a hung upstream read must report `upstream_read_timeout`,
transport loss, no fabricated progress, and no activity terminality. Control
time in the thread double and check zero and nonzero elapsed timing explicitly.

## Evidence

- Reproduced the original assertion locally by advancing a controlled clock
  15.625 ms after bridge initialization, with production code unchanged.
- Skimmed roadmap and manual workboard triage; this bounded CI repair fits
  their reproducible platform-verification direction. Left both unchanged.

## Verification

- Baseline `uv run pytest`: 3,596 passed, eight skipped, 17 deselected;
  100.00% statement coverage. No natural recurrence of the CI failure.
- Updated bridge module: 24 tests passed, 100.00% statement coverage using
  `scripts/targeted_coverage.py`.
- Acceptance: all 17 passed. Ruff and mypy passed.
- An overlapping no-coverage full-suite run stalled in stdio integration and
  hit the local 20-second timeout. The serial full-suite rerun with CI's
  `-o timeout=60` passed: 3,598 passed, eight skipped, 17 deselected,
  100.00% statement coverage. No production changes were necessary.
