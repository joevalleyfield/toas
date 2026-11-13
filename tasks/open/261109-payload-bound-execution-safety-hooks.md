Filed as: 261109-payload-bound-execution-safety-hooks
FKA:
AKA: payload safety hooks; whole-script safety evaluation; runtime payload evaluation; execution safety callable; grant policy convergence; callable safety hook
Legacy index:

keywords: active, feature, architecture, runtime, policy, safety, execution, grants, contract

Parent: `260803-language-exec-fenced-block-lane`
Related: `260830-exec-grant-policy-matchers`; `261102-executable-policy-module-and-validators`; `260530-shell-lane-spawn-semantics`

# Payload-Bound Execution Safety Hooks and Grant Policy Convergence

## Intent

Unify assistant execution authorization around a first-class payload safety hook capable of inspecting full runtime-bound command and script bodies, eliminating the blind spots of prefix-only token matching and subsuming the fragmented legacy grant system.

## Context & Motivation

TOAS currently enforces assistant execution boundaries through two disconnected mechanisms:
1. **Legacy string grants** (`shell.allowed_commands` / `SHELL_ALLOWED`): parsed via `shell_grants.py` into exact, prefix, or glob matchers.
2. **Post-resolution executable policy** (`ExecutableGrantPolicy` in `.toas/policy.py`): tri-state matchers dispatched by `argv[0]`.

This structure introduces three distinct design and operational friction points:

* **Prefix and token dispatch blind spot**:
  `ExecutableGrantPolicy` is strictly keyed on `prefix = argv[0]`. When evaluating scripted tools (`shell_script`, `python_script`, `powershell_script`, `interpreter_script`), TOAS only passes isolated segment command leaders (`['echo']`, `['git']`) or the launcher binary path (`['/bin/sh']`, `[sys.executable]`). The actual runtime-bound script body is never presented to any policy hook or validator. A policy cannot inspect the script for dangerous patterns, perform AST validation on Python code, or submit the payload to a safety model.

* **Grammar mismatch and false-positive blocks**:
  `ShellScriptCommandSegmenter` attempts to extract command names from arbitrary shell text, but its control/syntax vocabulary is limited to `if, then, elif, else, fi, while, until, do, done`. Common POSIX grouping syntax like `{ ... }` or subshells `( ... )` are misidentified as executable binary names. Because the grant grammar only accepts alphanumeric identifiers (`[A-Za-z0-9._+-]+`), the policy engine disallows `{` with an error indicating an override is needed, yet the grant language possesses no syntax capable of expressing permission for `{`.

* **Fragmented authority and legacy duality**:
  Although `docs/executable-policy.md` specifies that legacy grants are a fallback when no policy module exists, `src/toas/tools.py` continues to evaluate `validate_shell_script_args` and `validate_shell_args` against the legacy allowlist *before* reaching `_authorize_resolved_runtime`. As a result, programmatic policies cannot act as a true middle ground without operators first neutralizing the legacy gate via `glob:*`.

A unified **payload safety hook** resolves these issues by elevating authorization from isolated first-token checks to comprehensive payload inspection. The existing prefix matchers and legacy grants can be cleanly expressed as built-in validators within this hook, providing a smooth path toward deprecating legacy string grants entirely.

## In Scope

- [ ] **Payload Safety Seam**: Define an execution safety evaluation contract in `src/toas/runtime/` that accepts the full runtime-bound payload:
  ```python
  evaluate_payload_safety(tool_name: str, payload: str | Sequence[str], context: ExecutionContext) -> ExecutableGrantDecision
  ```
  with tri-state semantics (`allow`, `deny`, `abstain` / `default`).
- [ ] **Script Body Inspection**: Wire `shell_script`, `python_script`, `powershell_script`, and `interpreter_script` in `src/toas/tools.py` so their entire script body is passed to the safety evaluator prior to subprocess launching.
- [ ] **Full Command Line Inspection**: Wire `shell` calls so both the structured `argv` and the resolved command line are available to safety hooks.
- [ ] **Policy Module Integration**: Extend `.toas/policy.py` discovery (`src/toas/runtime/policy_loader.py`) to support payload evaluators / global safety callables alongside or superseding prefix matchers (e.g. `safety_evaluator` or `payload_matchers`).
- [ ] **Grammar & Syntax Normalization**: Update `ShellScriptCommandSegmenter` in `src/toas/shell_grants.py` to handle POSIX compound grouping (`{`, `}`, `(`, `)`) as syntax rather than command candidates, eliminating false-positive command blocking.
- [ ] **Legacy Seam Convergence**: Resolve the dual-gate sequencing in `src/toas/tools.py` so that an active executable policy / payload hook supersedes the legacy string allowlist rather than being trapped behind it. Implement a legacy grant validator that runs legacy string grants as a standard payload validator for backwards compatibility.
- [ ] **Standard Payload Validators**: Provide built-in payload safety primitives in `src/toas/runtime/matchers.py` (e.g. `deny_script_pattern`, `ast_validate_python`, `require_workspace_paths`).
- [ ] **Unit & Acceptance Coverage**: Add comprehensive tests covering payload evaluation across all script and shell tools while maintaining 100.00% statement coverage under `./scripts/check.sh`.

## Out of Scope

- Modifying user authority bypass: explicit user `$ ...` intent at the frontier remains unbounded and operator-authorized.
- In-process sandboxing of Python interpreters: subprocess isolation and policy gates remain the enforcement boundary.
- Dynamic transcript modification of Python safety callables mid-session.

## Acceptance Criteria

1. A policy module (`.toas/policy.py`) can export a payload safety callable that receives the complete script body for `shell_script`, `python_script`, etc., and can allow, deny, or abstain based on whole-payload analysis.
2. Shell script compound commands (e.g. `{ cmd1; cmd2; }`) are recognized as shell grouping syntax and no longer trigger false-positive `disallows command: {` errors.
3. When an executable policy or payload safety hook is active, it serves as the authoritative execution gate without requiring operators to configure `glob:*` on legacy string allowlists.
4. Legacy string grants remain fully supported as a fallback or standard validator for workspaces without an explicit policy module.
5. All tests pass with 100.00% statement coverage under `./scripts/check.sh`.

## Authorization spike (2026-11-13)

| Lane | Current gate and launch input |
| --- | --- |
| Assistant `shell` | Workspace policy sees normalized argv, then the legacy grant checks the executable token. Both must allow. Cwd, timeout, and environment validation remain in `tools_cluster/shell_ops.py`. |
| Assistant `shell_script` | Legacy checks the parsed segment leaders first. Workspace policy checks each leader and, for an explicit or configured runtime, the launcher argv without the script operand. The system-default launcher is outside that launcher check. |
| Assistant `python_script` / `powershell_script` | Workspace policy checks the explicit, configured, or default launcher. The tool validates and writes the script body to an artifact in its cluster runner after that check. |
| Assistant `interpreter_script` | Workspace policy checks the required explicit launcher. The cluster runner validates and writes the body to an artifact. |
| Direct user shell | `step._execute_user_shell` dispatches to the user branch of `execute_shell_call`, outside both assistant grants. User-owned YAML shell operations also use a separate user-context path. |

The step runtime loads the module in `runtime/step_runtime.py` and threads its
decision policy into the tools facade for assistant execution. Missing module
returns `None`, leaving the legacy gates active for shell and shell scripts.
The module and the effective transcript/config string grants are resolved
independently. The existing shell order is module then legacy, while the
shell-script order is legacy then module. Descriptions above of legacy checks
preceding workspace policy apply to script segments only.

The prefix selector evaluates the requested launcher token. The common process
runner later applies environment policy and resolves a bare executable against
PATH, so the token is not necessarily the filesystem executable ultimately
passed to subprocess. Preserve prefix matching semantics when introducing an
actual resolved launcher field. Queue execution in
`runtime/operator_command_replay.py` also has a direct plan call without a
workspace policy argument. Source-reference authority and queue adoption
require a separate decision; the payload hook must follow the chosen authority
at each entry point.

This slice removes the shell facade's second argv conversion. Workspace
matchers now receive the same normalized arguments that proceed to the legacy
gate and subprocess, including lowercase YAML boolean scalars and empty
positional strings. The public plan regression checks that the matcher and
runner see the same vector. Both existing gates still apply.

### Follow-on implementation order

1. Specify the authority table before changing gates. Decide whether an
   explicit payload decision ends evaluation, what an abstention falls
   through to, and whether transcript grants have an effect under a module.
   Define which queue and source-reference paths execute as assistant.
   Cover combinations of explicit allow, deny and abstain, legacy allow and
   deny, module absence, and direct user authority through public entry points.
2. Bind the normalized payload once per assistant execution. Give shell
   evaluators normalized argv and the resolved executable. Give script
   evaluators the actual body and launcher ahead of artifact creation or
   spawn. Assert on denied calls that no subprocess starts and no script
   artifact is written.
3. Separate POSIX grouping recognition from authorization convergence. Add
   public shell-script tests for grouping around allowed commands and for
   grouping around denied commands. Exercise grouping tokens without changing
   policy authority.
