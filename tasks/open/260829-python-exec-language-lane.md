Filed as: 260829-python-exec-language-lane
FKA:
AKA: python exec; Python executable fence; language runtime pathfinder
Legacy index:

keywords: runtime, implementation, active, correctness, python, tooling, shell

Parent: `260803-language-exec-fenced-block-lane`
Depends on: `260829-structured-fence-toolset-provenance`; `260530-shell-lane-spawn-semantics`
Related: `260829-action-plan-envelope`; `260829-bash-exec-fence-lane`; `260621-windows-shell-launcher-and-path-resolution`

# Python Executable Fence Lane

Make `python exec` the first non-shell executable language lane while keeping
language parsing separate from runtime selection, authority, and artifact
lifetime.

## Intent

Recognize Python source as an explicit executable request and run it through a
child Python process with the existing authority, workspace, subprocess,
result, and durable-history semantics.

## Surface

```text
```python exec [runtime=<invocation>] [cwd=<path>]
<Python source>
```
```

Execution artifact options are available as declarative attributes:

```yaml
persist: false
path: "./script###.py"
overwrite: false
```

The default execution is ephemeral. `path` names the generated script file
relative to `cwd`; `###` is an optional generated collision-resistant suffix.
`persist=true` retains the file. `overwrite=true` is legal only with
`persist=true` and explicitly replaces an existing target.

## Runtime resolution

- explicit `runtime` names an argv invocation and is strict: unavailable
  runtimes produce an error and do not fall back;
- omitted `runtime` resolves through the configured Python runtime and then a
  system-hardcoded Python backstop;
- runtime invocations are argv vectors, not shell command strings;
- record requested runtime, effective argv, and resolution source in durable
  metadata.

## Directory and authority

- omitted `cwd` inherits the current `/cd` or startup directory;
- relative `cwd` and `path` resolve from the inherited/current `cwd`;
- user execution may use any existing directory permitted by the operating
  system and current user semantics;
- assistant execution validates `cwd` and persisted artifact destinations
  against the configured workspace policy;
- user and assistant lanes retain their existing authority profiles and
  explicit `step` roundtrip;
- `toolset` is absent for the Python language lane; no TOAS modules or public
  APIs are implicitly imported into the script.

## Execution and artifacts

- write the source to a temporary `.py` file in the resolved `cwd`;
- execute the selected runtime against that file with the shared subprocess
  result and stream policy;
- remove the file after execution unless `persist=true`;
- create files exclusively by default and never silently overwrite;
- do not add backup/restore behavior;
- preserve the transcript as the canonical source for replay.

## Non-Goals

- executing Python in-process or with `eval`;
- implicit TOAS imports, tool injection, or a Python-specific toolset;
- automatic fallback from an explicitly named runtime;
- changing Bash’s default direct shell execution;
- implementing PowerShell, Node.js, or other language lanes;
- adding a new authority or policy model;
- making persisted artifacts canonical history in place of the transcript.

## Acceptance

- active `python exec` fences become one normalized Python execution request;
- ordinary `python` fences and explicitly inert fences remain inert;
- unavailable or unsupported Python runtimes produce an explicit error rather
  than falling through to LLM generation;
- configured-runtime and system-backstop resolution are distinguishable;
- `cwd` inheritance, relative resolution, and assistant workspace validation
  are test-covered;
- ephemeral, persisted, generated-name, exact-name, and overwrite cases are
  test-covered without backup semantics;
- stdout, stderr, timeout, nonzero exit, and missing-runtime results use the
  existing subprocess/result contracts;
- toolset remains absent and no TOAS API is imported implicitly;
- requested/effective runtime, resolved cwd, and artifact metadata are durable
  without changing the callable payload shape;
- existing Bash, YAML, JSON, operator, and LLM fallback behavior remains
  green.

## Allowed Write Surfaces

- the executable-fence lane registry and runtime dispatch seam;
- a language-runtime adapter near `src/toas/tools_cluster/` or the established
  runtime ownership boundary;
- focused tests under `tests/`;
- this task file and generated `tasks/WORKBOARD.md` sections.

## Open Decisions

- the configured Python runtime key and system backstop executable;
- the exact normalized capability name (`python_script` is provisional);
- whether artifact attributes live in fence info metadata or a structured
  execution envelope while preserving the source surface above.

## Progress

- 2026-08-29: Initial implementation slice landed. Active `python exec` fences
  normalize to `python_script`, execute through an ephemeral `.py` file in the
  resolved current directory, use the shared subprocess runner, and clean up
  the file afterward. Parser, registry, execution, cleanup, and arbitration
  coverage are green.
- Remaining in this task: explicit/configured runtime resolution, fence-level
  `cwd`, `path`, `persist`, and `overwrite` attributes, and durable execution
  metadata. These remain deliberately separate from the working first lane.
- 2026-08-29: Registered `python_script` with the stream-preserving result
  renderer so nonzero execution results retain captured stdout and stderr in
  the projected UI output.
- 2026-08-29: Added quoted fence attributes for explicit runtime argv and
  `cwd`; `python_script` now accepts those values while retaining the current
  Python executable as the local default. Persistence and overwrite remain
  the next artifact slice.

## Progress

- 2026-08-29: Claimed for implementation. The first slice will use the
  existing runtime configuration and subprocess ownership seams, retaining
  the provisional `python_script` capability name unless code evidence
  requires a narrower compatibility choice.
