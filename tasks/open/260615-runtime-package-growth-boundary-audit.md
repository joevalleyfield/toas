Filed as: 260615-runtime-package-growth-boundary-audit
FKA:
AKA: runtime package bloat; runtime god-package risk; runtime module placement audit
Legacy index:

keywords: runtime, investigation, inception, architecture, boundaries, maintainability, package, module

# Runtime Package Growth Boundary Audit

## Current Reality

`src/toas/runtime/` became the natural home for code pulled out of CLI,
daemon, and step-era broad modules. That was an improvement, but the same
pressure can turn `runtime/` into a new god package if every semantic concern
lands there without a named owner.

Parent: `260614-architecture-follow-through-coordination`

## Desired Reality

Runtime modules should be grouped by ownership force, not merely by the fact
that they are no longer CLI or daemon code.

Before moving more code, TOAS should know which current runtime modules belong
to:

- Operator Semantics
- Activity Lifecycle
- Session Host Supervision
- Transport And Protocol
- Effective Policy And Authority
- Model Invocation
- Model Backend Lifecycle
- Projection And Rendering
- cross-surface edge glue

## Alignment Target

This task is not a request to create new package abstractions. It is a
boundary-audit task for what already exists.

The first useful result is a map of current `runtime/` modules to architecture
domains, with only the highest-signal naming or placement follow-ups split out.

## Known Facts

- `docs/runtime-ownership.md` already warns that `runtime/` is a current home,
  not a blanket owner.
- Recent work moved policy, backend lifecycle, activity, and host behavior into
  runtime-owned modules.
- The package now contains both semantic domain modules and edge/glue modules.

## Unknowns

- Which runtime modules are named by implementation path rather than ownership
  force.
- Which modules mix multiple domains enough to block future alignment work.
- Which naming problems belong with `260614-retire-local-suffix-naming-inversion`.
- Whether any package split is worth doing now, or whether documentation and
  naming are enough.

## Evidence

Ready to leave inception when:

- a runtime module-to-domain map exists
- mixed-domain modules are named with concrete evidence
- any follow-up distinguishes alignment cleanup from speculative package design
