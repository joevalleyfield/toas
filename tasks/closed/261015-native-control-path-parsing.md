# Native Windows Paths in Transcript Controls

Filed as: 261015-native-control-path-parsing
FKA:
AKA: Windows cd parsing; config load path backslashes; workspace control replay
Legacy index:

keywords: runtime, hardening, historical, compatibility, windows, transcript

Parent: `261015-windows-compatibility-restoration`
Related: `260621-windows-shell-launcher-and-path-resolution`

Status: CLOSED 2026-10-15; preserve native Windows paths in execution and branch replay

## Failure and Contract

POSIX `shlex.split` consumed backslashes in unquoted native Windows paths.
`/cd C:\work\target` reached resolution as `C:worktarget`; config loading and
workspace additions failed the same way. Historical branch reduction used a
second parser and silently ignored the resulting invalid paths.

On Windows, `/cd`, `/workspace add|remove`, and `/config load|save` now treat
backslashes literally and accept single or double quotes around paths with
spaces. A quoted trailing directory separator is retained. Shell scripts,
other controls, and POSIX-host escaping retain their existing behavior.

The shared runtime parser is used by both frontier command extractors, the
session command-tail extractor, and config/directory/workspace branch reducers.
This changes parsing before consequence resolution; it does not rewrite prior
history or introduce a transport-specific execution path.

## Evidence and Verification

- Reproduced five baseline failures in directory/config transcript replay and
  the ordered `/cd` reducer; new frontier path regressions also failed before
  parser integration. All now pass.
- Added cross-platform parser cases for native drive paths, UNC paths, quoted
  spaces, trailing separators, config load/save, workspace add/remove, `/cd -`,
  malformed quoting, and unchanged POSIX/non-path escaping.
- A sixth baseline failure was a config digest test expecting an LF hash after
  native text output wrote CRLF. Explicit LF/CRLF byte fixtures now verify both
  fixed digests without changing production digest semantics.
- Combined focused run: **388 passed**, covering parser, runtime step/replay,
  request handler, session edges, frontier, operator commands/handlers, and
  config digest cases with `-o addopts= -q --tb=short`.
- New parser targeted coverage: **100%**, 14 statements, 12 tests, zero missing
  files via `scripts/targeted_coverage.py`.
- Changed-file Ruff passes.
- Real `python -m toas step` with `TOAS_RPC_MODE=off` in a temporary directory
  containing spaces: inspected `/cd`, `/config save`, and `/config load` output;
  verified the saved file and durable `command_context` native cwd.

POSIX parser behavior is exercised by platform-independent tests; actual POSIX
host verification and the complete Windows check spine remain master-task gates.
