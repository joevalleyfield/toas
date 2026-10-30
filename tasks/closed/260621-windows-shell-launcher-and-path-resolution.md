Filed as: 260621-windows-shell-launcher-and-path-resolution
FKA:
AKA: windows shell launcher; bash -ic; msys find resolution
Legacy index:

keywords: tooling, implementation, closed, compatibility, shell, windows, path

Status: CLOSED — 2026-10-30

# Windows Shell Launcher And Path Resolution

## Current Reality

The environment-policy implementation pass is landed. Real Windows runtime
matrix verification was recorded on 2026-10-15. The October 29 operator
failure provides secondary evidence of correct GNU find selection; its
argument-corruption fix and successful execution complete the evidence chain.

- The shared shell launcher now prefers `bash -lc` instead of `bash -ic` for
  Windows non-TTY subprocess execution.
- The shared subprocess boundary now resolves bare outer executables through the
  effective PATH before process creation, avoiding Windows `CreateProcess`
  lookup surprises.
- Explicit environment profiles can now select `inherit`, `replace`, or
  `merge`, with runtime-family and exact-runtime bindings and deduplicated PATH
  prepend/append composition.
- The legacy launcher duplication in `src/toas/tools.py` has been collapsed
  onto the shared shell launcher.
- The old implicit PATH-reordering fix was superseded by explicit environment
  policy. Do not restore executable-derived PATH shaping to force `find`
  precedence. Verify the intended inherited/configured environment at the
  operator's bound-process boundary.

## Desired Reality

Windows shell execution should be non-interactive by default and should pass
the host-launched environment through to subshells and executed tools without
implicitly rewriting `PATH` based on the selected child executable.

If the host was launched from Git Bash/MSYS, its MSYS environment should remain
available to children. If the host was launched natively, TOAS should not
invent MSYS-style paths. A project may explicitly select a different
environment policy when it needs to act as the Romans in Rome.

## Contract Direction

Environment selection and executable selection are independent decisions.

The environment contract has three modes:

- `inherit`: pass the host environment through unchanged by default.
- `replace`: use the configured environment instead of the lower-level one.
- `merge`: apply configured changes over the lower-level environment.

Configuration resolves from broad to specific levels:

```text
host → general project → runtime family → exact resolved runtime
```

Each level may reference one named environment profile and may select its own
mode. A runtime identity is the selector; the profile name is the reusable
handle; profile values define the environment changes.

For `PATH`, the first implementation only needs ordered `prepend` or `append`
operations. Entries preserve declared order, and the resulting path is always
deduplicated using platform-appropriate comparison (case-insensitive on
Windows). Removal is deferred until a concrete use case requires it.

Runtime-family fallback and exact-runtime selection provide composition across
levels, so profile lists or profile inheritance are deferred.

## Known Facts

- `src/toas/tools_cluster/shell_ops.py` owns the shared shell launcher used by
  user-shell execution.
- `src/toas/tools.py` now delegates `_shell_launcher_argv(...)` to the shared
  cluster implementation used by user-shell execution.
- Regression coverage expects `bash -lc` on Windows launcher paths and asserts
  that default normalization does not seed PATH from the selected executable.

## Decisions

- Prefer `bash -lc` instead of `bash -ic` for non-TTY Windows subprocess work.
- Preserve the host-launched environment by default; child shell choice must
  not implicitly modify `PATH`.
- Allow explicit runtime-specific environment profiles to modify the inherited
  environment through `inherit`, `replace`, or `merge` modes.
- Resolve exact runtime profiles before runtime-family profiles, then fall
  back to general project configuration and host inheritance.
- Deduplicate composed `PATH` entries while preserving the winning
  prepend/append order; defer removal operations.
- Collapse the legacy launcher facade onto the shared cluster implementation.

## Progress Notes

2026-10-15: `261015-shell-launcher-reader-portability`, under the Windows
restoration master, verified real execution on this Windows machine. Native
default selection avoids the System32 WSL shim and discovers Git Bash relative
to Git without modifying PATH. Explicit WSL Bash, Git Bash, Windows PowerShell,
and pwsh each passed environment/cwd/runtime tests; WSL uses declared WSLENV
transfer. Bash tests exercise POSIX find; PowerShell tests inspect find.exe
resolution. Keep exact runtime selection distinct from the native default;
matching executable names do not imply matching environments or utility semantics.

- 2026-06-22: Narrowed the remaining bug from "Windows verification pending" to
  a concrete `find`-resolution precedence issue.
- 2026-06-22: Updated Windows shell-path shaping so the selected shell's
  `usr/bin` precedes sibling `bin` and Windows system paths, and path reordering
  now deduplicates case-insensitively.
- 2026-06-22: Added focused regression coverage for:
  - `usr/bin` precedence ahead of `C:/Windows/System32`
  - case-insensitive PATH dedup on Windows
  - assistant shell env-merge branch coverage
  - streaming subprocess branch coverage
- 2026-06-22: Local focused verification passes, but a real Windows host still
  needs to confirm that the bound process resolves the intended `find`.
- 2026-08-30: A Windows transcript showed that the selected-executable path
  normalizer manufactured `C:\Windows\usr\bin` and `C:\Windows\bin` for
  native `cmd.exe`, while PowerShell only appeared correct because its
  fabricated paths did not contain `find.exe`. This supersedes the assumption
  that PowerShell rebuilds `PATH` from the registry.
- 2026-08-30: Contract discussion established exact host-environment
  inheritance by default, explicit `inherit`/`replace`/`merge` modes,
  runtime-family fallback, named profiles, and prepend/append path composition
  with deduplication.
- 2026-08-30: Began the implementation slice by removing implicit
  child-executable `PATH` shaping and adding a runtime matrix proving that
  Bash, `cmd.exe`, PowerShell, and Python preserve the host path.
- 2026-08-30: Implemented the explicit environment-policy seam. Bare outer
  executables are resolved through the effective PATH before subprocess launch;
  configured profiles support inherit/replace/merge, exact bindings take
  precedence over family bindings, and PATH prepend/append composition is
  deduplicated with case-insensitive comparison on Windows.

## Evidence audit — 2026-10-30

The October 15 evidence covers native default discovery and explicit WSL/Git
Bash/Windows PowerShell/pwsh execution, cwd, environment, and utility resolution.
The October 30 native full check also passes the runtime matrix (10 tests).

Commit `8bd9769d` and closed task `261029-preserve-literal-shell-argv` record
the missing secondary operator evidence: `/usr/bin/find` emitted GNU find's
`paths must precede expression` diagnostic for `attachments\\.jj`. That identifies
the intended utility already running before the fix. Python-side glob expansion
had replaced the literal `*/.*` predicate argument with filesystem matches;
executable selection was not the cause of that failure.

The fix removes that expansion from assistant argv execution, adds a literal
argument regression, and records successful end-to-end `find . -maxdepth 2
-not -path '*/.*'` execution. Together with the real Windows matrix and today's
green full spine, this satisfies the verification intent. This is secondary
evidence, not a newly captured executable-path trace from the bound process.

Closed after reconciling that evidence. The separate MSYS Vim harness/operator
setup question remains in `261017-msys-vim-native-host`.
