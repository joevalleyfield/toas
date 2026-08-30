Filed as: 260829-executable-fence-activation
FKA:
AKA: fence potency classifier; executable fence activator; explicit exec marker
Legacy index:

keywords: runtime, implementation, active, correctness, tooling, frontier, provenance

Parent: `260803-language-exec-fenced-block-lane`
Depends on: `260829-markdown-fence-scanner`
Related: `260829-action-plan-envelope`; `260803-tool-intent-ingress-separation`

# Executable Fence Activation Classification

Classify structurally scanned fences as explicitly active, inert, unsupported,
or malformed without parsing or executing their bodies.

## Scope

- recognize the overt `<language> exec` activation form;
- normalize registered language aliases;
- let explicit inert forms and non-active `toas-output` fences win;
- leave unknown languages unsupported and inert;
- return activation provenance for later lane routing;
- add focused precedence and malformed-input tests.

## Non-Goals

- parsing YAML, JSON, call expressions, or interpreter source;
- invoking subprocesses or capabilities;
- changing existing YAML extraction behavior;
- deciding authority or arbitration;
- adding proxy-specific fallback activators.

## Acceptance

- one lane-neutral activation result shape exists;
- explicit active, inert, unsupported, and malformed outcomes are distinct;
- unknown languages never become host executable names;
- existing scanner and current extraction tests remain green;
- completion evidence records deferred structural activation and routing.

## Outcome

Implemented lane-neutral `FenceActivation` classification over the shared
Markdown scanner. Registered language aliases with an exact `exec` marker are
active; ordinary fences, explicit inert forms, and `toas-output` remain inert;
unknown or extra-token forms are unsupported; missing structure is malformed.
No body parser, authority decision, or execution path was added.

Verification:

- `./.codex-local/bin/uvt run pytest tests/test_runtime_fence_activation.py tests/test_runtime_markdown_fence.py tests/test_shell_intent.py tests/test_graph.py -q --no-cov` (`182 passed`)
- `./.codex-local/bin/uvt run ruff check src/toas/runtime/fence_activation.py tests/test_runtime_fence_activation.py`

Parser, lane registry, proxy-compatible fallback activation, and runtime
routing remain deferred to subsequent executable-fence follow-ons.
