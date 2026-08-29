Filed as: 260829-action-plan-envelope
FKA:
AKA: canonical action plan; plan provenance envelope; tool request plan context
Legacy index:

keywords: runtime, implementation, active, maintainability, correctness, provenance, frontier

Parent: `260829-canonical-action-ingress-contract`
Depends on: `260829-compound-tool-request-records`
Related: `260803-tool-intent-ingress-separation`

# ActionPlan Envelope

Introduce a narrow `ActionPlan` envelope at the recognition/arbitration
boundary so plan-level provenance travels with ordered inert `ToolRequest`
values without changing capability inputs.

## Scope

- represent one recognized plan and its ordered normalized request list;
- carry origin, ingress, source, and selection position when available;
- preserve the existing list-of-dictionaries serialization at execution and
  durable-history boundaries;
- make the envelope inspectable and inert;
- add focused construction, serialization, and runtime hand-off tests.

## Non-Goals

- changing capability execution or authority resolution;
- adding policy, status, result, or retry fields to the plan;
- implementing native, JSON, or executable-fence ingress;
- requiring every provenance field to be present for current text lanes;
- replacing all dictionaries in one migration.

## Acceptance

- recognized plans can carry provenance without placing it in capability args;
- execution receives the unchanged normalized request list;
- single and compound durable payloads remain readable;
- missing optional source context is representable without fabricated values;
- focused tests and relevant regression tests pass;
- completion evidence records the boundary and any deferred migration.

## Outcome

Implemented a narrow frozen `ActionPlan` envelope with inert `ToolRequest`
values. The plan carries optional origin, ingress, source, position, and
selection context; `as_normalized_plan()` returns the incumbent list shape so
capability execution and durable serialization remain unchanged. Assistant
candidate resolution now constructs and hands off the envelope while the
existing plan handler continues to execute normalized dictionaries.

Verification:

- `./.codex-local/bin/uvt run pytest tests/test_runtime_action_plan.py tests/test_runtime_step_runtime.py tests/test_runtime_intent_arbitration_edges.py tests/test_runtime_session_step_edges.py tests/test_graph.py -q --no-cov` (`294 passed`)
- `./.codex-local/bin/uvt run ruff check src/toas/runtime/action_plan.py src/toas/runtime/step_runtime.py tests/test_runtime_action_plan.py tests/test_runtime_step_runtime.py`

The envelope is not yet the universal runtime type. User candidate execution,
native/provider identity, and broader durable migration remain deferred until
their concrete ingress seams require the context.
