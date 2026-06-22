Filed as: 260621-windows-shell-launcher-and-path-resolution
FKA:
AKA: windows shell launcher; bash -ic; msys find resolution
Legacy index:

keywords: tooling, implementation, active, compatibility, shell, windows, path

# Windows Shell Launcher And Path Resolution

## Current Reality

The first implementation pass is landed, but it still needs verification on a
real Windows box.

- The shared shell launcher now prefers `bash -lc` instead of `bash -ic` for
  Windows non-TTY subprocess execution.
- Windows shell subprocess environment shaping now prepends `PATH` entries
  derived from the selected shell executable so commands like `find` should
  resolve from the same MSYS/Git-Bash toolchain.
- The legacy launcher duplication in `src/toas/tools.py` has been collapsed
  onto the shared shell launcher.
- The remaining uncertainty is empirical: we have test coverage, but not yet
  confirmation from an actual Windows runtime.

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

## Next Actions

- Verify the launcher and command-resolution behavior on a real Windows host.
- Confirm that `find` resolves to the intended MSYS/Git-Bash binary in the
  bound stdio TOAS process, not just in isolated tests.
