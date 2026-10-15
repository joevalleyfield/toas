# Native Windows Vim Harness Restoration

Filed as: 261017-vim-harness-windows
FKA:
AKA: Vim PTY portability; pexpect Windows; plugin verification
Legacy index:

keywords: tooling, hardening, compatibility, windows, vim

Parent: `261015-windows-compatibility-restoration`

Status: CLOSED 2026-10-17; native Windows Vim contracts restored

Thirty tests fail at POSIX-only pexpect.spawn before exercising Vim. Restore
native Windows terminal execution, keeping real interactive timer, job/channel,
projection, cancellation, and real-host plugin contracts exercised. Preserve
POSIX verification and bound process lifetimes with useful diagnostics.

Initial reproduction: baseline and both contract-plugin cases fail with missing
pexpect.spawn. Windows resolves vim through C:/Windows/vim.bat.

Existing edits are prior restoration slices and preexisting experiment artifacts;
keep this slice scoped to the Vim harness and any observed plugin defects.

## Restoration

- Shared vim_terminal adapter: existing POSIX pexpect path plus native Windows
  ConPTY through a Windows-only pywinpty development dependency. Checked drivers
  still run real Vim and real foreground keystrokes; no Windows contract is skipped.
- Bound native terminal reads, distinguish process exit from a retained ConPTY
  handle, retain diagnostics, and kill the Windows process tree on timeout.
- Use slash-separated Vim script paths, sys.executable for checked Python hosts,
  and argv lists for the contract host (legacy string configuration remains).
- Real-host fixtures explicitly select their temporary workspace, avoiding
  ancestor .toas discovery. Script-ID lookup accepts native Vim separators.
- Fixed a product defect exposed after terminal startup: os.kill(pid, 0) has
  console-control semantics on Windows, not POSIX existence-check semantics.
  Extracted the existing OpenProcess/GetExitCodeProcess query into runtime-owned
  process_liveness; daemon keeps its import surface. Host owner and durable-host
  record checks now use the safe probe. POSIX permission/missing behavior stays
  covered. A real-child regression checks repeated probes leave it alive.
- TOAS_TEST_VIM_BIN selects the bare Vim used by pytest wrappers. Explicit driver
  paths retain precedence. Native Vim is the Windows contract; mixed MSYS/native
  host behavior is tracked in 261017-msys-vim-native-host.

## Focused Verification

- All 34 existing Vim-related checks pass. With the first three real-terminal
  regressions included: 37 passed, 3559 deselected in 65.53 seconds, normal deadline.
  A subsequent runtime-override regression brings the focused terminal module to
  four passes (1.72 seconds), including explicit executable precedence.
- Runtime host/process/record plus daemon query tests: 94 passed, 284 statements
  at 100% targeted coverage, zero missing files. Changed-file Ruff passes; focused
  mypy succeeds for all four changed source files.
- Inspected actual native Vim JSON/transcripts: real-host answer succeeds and
  reasoning contains the complete THINKING block followed by final answer.
- Git Bash explicitly selecting native Vim passes baseline, interactive timer,
  and real-host smoke (three passes). MSYS baseline passes after path repair;
  its real-host probe still hits an exit-hook E282 and is not claimed supported.
- Acceptance now completes all 17 scenarios: 16 pass, one fails launching direct
  echo on Windows (WinError 2). This is evidence of restored completion, not an
  acceptance success claim. Shell execution remains with the restoration parent.
## Full Native Rebaseline

PowerShell uv run pytest --tb=short completed in 207.66 seconds: **3,565 passed,
six failed, eight skipped, 17 deselected**. All Vim checks pass. Coverage is
99.96%, nine missing statements in cli_session_commands (three), daemon lifecycle
(two), and journal locking (four). The later fourth terminal regression passed
separately; no aggregate is inferred by adding it to this measured run.

The six native shell/frontier failures and one completed-run acceptance failure
are tracked in 261017-native-shell-frontier. Static and full coverage gates stay
with the master. MSYS interoperability remains an explicit open follow-on; native
verification from Git Bash uses TOAS_TEST_VIM_BIN to select the intended Vim.