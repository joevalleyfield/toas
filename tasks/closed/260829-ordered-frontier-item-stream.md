Filed as: 260829-ordered-frontier-item-stream
FKA:
AKA: interleaved operator actions; ordered frontier execution; config-before-callable
Legacy index:

keywords: runtime, implementation, active, correctness, frontier, config, projection

Parent: `260829-canonical-action-ingress-contract`
Depends on: `260829-action-plan-envelope`
Related: `260829-compound-tool-request-records`; `260803-tool-intent-ingress-separation`

# Ordered Frontier Item Stream

Process operator commands and callable action plans in one source-ordered
frontier stream while keeping their execution handlers and semantic payloads
distinct.

## Confirmed Behavior

An operator command can change the context observed by a later callable in the
same frontier:

```text
/config A
$ command under A
/config B
$ command under B
```

The stream must discover every supported item, preserve textual order, apply
operator side effects before the next item, and retain the original item type
for execution, provenance, and durable recording.

## Scope

- collect all operator commands with source positions;
- interleave operator commands, `ActionPlan` candidates, and supported shell
  candidates in source order;
- preserve `first_wins`, `last_wins`, and `strict` behavior over the combined
  item stream unless existing semantics explicitly require otherwise;
- apply same-step configuration/context updates before later items execute;
- retain separate operator, callable, and shell handlers;
- add focused tests for interleaving, configuration visibility, and turn shape.

## Non-Goals

- making operator commands `ToolRequest` values;
- changing the `ActionPlan`/`ToolRequest` hierarchy;
- adding hidden loops or implicit extra steps;
- changing authority profiles or capability implementations;
- broadening recognition to native, JSON, or executable-fence lanes.

## Acceptance

- `/config`, callable plans, and later `$` commands execute in source order;
- a context update from one item is visible to later items in that same step;
- existing single-item and user/assistant authority behavior remains green;
- selection modes have explicit tests over mixed item types;
- completion evidence records any deliberately deferred operator semantics.

## Outcome

Implemented ordered operator discovery and interleaving with callable plans.
All recognized operator commands now retain source order and participate in
the same candidate stream as callable plans. The existing distinct handlers
remain in place, and ordinary nested `/config set` updates are applied to the
live config passed to later operator items in the same step.

Verification:

- `./.codex-local/bin/uvt run pytest tests/test_runtime_intent_arbitration_edges.py tests/test_runtime_step_runtime.py tests/test_runtime_session_step_edges.py tests/test_step.py -q --no-cov` (`403 passed`)
- `./.codex-local/bin/uvt run ruff check src/toas/runtime/intent_arbitration_edges.py src/toas/runtime/step_runtime.py tests/test_runtime_intent_arbitration_edges.py tests/test_runtime_step_runtime.py`

Unsetting/restoring durable overrides and dynamically changing settings that
were already consumed during candidate discovery remain deferred. They need a
separate live-context design rather than being approximated by this ordering
change.
