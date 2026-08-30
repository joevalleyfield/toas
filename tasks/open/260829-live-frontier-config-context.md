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

## Evidence Crosswalk

The ordered-frontier implementation establishes the current boundary:

- candidate discovery and arbitration happen before frontier consequences are
  executed, so the recognized candidate set is a per-step snapshot;
- ordinary nested `/config set` updates are applied to the live config passed
  to later operator handlers in the same step;
- a later handler therefore sees the update without requiring recognition to
  run again;
- `/config unset` and `/config restore` already produce durable override
  operations, but their live in-memory effect for later same-step items is not
  yet defined;
- changing a setting must not retroactively alter an item already recognized
  or an action already executed.

This is a configuration-context seam, not a new action or authority model.

## Questions To Resolve

- which configuration changes should affect later items in the same step;
- whether discovery is fixed at the start of a step or can be revisited after
  a configuration change;
- how unset/restore derives the live value without bypassing durable history;
- how updated shell, workspace, stream, and timeout policy reaches later
  execution without creating a hidden loop;
- which changes intentionally take effect only on the next step.

## Provisional Semantics

Unless a concrete setting requires a narrower rule:

1. Discovery and arbitration take a snapshot at the start of the explicit
   `step`.
2. Each later item executes against the current live configuration after all
   preceding configuration results have been applied.
3. `set`, `unset`, `restore`, and `load` update both durable override state and
   the live context for later items in that same step.
4. No configuration update re-runs discovery, changes the order of already
   recognized items, or re-executes an earlier item.
5. Settings needed only by a later model invocation or later explicit step are
   read when that consumer is reached; no hidden invocation is created to
   observe the update.
6. Authority profile selection remains governed by the frontier origin and
   existing user/assistant policy rules. Configuration can affect policy where
   the existing policy surface permits it, but cannot launder origin or grant
   authority through a callable request.

This preserves the useful interleaving case:

```text
/config set <key> <new-value>
<later action>
```

The later action sees the new value, while the set operation does not cause a
new candidate-discovery pass.

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

## Implementation-Ready Follow-On

The bounded implementation should own the live context update path for
`unset`, `restore`, and `load`, plus focused tests for the snapshot/live split.
It should not redesign candidate arbitration, authority profiles, durable
override record shapes, or operator command families.

Suggested guardrail scenarios:

- a configuration update changes the next operator handler's observed config;
- a configuration update does not cause a newly discoverable candidate to
  enter the current step;
- `unset` and `restore` affect later items from the restored baseline;
- an already recognized or executed item retains the context selected when it
  was reached;
- no update creates an implicit extra step or model invocation.
