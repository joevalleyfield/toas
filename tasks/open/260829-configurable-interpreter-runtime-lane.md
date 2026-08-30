Filed as: 260829-configurable-interpreter-runtime-lane
FKA:
AKA: configured interpreter runtime; powershell exec; open language runtime set
Legacy index:

keywords: runtime, implementation, active, config, tooling, language, powershell

Parent: `260803-language-exec-fenced-block-lane`
Depends on: `260829-executable-fence-activation`; `260829-python-exec-language-lane`
Related: `260829-bash-exec-fence-lane`; `260829-action-plan-envelope`

# Configurable Interpreter Runtime Lane

Add configuration-driven interpreter resolution for executable language fences
and make PowerShell the next registered non-shell language lane.

## Intent

Let the language marker identify source syntax while configuration identifies
the process that executes it. Support an open set of explicitly configured
languages without treating every language tag as an executable host command.

## Desired Outcome

These fences use the same recognition, authority, execution, durable-result,
and projection path:

````markdown
```powershell exec
Write-Output "Hi Mom!"
```
````

The active configuration supplies the runtime mapping:

```yaml
languages:
  python:
    runtime: python
  powershell:
    runtime: pwsh
  ruby:
    runtime: ruby
```

The exact configuration nesting may follow the existing configuration model,
but the semantic distinction is fixed: language selects the lane; runtime
selects the interpreter invocation.

## Runtime Resolution

Resolution follows this hierarchy:

```text
explicit runtime override, if supported
  > configured runtime for the language
  > system backstop for a built-in language
  > unsupported or unconfigured language
```

An explicitly named runtime is authoritative. If it cannot be resolved, the
request fails closed with a runtime-resolution error. It must not silently fall
back to another executable, invoke the LLM, or change the language meaning.

An unregistered language becomes executable when the active configuration
supplies its runtime mapping. Without that mapping it remains unsupported or
inert according to the existing executable-fence diagnostic policy.

Runtime resolution must preserve the existing `cwd` semantics. In assistant
scope, the selected working directory remains workspace-validated; in direct
user scope, existing user authority semantics remain unchanged.

## Scope

- define the configuration mapping from language name to runtime invocation;
- resolve configured runtimes and report missing executables explicitly;
- preserve the distinction between language syntax and runtime selection;
- register and execute PowerShell through the shared executable-language path;
- retain the existing temporary-file default and `persist`/`path` behavior;
- preserve stdout, stderr, exit status, timeout, cancellation, and artifact
  details on success and failure;
- add focused guardrails for configured, backstop, missing, and unconfigured
  runtime cases.

## Non-Goals

- arbitrary inline process construction as the primary fence surface;
- implicit imports of `toas.public_tool_api` or another TOAS toolset;
- changing direct-user or assistant authority policy;
- changing Bash execution semantics;
- adding PowerShell-specific tool calling;
- implementing additional language lanes beyond the PowerShell path;
- silently falling back from an explicitly named runtime.

## Acceptance Criteria

- [ ] A configured language resolves its configured runtime without requiring a
  runtime attribute in the fence.
- [ ] An unconfigured language does not execute merely because its tag names a
  plausible host executable.
- [ ] An explicitly named runtime, if supported by the final surface, takes
  precedence over configuration and fails closed when unavailable.
- [ ] Built-in runtime backstops are used only when no explicit or configured
  runtime exists.
- [ ] Runtime-not-found evidence identifies the requested language/runtime and
  does not invoke a substitute runtime or the LLM.
- [ ] PowerShell executes through the shared language-fence authority,
  validation, execution, durable-result, and projection seams.
- [ ] PowerShell uses the configured `cwd`, temporary execution by default,
  and the existing persistence/path controls.
- [ ] PowerShell success and failure preserve stdout and stderr separately,
  including non-zero exits.
- [ ] Assistant-scope PowerShell receives workspace validation and configured
  assistant policy; direct-user PowerShell retains direct-user semantics.
- [ ] Runtime resolution and PowerShell behavior have focused tests covering
  success, missing runtime, non-zero exit, stderr, cwd, and persistence.
- [ ] Existing language-fence, Bash, Python, and full-suite guardrails remain
  green.

## Required Completion Evidence

- runtime configuration examples and precedence table;
- resolution results for configured, backstop, missing, and unconfigured cases;
- PowerShell success/failure projections with separate stdout/stderr;
- cwd and persistence examples;
- authority-path and no-fallback guardrail tests;
- focused coverage plus full-suite verification.

## Allowed Write Surfaces

- `src/toas/runtime/` and the language-runtime ownership selected by the
  existing runtime-ownership guide;
- configuration parsing/resolution modules required by that seam;
- focused runtime, configuration, and executable-fence tests;
- this task file and mechanically generated `tasks/WORKBOARD.md` sections;
- narrowly related documentation when implementation changes make a current
  runtime contract inaccurate.

## Open Decisions

- deferred: whether one-off explicit runtime overrides belong in the fence
  syntax or only in configuration;
- delegated: the exact argv shape for PowerShell on each supported platform;
- delegated: the system backstop executable names, provided they never
  override an explicit or configured runtime failure.
