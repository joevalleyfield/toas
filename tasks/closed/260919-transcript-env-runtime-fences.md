Filed as: 260919-transcript-env-runtime-fences
FKA:
AKA: env set executable fences; runtime fence environment; fence environment parity; windows fence env
Legacy index:

keywords: runtime, implementation, active, correctness, contract, environment, transcript, fence, parity, windows

Parent: `260803-language-exec-fenced-block-lane`
Related: `310-transcript-env-modifiers-as-execution-surface`; `260831-preserve-exec-fence-path`; `260903-user-lane-timeout-recovery`

# Apply Transcript Environment Modifiers to Runtime Fences

Make transcript-scoped `/env set` and `/env unset` modifiers apply to every
runtime executable-fence lane with the same durable, ordered semantics already
used by direct user shell execution.

## Current Reality

`resolve_effective_env_modifiers()` correctly collects user-authored `/env`
directives and the direct user shell path passes them as environment overrides.
The general executable-plan path receives those modifiers as
`default_shell_env`, but applies them only to the `shell` tool. Runtime
executable fences map to `shell_script`, `python_script`,
`powershell_script`, or `interpreter_script`, whose runners instead begin from
the ambient `os.environ`.

As a result, with a host value of `TOAS_ENV_TEST=host-value` and a preceding
`/env set TOAS_ENV_TEST transcript-value`, a direct `python exec` fence prints
`host-value`. This is a lane-parity defect, not a Windows-only behavior,
although it is particularly visible for Windows runtime setup.

The closed `260831-preserve-exec-fence-path` slice already fixed a distinct
bug: process-environment/PATH inheritance must be retained when an execution
path receives a partial override mapping. This follow-on must preserve that
contract and Windows alias normalization; it must not replace the effective
environment with transcript modifiers alone.

## Desired Reality

For every executable-fence runtime, the process environment is resolved as:

```text
host process environment
  + ordered transcript /env set and /env unset modifiers
  + configured environment-policy merge/replace behavior
  -> selected executable fence process
```

The same execution context reaches direct user fences and selected
assistant-source `/run` fences. A modifier is not silently limited to the
loose `$ ...` shell lane merely because the operator used a fence.

## Scope

- Thread the resolved transcript environment through the shared executable-plan
  boundary without a shell-specific name or restriction.
- Apply it to Bash, Python, PowerShell, and generic interpreter executable
  fences, including selected assistant source run by `/run`.
- Preserve ordered set/unset behavior, host-environment inheritance, explicit
  environment-policy semantics, and Windows case/alias handling.
- Add focused regression coverage at the runtime and subprocess seams.

## Non-goals

- Adding an `env` fence-header attribute or a new environment syntax.
- Changing the authority, timeout, recovery, or source-materialization policy
  of executable fences.
- Reopening the completed inherited-PATH fix except where its regression
  evidence must be extended to the shared contract.

## Acceptance Evidence

- A preceding `/env set TOAS_ENV_TEST transcript-value` overrides an inherited
  `TOAS_ENV_TEST=host-value` inside direct Bash, Python, PowerShell, and
  generic-interpreter executable fences.
- `/env unset TOAS_ENV_TEST` removes an inherited value for those same fence
  paths.
- The equivalent selected assistant source executed with `/run` observes the
  same resolved modifiers.
- A partial modifier mapping retains unrelated inherited variables, especially
  `PATH`; configured environment-policy `replace` behavior remains the sole
  way to intentionally omit inherited values.
- Windows-focused mocked coverage proves the resolved fence environment keeps
  canonical aliases and case-insensitive PATH behavior.
- Focused runtime/tool coverage and the full suite pass; record the owner
  seam, fixtures, verification commands, and commit in this task.

## Likely Ownership

- Execution-context adaptation: `src/toas/tools_cluster/execution.py` and
  `src/toas/tools.py`.
- Runtime fence subprocess runners: `src/toas/tools_cluster/shell_ops.py`,
  `python_ops.py`, `powershell_ops.py`, and `interpreter_ops.py`.
- Transcript environment resolution and end-to-end coverage:
  `src/toas/step.py` and the existing step/runtime tool test modules.

## Next Actions

1. Add a failing direct Python-fence test that distinguishes the host value
   from a prior `/env set` value, then repeat the contract for each runtime
   family using mocked launchers where platform runtimes are unavailable.
2. Rename or replace the shell-only execution-environment adapter parameter
   with a shared process-environment overlay, and thread it to every runtime
   subprocess runner.
3. Add `/env unset`, `/run`, inherited-PATH, and Windows-normalization
   regressions; verify configured environment policy continues to compose only
   after the transcript overlay is resolved.

## Status

Closed: 2026-09-19

## Progress

- 2026-09-19: Added a shared process-environment overlay context at the
  executable-plan boundary. Host inheritance is retained, ordered transcript
  set/unset modifiers are applied before Windows normalization, and configured
  environment policy still composes afterward. The legacy shell-named keyword
  remains accepted as a compatibility alias while `default_process_env` is the
  shared owner-facing parameter.
- 2026-09-19: Added direct shell-script, Python, generic-interpreter, and
  PowerShell-runner coverage, plus unset, inherited-PATH, replace-policy, and
  mocked Windows case-insensitive environment regressions. `/run` uses the same
  `_execute_plan` boundary and therefore receives the overlay.
- 2026-09-19: Verification passed: focused runtime/tool tests (577 passed),
  full suite (3,240 passed, 17 deselected, 100% coverage), and Ruff checks.
