Filed as: 260614-effective-policy-authority-resolver
FKA:
AKA: Effective Policy And Authority resolver shape; policy authority resolver; resolved policy boundary
Legacy index:

keywords: config, investigation, active, architecture, policy, authority, boundaries, resolver

# Effective Policy And Authority Resolver Shape

## Current Reality

The architecture documents identify Effective Policy And Authority as a domain,
but the concrete resolver shape is not yet specified.

Policy-like inputs are distributed across config defaults/files, durable
overrides, environment, shell grants, owner identity, workspace roots,
transcript/control modifiers, backend startup config, and runtime-adjustable
model invocation config.

The architecture coordination task names this as the likely first high-leverage
child because backend stale-config work depends on knowing who owns resolved
desired policy.

Parent: `260614-architecture-follow-through-coordination`

## Desired Reality

TOAS should have a clear boundary for resolving policy and authority before
domain consumers act.

The resolver should answer:

- which inputs are policy sources
- which source wins when values conflict
- what provenance is observable
- which consumers may use resolved values
- which consumers must not recompute precedence themselves

## Gap Analysis

The force is identified, but the implementation shape is not.

Without a resolver boundary, future backend lifecycle, capability, host,
workspace, and model invocation work can each resolve policy slightly
differently. That risks silent permission widening, stale backend desired-state
confusion, and tests that only prove local wiring.

## Known Facts

- `docs/architecture-masterplan.md` lists Effective Policy And Authority as a
  domain.
- `docs/runtime-ownership.md` says config, grants, owner identity, and
  authority precedence belong to this domain, and consumers should keep
  provenance observable.
- `/config` precedence diagnostics and durable shell grants already exist, but
  they do not by themselves define one cross-domain resolver boundary.
- Backend lifecycle stale-config detection likely needs a resolved desired
  startup identity from this domain.

## Unknowns

- Which existing helpers already form pieces of the resolver.
- Whether the first deliverable should be documentation, a small resolver
  object, or an inventory plus proposed module boundary.
- Which consumers should move first: backend lifecycle, capabilities, model
  invocation, workspace/shell authority, or host ownership.
- Whether runtime-adjustable config and startup-only config should be resolved
  through one object with typed projections or separate resolver APIs.

## Scope

- Inventory policy/authority sources and consumers.
- Identify duplicated precedence/resolution logic.
- Propose a resolver boundary with explicit inputs, outputs, provenance, and
  non-goals.
- Open implementation follow-ups only when a first consumer and test surface are
  clear.

## Out of Scope

- Rewriting all config handling in one slice.
- Changing user-facing config semantics without evidence.
- Folding capability execution, model invocation, or backend lifecycle behavior
  into the resolver.

## Evidence

Done when:

- there is a policy/authority source-and-consumer map
- resolver responsibilities and forbidden responsibilities are explicit
- at least one first implementation slice is either selected or deliberately
  deferred
- backend lifecycle stale-config work knows whether it depends on this resolver
  first

## Next Actions

1. Inventory current config/grant/owner/workspace/backend policy sources.
2. Trace at least three consumers: capability authority, model invocation, and
   backend lifecycle startup desired state.
3. Decide whether to implement a resolver slice before backend stale-config
   work.
