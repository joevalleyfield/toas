Filed as: 260621-windows-shell-launcher-and-path-resolution
FKA:
AKA: windows shell launcher; bash -ic; msys find resolution
Legacy index:

keywords: tooling, implementation, active, compatibility, shell, windows, path

# Windows Shell Launcher And Path Resolution

## Current Reality

The first implementation pass is landed, but one Windows tool-resolution seam
is still open and the result still needs verification on a real Windows box.

- The shared shell launcher now prefers `bash -lc` instead of `bash -ic` for
  Windows non-TTY subprocess execution.
- Windows shell subprocess environment shaping now prepends `PATH` entries
  derived from the selected shell executable, but local operator evidence still
  suggests `find` can resolve from the wrong neighborhood.
- The legacy launcher duplication in `src/toas/tools.py` has been collapsed
  onto the shared shell launcher.
- The remaining uncertainty is now narrower: we need both a code-level fix for
  `find` precedence and a real Windows verification pass afterward.

## Desired Reality

Windows shell execution should be non-interactive by default and should resolve
commands from the same shell toolchain that TOAS selected to launch the shell.

## Known Facts

- `src/toas/tools_cluster/shell_ops.py` owns the shared shell launcher used by
  user-shell execution.
- `src/toas/tools.py` now delegates `_shell_launcher_argv(...)` to the shared
  cluster implementation used by user-shell execution.
- Regression coverage now expects `bash -lc` on Windows launcher paths and
  asserts Windows `PATH` seeding from the selected shell executable.

## Decisions

- Prefer `bash -lc` instead of `bash -ic` for non-TTY Windows subprocess work.
- Seed Windows subprocess `PATH` from the chosen shell executable so adjacent
  shell tools resolve consistently.
- Collapse the legacy launcher facade onto the shared cluster implementation.

## Progress Notes

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

## Next Actions

- Prefer the selected shell's Unix userland path entries ahead of Windows
  system paths when shaping subprocess `PATH`.
- Verify the launcher and command-resolution behavior on a real Windows host.
- Confirm that `find` resolves to the intended MSYS/Git-Bash binary in the
  bound stdio TOAS process, not just in isolated tests.
