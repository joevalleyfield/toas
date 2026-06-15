Filed as: 260614-model-backend-failure-handoff
FKA:
AKA: provider failure handoff; model invocation lifecycle query; backend failure escalation
Legacy index:

keywords: runtime, investigation, inception, architecture, model, backend, lifecycle, failure

# Model Invocation To Backend Lifecycle Failure Handoff

## Current Reality

The architecture says provider/model-call failure belongs to Model Invocation
unless Model Backend Lifecycle explicitly observes or records lifecycle failure.

That rule is documented, but the query/escalation contract is not designed.

Parent: `260614-architecture-follow-through-coordination`

## Desired Reality

When generation fails against a managed backend, TOAS should be able to explain
whether the failure is:

- a provider/model invocation failure
- an observed backend lifecycle failure
- an unknown condition that needs an explicit status probe

Model Invocation must not silently mutate backend lifecycle state or restart the
backend just because a provider call failed.

## Inception Note

This task is intentionally inception-only. It records a real architectural
pressure, but it should not start implementation until policy resolution and
backend identity/stale-config contours are clearer.

## Known Facts

- Model Invocation and Model Backend Lifecycle are separate domains.
- Provider failure is not lifecycle failure without lifecycle observation.
- Backend lifecycle status can report stopped/running/failed for its current
  live process state.

## Unknowns

- Whether Model Invocation should query lifecycle directly, emit a diagnostic
  that suggests `backend status`, or call a narrow handoff port.
- Whether lifecycle observation after provider failure should be durable.
- Whether retry/recovery policy belongs to Model Invocation, Effective Policy,
  or an explicit operator decision.

## Evidence

Ready to leave inception when:

- the failure states are named
- the handoff boundary is explicit
- tests can prove provider failure does not mutate lifecycle state accidentally
