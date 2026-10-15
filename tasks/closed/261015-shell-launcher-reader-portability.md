# Shell Runtime Selection and Reader-Stall Portability

Filed as: 261015-shell-launcher-reader-portability
FKA:
AKA: Git Bash versus WSL; multiple PowerShell runtimes; POSIX reader-stall tests
Legacy index:

keywords: tooling, hardening, historical, compatibility, windows, shell, stream

Parent: `261015-windows-compatibility-restoration`
Related: `260621-windows-shell-launcher-and-path-resolution`

Status: CLOSED 2026-10-15; restore native default shell execution and intentional runtime tests

## Causes and Changes

- Windows PATH resolves bare Bash to the System32 WSL launcher here, while
  native Git Bash is installed outside PATH. The default native shell launcher
  now avoids that WSL shim, retains native Bash/sh found on PATH, and otherwise
  locates `bin/bash.exe` relative to the discovered Git installation before the
  existing cmd fallback. It does not mutate PATH or reject explicit WSL argv.
- Two POSIX reader-stall tests accidentally selected the Windows drain branch
  on this host. A small platform-query seam lets them explicitly exercise POSIX
  behavior without changing global `os.name` and breaking pathlib. Added bounded
  tail-drain cases for missing/closed streams, failed nonblocking setup, EAGAIN,
  read errors, empty tails, and text tails.
- PATH composition testing now uses the host separator and its case comparison
  contract. Direct argv tests use the known Python executable with explicit
  grants instead of assuming external echo/pwd/printf programs exist. They
  still assert output, real cwd, and projection; argv execution was not silently
  changed into shell interpretation.
- Launcher assertions allow absolute native shell paths. A regression covers
  WSL-shadowed Bash, a Git installation with spaces, and missing Git Bash.

## Multiple Runtime Contract

The operator explicitly requested that Bash variants and PowerShell variants
remain independently usable, with tests identifying what they exercise.
`tests/test_shell_runtime_matrix.py` selects each discovered executable by its
explicit path: PATH Bash (identified as WSL here), Git Bash, Windows PowerShell,
and pwsh. Missing or unusable runtimes receive explicit test skip reasons.

All four are installed and passed here. WSL required explicit `WSLENV` transfer
of the test variable; native shells inherited it directly. The test declares
that boundary rather than changing global environment policy. Bash tests exercise
POSIX `find` semantics on a real fixture; PowerShell cases inspect resolved
`find.exe`. Identical command names must not be treated as interchangeable
utilities or a reason to rewrite PATH implicitly.

## Verification

- Four shell/reader modules: **260 passed**, including real execution and both
  platform-specific drain tests. Shell ops/streaming targeted coverage: **100%**,
  430 statements, zero missing files. The successful coverage rerun used
  `--timeout=60` after one earlier run hit a filesystem fixture-write timeout.
- Explicit runtime matrix: **4 passed**, no runtime skips on this machine.
- Complete host-stdio LLM stand-in integration module: **11 passed**, including
  shell provisional/final projection and user-lane pacing; no deselection.
- Ruff passed for changed Python files; whitespace checks passed.
- Inspected actual native user-shell pipeline output in a temporary directory:
  launcher was `C:\Program Files\Git\bin\bash.exe`, output was `native-ok` in
  the expected inert stdout block, exit status was zero, and host PATH was unchanged.

Full repository spine and POSIX-host execution remain master-task gates.
