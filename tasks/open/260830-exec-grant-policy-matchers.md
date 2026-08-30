Filed as: 260830-exec-grant-policy-matchers
FKA:
AKA: executable grants; runtime grant policy; prefix matcher policy; interpreter authorization
Legacy index:

keywords: runtime, config, implementation, active, authority, boundaries, policy, shell, defaults, correctness

Parent: `260803-language-exec-fenced-block-lane`
Related: `260530-shell-lane-spawn-semantics`; `260829-configurable-interpreter-runtime-lane`; `260829-generic-interpreter-runtime-lane`

# Central Executable Grant Policy And Matchers

Create the shared post-resolution authorization seam for assistant-directed
executable runtimes. The seam should let user-owned policy express ordered
allow or deny behavior without creating separate policy implementations for
shell, Python, PowerShell, generic interpreters, or future executable lanes.

## Intent

Assistant execution should be governed by a user-configurable policy over the
fully resolved executable invocation. Direct user execution remains
intentionally unbounded and does not enter this evaluator.

The first implementation should establish the callable evaluator machinery
without solving open-ended user module discovery. Policy callables may be
built-in or supplied by tests/internal configuration while the designated
user policy-module surface remains deferred.

## Provisional model

The policy has a default decision and ordered matcher sequences selected by the
first executable argument:

```python
policy = {
    "default": "deny",
    "prefix_matchers": {
        "uv": [deny_network, allow_all],
        "jj": [allow_all],
    },
}
```

Each matcher receives the complete resolved `argv` and returns:

- `True`: allow and stop evaluating;
- `False`: deny and stop evaluating;
- `None`: abstain and continue to the next matcher.

When the selected sequence is exhausted, its policy default applies. This
supports allowlists (`default="deny"`) and blacklist-style policies (explicit
denials followed by `allow_all`, or a broader `default="allow"`) without
separate evaluator concepts.

## Scope

- Define a small internal policy/evaluator shape for resolved executable
  invocations.
- Apply the evaluator after runtime resolution and before subprocess launch.
- Route shell and language/interpreter execution through the shared seam.
- Preserve explicit runtime resolution and existing direct-user semantics.
- Record the effective authorization decision and resolved invocation in the
  durable tool evidence where the existing record shape permits it.
- Keep matcher execution trusted and ordinary Python; do not invent a DSL,
  transcript-supplied code path, or sandboxing mechanism in this task.

## Deferred

- Discovery/import of a user-designated policy module.
- A broader policy language or configuration UI.
- Sandboxing or containing trusted user-authored matcher code.
- Generalizing policy evaluation to LLM endpoint selection or unrelated
  capabilities.
- Reworking direct-user execution bounds; those remain intentionally
  unbounded unless a concrete use case appears.

## Acceptance criteria

- A resolved assistant executable invocation passes through one shared
  authority/evaluator seam regardless of whether it originated as shell,
  Python, PowerShell, or a generic interpreter request.
- Matcher sequences are evaluated in declaration order and short-circuit on
  the first non-`None` result.
- Prefix dispatch is an index, not a second authorization rule; an unmatched
  prefix falls through to the configured default.
- Both allowlist and blacklist-shaped policies are covered by tests,
  including deny matchers followed by `allow_all` under `default="deny"`.
- Assistant policy remains bounded by default, with an explicit unbounded
  assistant setting preserved as a user-configurable choice if already
  supported by the relevant policy surface.
- Direct user execution remains outside the matcher evaluator and retains its
  intentional unbounded behavior.
- Assistant-supplied runtime descriptors cannot supply, replace, or evaluate
  matcher code.
- Denials are visible in the existing result/error projection and durable
  evidence rather than appearing as an unexplained subprocess failure.
- Targeted tests and the full required check set pass with the repository’s
  coverage gate intact.

## Likely ownership

The evaluator belongs in `src/toas/runtime/` with authority/policy resolution.
Tool behavior remains in `src/toas/tools_cluster/`; the public registry in
`src/toas/tools.py` should only route resolved requests through the shared
seam. Configuration should carry policy data and references, not executable
transcript content.

## Open decisions for implementation

- Exact names and module placement for the evaluator and policy types.
- The durable field names for policy identity and effective decision.
- Whether the first internal matcher registry is a small explicit mapping or
  a directly constructed test/config object.

## Completion evidence

The implementing change should update this task with the final evaluator
shape, the deliberate treatment of deferred user-module loading, test
commands/results, and the closing commit.

## Progress

- 2026-08-30: First implementation slice landed as
  `src/toas/runtime/executable_grants.py`. It provides a trusted callable
  matcher type, exact first-argv prefix dispatch, ordered tri-state
  short-circuiting, configurable boolean fallthrough, and an explicit
  decision record. Focused tests cover allowlist, blacklist, `allow_all`,
  unmatched prefixes, validation, and short-circuit behavior. Execution-layer
  integration and user policy-module discovery remain for subsequent slices.
- 2026-08-30: Focused tests and targeted 100% coverage pass. The full suite
  reached 100% coverage with 3018 tests passing; three Vim/plugin checks were
  blocked by the ordinary sandbox rather than failing product behavior. Full
  checks should elevate `scripts/check.sh` and the subprocesses it invokes.
  The task remains open for the execution-layer integration slice.
