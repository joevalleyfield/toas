Filed as: 260614-model-backend-failure-handoff
FKA:
AKA: provider failure handoff; model invocation lifecycle query; backend failure escalation
Legacy index:

keywords: runtime, investigation, historical, architecture, model, backend, lifecycle, failure

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

Claimed for an evidence-backed contract pass on 2026-08-10. The pass is
limited to tracing current behavior and naming the handoff boundary; it does
not add automatic backend probing, restart, or recovery.

## Alignment Target

This task should align existing failure explanation and ownership. It should
not invent automatic backend recovery, restart behavior, or a richer managed
backend feature.

The first useful slice is a trace of current model-call failure paths and
current backend status/lifecycle observation points, ending in a small contract
for who may observe what and who may record what.

## Known Facts

- Model Invocation and Model Backend Lifecycle are separate domains.
- Provider failure is not lifecycle failure without lifecycle observation.
- Backend lifecycle status can report stopped/running/failed for its current
  live process state.

## Current Repo Trace: 2026-08-10

- `GenerationRunner.execute_with_retry()` owns the provider-call failure path.
  It classifies the exception, writes one `llm_call` audit record per attempt
  with endpoint/model/transport context, applies the configured retry policy,
  and ultimately raises a terminal generation error.
- The failure path has no `ModelBackendLifecycle` dependency and does not call
  backend start, stop, or restart.
- `ModelBackendLifecycle.status()` is an explicit observation operation. For
  managed-local mode it reads the live process and can return `stopped`,
  `running`, `failed`, or `stale`; external mode returns `external`.
- Lifecycle actions write separate `backend_lifecycle` records. Failed model
  calls write `llm_call` records, so the two fact types are already distinct in
  durable history.
- Existing regression coverage in
  `tests/test_cli.py::test_run_step_records_llm_failure_and_exits` proves that
  a provider failure records only the classified `llm_call` failure and does
  not synthesize a lifecycle record.

## Handoff Contract

The current evidence supports this narrow contract:

1. Model Invocation reports a provider/model invocation failure, including its
   classified error and selected backend connection context. It may retry only
   under its existing invocation policy.
2. Model Invocation does not infer a backend lifecycle failure from that
   provider error and does not mutate backend process state.
3. A lifecycle diagnosis is obtained only through an explicit,
   observation-only `backend status` operation (or a future narrow equivalent
   port). That observation may distinguish `external`, `stopped`, `running`,
   `failed`, and `stale`.
4. Automatic status probing, durable lifecycle observation after every provider
   failure, and restart/recovery remain policy decisions and are not part of
   this handoff contract.

This gives operators a three-way explanation without conflating domains:

- provider failure: the `llm_call` failed and no lifecycle fact was observed;
- observed lifecycle failure: an explicit status operation reports `failed` or
  another lifecycle diagnosis;
- unknown: no lifecycle observation has been made, so the operator should run
  an explicit status probe if that distinction matters.

## Disposition: 2026-08-10

The task has left the policy/identity ambiguity that justified inception. The
handoff boundary is now explicit and current behavior already satisfies the
non-mutation invariant. No implementation change is justified by the present
evidence. Keep automatic post-failure probing/recovery parked unless an
observed operator workflow demonstrates that the explicit status handoff is
insufficient; any such work should be a narrower follow-on with a concrete
status-port and test contract.

## Unknowns

- Whether a future user-facing failure projection should suggest `backend
  status` automatically, or leave the explicit probe to the operator.
- Whether a future explicit handoff port needs a richer backend identity than
  the current selected endpoint/model context.
- Whether an observed post-failure status should be copied into a separate
  diagnostic record; current evidence does not justify doing so.

## Evidence

Ready to leave inception when:

- the failure states are named
- the handoff boundary is explicit
- tests can prove provider failure does not mutate lifecycle state accidentally
- any recovery idea is explicitly parked unless backed by current behavior

The 2026-08-10 trace satisfies these exit conditions. The task is closed as an
architectural record. Intervening runtime fixes smoothed the original failure
experience, and no remaining observed workflow justifies a new handoff
implementation. Reopen only from concrete evidence of operator confusion or
a lifecycle distinction that the existing explicit status surface cannot
explain.

## Closure Evidence: 2026-08-10

- No production or test change is required for closure.
- The focused provider-failure regression passed during the contract pass.
- The original pain point was reduced by intervening runtime fixes rather than
  by a dedicated backend-failure handoff feature.
