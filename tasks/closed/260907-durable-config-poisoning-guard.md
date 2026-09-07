Filed as: 260907-durable-config-poisoning-guard
FKA:
AKA: malformed config recovery; durable override poison guard; step startup recovery
Legacy index:

Parent: `260907-endpoint-target-acceptance`
Depends on: `260907-endpoint-target-acceptance`
Blocks:
Blocked by:
Related: `260907-target-authoring-surface`

keywords: config, runtime, implementation, active, correctness, recovery

# Guard Step Startup Against Malformed Durable Config

Ensure stale or malformed durable configuration records cannot prevent the
runtime from reaching operator-command handling and recovery.

## Contract

- Sparse target overrides must not replace global generation policy state.
- Null or malformed numeric generation values must fall back safely at the
  generation-policy boundary.
- A regression test must reconstruct the affected durable override shape and
  still permit a step.

## Progress Evidence

Closed: fixed sparse target override state shadowing so target reconstruction
cannot replace global `GenerationPolicy`, and added generation-policy boundary
fallbacks for null or negative numeric values. The existing malformed target
record remains historical; no durable event rewrite was required, and a fresh
step now reconstructs the log successfully.

Verification: focused policy/config tests 87 passed; config-discovery
acceptance 4 passed; full suite 3,204 passed, 13 deselected, 100% coverage;
Ruff clean.
