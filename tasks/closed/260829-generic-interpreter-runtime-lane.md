Filed as: 260829-generic-interpreter-runtime-lane
FKA:
AKA: open interpreter set; bc exec; explicit runtime language lane
Legacy index:

keywords: runtime, implementation, active, config, tooling, language, interpreter

Parent: `260803-language-exec-fenced-block-lane`
Depends on: `260829-configurable-interpreter-runtime-lane`; `260829-executable-fence-activation`
Related: `260829-python-exec-language-lane`; `260829-bash-exec-fence-lane`

# Generic Interpreter Runtime Lane

Allow an otherwise unregistered executable language fence to run through a
generic interpreter path when, and only when, it names an explicit runtime.

## Intent

Make the open set useful without making language tags executable by implication.
The motivating example is `bc`:

````markdown
```bc exec runtime=bc
scale=4
1 / 3
```
````

`bc` identifies the source language and `runtime=bc` identifies the process.
An unconfigured `bc exec` remains unsupported.

## Resolution Rule

```text
registered language + configured runtime → registered lane
unregistered language + explicit runtime → generic interpreter lane
unregistered language without explicit runtime → unsupported
```

An explicit runtime is strict. If it cannot be resolved, the request fails
closed and does not fall back to a configured runtime, another executable, or
LLM generation.

## Scope

- permit unknown language tags to activate only when `runtime=...` is present;
- normalize them into one generic interpreter capability;
- preserve language, runtime, `cwd`, temporary artifact, persistence, overwrite,
  timeout, cancellation, stdout/stderr, and result metadata;
- route the generic capability through the shared authority and subprocess
  seams;
- keep ordinary and unconfigured language fences inert or unsupported;
- use `bc` in deterministic tests through an injected or portable stand-in,
  not as a suite dependency.

## Non-Goals

- inferring an executable from a language tag;
- configuration-driven arbitrary maps in this first generic slice;
- implicit TOAS imports or toolsets;
- shell evaluation or shell command interpolation;
- changing registered Python or PowerShell behavior;
- making `bc` a hard dependency of the test suite.

## Acceptance Criteria

- [ ] `bc exec runtime=bc` becomes one generic interpreter request.
- [ ] `bc exec` remains unsupported and does not fall through to generation.
- [ ] Explicit runtime argv parsing preserves quoted arguments.
- [ ] Missing explicit runtimes fail closed without fallback.
- [ ] Generic execution preserves the shared cwd, artifact, authority, and
  result contracts.
- [ ] Language and runtime identity are present in request/result metadata and
  are not hidden in arbitrary shell syntax.
- [ ] Deterministic tests cover success, missing runtime, stderr/non-zero exit,
  temporary cleanup, persistence, and no-runtime rejection without requiring
  `bc` or another optional interpreter.
- [ ] Existing Python, PowerShell, Bash, structured-callable, and full-suite
  guardrails remain green.

## Allowed Write Surfaces

- executable-fence recognition and generic interpreter dispatch;
- the established script/interpreter runtime seam under `src/toas/tools_cluster/`;
- focused executable-fence, runtime, and registry tests;
- this task file and generated `tasks/WORKBOARD.md` sections.

## Progress

- 2026-08-29: Task opened and claimed for implementation.
- 2026-08-29: Implemented the generic explicit-runtime interpreter lane.
  Unknown language fences such as `bc exec runtime=bc` now normalize to the
  shared `interpreter_script` capability, while `bc exec` remains unsupported.
  Runtime resolution is strict, with no shell or LLM fallback; language,
  runtime, cwd, artifact, and result metadata remain explicit.
- 2026-08-29: Added deterministic tests using the Python executable as a
  portable stand-in for generic interpreter behavior. The full suite passes
  with 3,013 tests passed, 9 deselected, and 100% coverage; Ruff passes.

## Outcome

Closed on 2026-08-29. The open-set rule is now implemented for explicit
runtime fences. Registered languages retain their lane-specific resolution;
unregistered languages require `runtime=...` and enter the shared generic
interpreter path. Optional interpreters such as `bc` are not test dependencies.
