# Selectable Shell Runtime

Filed as: 261015-selectable-shell-runtime
FKA:
AKA: runtime.shell_runtime; choose sh executable; per-call shell interpreter
Legacy index:

keywords: tooling, implementation, active, compatibility, shell, runtime

Parent: `261015-windows-compatibility-restoration`
Related: `260621-windows-shell-launcher-and-path-resolution`

Status: CLOSED 2026-10-15; configured and per-call shell argv prefixes implemented

## Contract

The operator must be able to choose `/bin/sh` versus
`/opt/openai_s_own_sh/bin/sh`, independently of automatic discovery and PATH.
Add `runtime.shell_runtime` as an argv prefix, including command-mode flags.
An empty default preserves automatic selection. Shell-script calls may override
with `runtime: [...]`; the script is appended as one argument. Explicit or
configured missing executables fail rather than silently selecting another.
Keep environment profiles independent, direct executable argv unchanged, and
assistant runtime authorization intact. Apply the project choice to shell-script
execution and user commands that require a shell. Advertise and document the
new affordance; verify precedence, validation, actual execution, and coverage.

## Implementation and Verification

- Added the typed config field, quoted-argv string parsing, project-file
  discovery, and a scoped effective-runtime context so transcript config
  overrides reach both user and assistant execution.
- `shell_script` accepts an advertised per-call `runtime` argv prefix;
  executable shell fences forward it too. Per-call wins over config; empty
  config retains automatic discovery. Missing selections fail without fallback.
- User shell-script execution no longer hardcodes `sh -lc` or reparses a fully
  constructed argv as a second shell command. Direct argv remains literal;
  configured shell choice applies where a shell is actually needed.
- Validation covers malformed prefixes, quoted paths, script-as-one-argument,
  precedence, config restoration, missing executables, and assistant runtime
  authorization. No runtime-name migration was attempted.
- 684 tests passed in the broad config/tool/step/fence run before the final
  quoted-fence and transcript-override regressions were added. Those final
  regressions passed in a further 70-test run.
- Targeted shell selection coverage: 193 tests passed, 286 statements, 100%,
  zero missing files across `runtime.shell_runtime` and `tools_cluster.shell_ops`.
- Actual `python -m toas step` in a temporary workspace used a configured
  absolute Git Bash prefix, emitted `configured-shell-ok` in an inert stdout
  block, and advertised the new key through `/help config runtime`.
- Changed-file Ruff passes. Mypy reports the six existing Windows journal-lock
  errors only; corrected the earlier pipe reader's IO annotation mismatch.
- Full-suite Git Bash run: 3,524 passed, 38 failed, 9 skipped, 17 deselected;
  coverage 99.90%, with missing statements confined to the existing daemon
  lifecycle, state-execution experiment, and journal-lock modules. A
  PowerShell-launched attempt exited early without a summary.
- One full-run failure was the intentional shell-script prompt signature change;
  inspected the actual prompt and updated its single golden signature line.
  Other failures belong to state-execution experiments, task capture, and the
  known POSIX-only Vim harness. The master retains these open.
- Rechecked pipe-reader/client and runtime matrix after the IO annotation
  correction: 110 passed. Full-suite aggregates above are the recorded run,
  not a claimed green result after the golden update.
- Final config, prompts, tools, step/replay, fence, selection, and help run:
  **786 passed** after the golden correction. Changed-file Ruff passed.
