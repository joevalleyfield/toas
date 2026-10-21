# PowerShell platform find expectation

Filed as: 261020-pwsh-platform-find-expectation
FKA:
AKA:
Legacy index:

keywords: tooling, hardening, historical, compatibility, shell

Related: `261015-windows-compatibility-restoration`

Status: CLOSED — 2026-10-20

## Intent and acceptance

The explicit PowerShell runtime test must resolve `find.exe` on Windows and
`find` on macOS/Linux, retaining application-only lookup so PowerShell aliases
cannot satisfy the assertion. Missing applications must fail explicitly.
Verify with installed PowerShell on macOS and run the repository check script.

## Progress

- Replaced the unconditional Windows executable expectation with the native
  platform name; application lookup uses `-ErrorAction Stop`.
- Reviewed roadmap and manual workboard triage; no strategic changes needed.

## Verification

- `.codex-local/bin/uvt run bash scripts/check.sh`: 3,585 passed, 9 skipped,
  17 deselected; 100.00% statement coverage. All 17 acceptance tests, Ruff,
  and mypy passed. Installed macOS `pwsh` exercised the POSIX expectation.
- Windows/Linux were not available for local execution; Windows retains its
  existing `find.exe` expectation and Linux shares the POSIX branch.
