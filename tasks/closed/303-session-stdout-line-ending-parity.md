## Goal

Preserve line-ending style parity between `session.md` and projected stdout transcript writes so operator output does not unexpectedly flip newline conventions.

## Why Now

Live usage surfaced a mismatch between line endings present in `session.md` and line endings written to stdout/projection surfaces. This causes avoidable churn in diffs, tooling behavior, and editor display.

## Scope

- detect effective newline style of `session.md` content (`LF` vs `CRLF`) when projecting/writing transcript output
- use detected style for generated transcript-aligned stdout text where feasible
- define deterministic fallback when no prior file exists or style cannot be inferred
- add tests covering LF, CRLF, and mixed-input fallback behavior

## Intended Inputs

- transcript read/write/projection logic in `src/toas/transcript.py`
- CLI projection paths in `src/toas/cli.py`
- tests in `tests/test_transcript.py` and/or `tests/test_cli.py`

## Intended Outputs

- consistent newline behavior matching user/editor choice in `session.md`
- reduced line-ending churn in projected output
- explicit documented policy for mixed/new-file cases

## Constraints

- do not mutate historical durable records to normalize line endings
- preserve existing transcript semantic structure and parsing contracts
- keep behavior cross-platform and deterministic

## Non-Goals

- no global repository newline policy enforcement
- no retroactive rewriting of existing files for normalization

## Done When

- projection output matches existing `session.md` newline convention in representative cases
- fallback behavior is explicit and tested
- no regressions in transcript parsing/projection tests
