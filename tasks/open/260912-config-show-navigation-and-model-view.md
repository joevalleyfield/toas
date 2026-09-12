Filed as: 260912-config-show-navigation-and-model-view
FKA:
AKA: config show contract audit; config navigation and structured models
Legacy index:

Parent: `260912-config-show-effective-overview`

Related: `260912-config-discovery-preservation`

keywords: config, discovery, surface, contract, decomposition, active

# Rationalize config-show navigation and model detail views

## Objective

Turn the new `/config show` overview into a trustworthy navigation surface and
make detailed model configuration human-readable by default without losing the
existing dictionary-shaped projection.

## Plan / ordered work

1. Inventory every command in the overview's `next:` block and config-help
   asset, resolve each against an actual handler, and classify it as working,
   misleading, or intentionally deferred.
2. Repair or remove vapor commands and add acceptance coverage that executes
   the advertised discovery path rather than checking strings alone.
3. Define the two representations of filtered model configuration: a
   structured human view as the default and an explicit switch for the
   exhaustive flat/dictionary projection.
4. Cross-check the structured model view and its escape hatch against the
   complete valid configuration-key registry so no non-deprecated key becomes
   unreachable or silently omitted.
5. Update help assets, usage, and acceptance evidence together, preserving
   source/provenance semantics and explicit compatibility labels.

## Invariants

- Every advertised next action is executable or explicitly labeled deferred.
- Every non-deprecated key remains reachable through help, a filtered view, or
  the exhaustive escape hatch.
- Structured output is optimized for human reading; the escape hatch remains
  stable and suitable for complete inspection.
- No secret values are rendered in either representation.

## Child tasks

- `260912-config-show-next-command-audit`
- `260912-config-model-structured-view`

## Non-goals

- No new configuration semantics or precedence changes.
- No removal of legacy config inputs in this arc.
- No machine-readable schema beyond preserving the current explicit escape
  hatch.

## Status

Plan recorded; child tasks ready for implementation.
