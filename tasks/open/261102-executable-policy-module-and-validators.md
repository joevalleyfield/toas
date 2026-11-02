Filed as: 261102-executable-policy-module-and-validators
FKA:
AKA: user policy module; policy discovery; executable validators; standard matchers; policy.py
Legacy index:

keywords: runtime, policy, authority, matchers, validators, config, discovery, execution

Parent: `260803-language-exec-fenced-block-lane`
Related: `260830-exec-grant-policy-matchers`; `261030-namespaced-config-policy-coalescence`

# User Executable Policy Module Discovery And Standard Matcher Library

Connect the central post-resolution executable grant evaluator to user-authored
policy by establishing a discovery convention for workspace policy modules and
providing a library of reusable, composable validator matchers.

## Intent

`260830-exec-grant-policy-matchers` established the shared runtime authorization
seam and tri-state evaluator (`ExecutableGrantPolicy`), but deliberately deferred
user policy module discovery and validator design.

Currently, matchers are trusted Python callables wired in internal tests or
synthesized from legacy string grants (`exact`, `prefix`, `glob`). To make this
power genuinely usable by human operators and repository owners, TOAS needs:

1. A clear discovery and loading convention for user/workspace policy modules
   (e.g., `.toas/policy.py` or configured path in `toas.toml`).
2. A clean, idiomatic export contract for user policy definitions.
3. A standard library of composable validator primitives for common security
   rules (flag denials, subcommand filtering, read-only constraints) without
   requiring operators to write raw boilerplate.

## Scope

- Define the discovery convention for a workspace policy module (defaulting to
  `.toas/policy.py` with an optional `runtime.policy_module` config override).
- Define the module export contract: the module may export an
  `ExecutableGrantPolicy` instance, a mapping of prefix matchers, or a factory
  function accepting active workspace configuration.
- Keep execution trusted Python: import the module using standard Python import
  mechanisms; do not invent an ad-hoc DSL or execute transcript code.
- Implement a focused library of reusable matchers/validators in
  `src/toas/runtime/matchers.py`:
  - `deny_flags(*flags)` (e.g. `--network`, `--force`, `-f`)
  - `allow_subcommands(*subcommands)` (e.g. `status`, `diff`, `log`)
  - `deny_subcommands(*subcommands)` (e.g. `push`, `publish`, `reset`)
  - `allow_all` / `deny_all`
- Wire policy resolution into `src/toas/runtime/step_runtime.py` so the active
  policy is instantiated once per step execution and passed to `_execute_plan`.
- Expose policy and active matcher names in capability inspection and help views
  (`/help capabilities`, `/config show`).

## Non-Goals & Deferred

- Sandboxing or containing trusted user policy code: policy modules remain trusted
  developer/repository code, running in-process with ordinary Python semantics.
- Non-Python policy languages or complex declarative rule DSLs in TOAS config.
- Dynamic transcript modification of Python matcher functions.

## Acceptance Criteria

- A workspace containing `.toas/policy.py` has its policy loaded and applied to
  assistant executable tool calls (`shell`, `shell_script`, `python_script`,
  `powershell_script`, `interpreter_script`).
- When no policy module exists, execution falls back cleanly to the existing
  legacy grant policy behavior (`shell.allowed` grants).
- Standard matcher primitives (`deny_flags`, `allow_subcommands`,
  `deny_subcommands`) correctly short-circuit or abstain according to the
  tri-state contract.
- Direct user execution continues to intentionally bypass policy evaluation.
- Syntax or import errors in user policy modules produce clear diagnostic errors
  rather than silent execution or unhandled tracebacks.
- Full test suite passes at 100.00% statement coverage.

## Likely Ownership

- Evaluator and matcher primitives: `src/toas/runtime/executable_grants.py`,
  `src/toas/runtime/matchers.py`.
- Module loading & policy resolution: `src/toas/runtime/policy_loader.py` or
  `src/toas/runtime/step_runtime.py`.
- Capability exposure: `src/toas/tools_cluster/capability_help_ops.py`.

## Progress

- 2026-11-02: Task opened as the direct follow-on to
  `260830-exec-grant-policy-matchers` to bridge the internal evaluator engine
  with user policy discovery and composable matcher primitives.
