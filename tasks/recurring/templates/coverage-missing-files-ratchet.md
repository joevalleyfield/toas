# Recurring: Coverage Missing-Files Ratchet

## Purpose
Ratcheting cadence for `--cov-max-missing-files` to prevent drift and steadily reduce partially covered files.

## Trigger
- Weekly or after meaningful test coverage improvements

## Inputs
- Full-suite coverage report
- Current cap in `pyproject.toml`
- Candidate low-effort/high-signal coverage targets

## Checklist
- Run full suite with coverage
- Confirm current cap passes
- Improve coverage for selected target files where needed
- Ratchet cap downward by 1 when suite is stable
- Record cap change and validation results

## Output
- Dated run artifact with before/after cap and test result summary
