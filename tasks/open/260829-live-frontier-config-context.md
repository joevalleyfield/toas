Filed as: 260829-live-frontier-config-context
FKA:
AKA: same-step config context; dynamic frontier policy; live operator context
Legacy index:

keywords: runtime, investigation, active, correctness, config, frontier, policy

Parent: `260829-canonical-action-ingress-contract`
Depends on: `260829-ordered-frontier-item-stream`
Related: `325`; `260829-compound-tool-request-records`

# Live Frontier Configuration Context

Define how operator configuration changes affect later items in the same
explicit `step`, including durable override operations and settings consumed
before item execution.

## Known Deferred Seam

Ordered frontier execution now applies ordinary nested `/config set` overlays
to later operator handlers. It does not yet dynamically reconfigure settings
that candidate discovery or the injected executor already consumed, and
`/config unset`/`restore` still represent durable updates whose live same-step
behavior is undefined.

## Questions To Resolve

- which configuration changes should affect later items in the same step;
- whether discovery is fixed at the start of a step or can be revisited after
  a configuration change;
- how unset/restore derives the live value without bypassing durable history;
- how updated shell, workspace, stream, and timeout policy reaches later
  execution without creating a hidden loop;
- which changes intentionally take effect only on the next step.

## Non-Goals

- changing the explicit `step` boundary;
- making configuration changes retroactive to already executed items;
- changing user/assistant authority profiles;
- replacing durable config override records.

## Exit Criteria

- one concrete same-step configuration scenario has an agreed behavior;
- the live context owner and update path are identified;
- focused tests distinguish current-step effects from next-step effects;
- a bounded implementation follow-on can be opened without redesigning all
  operator commands.
