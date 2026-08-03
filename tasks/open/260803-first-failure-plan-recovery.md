Filed as: 260803-first-failure-plan-recovery
FKA:
AKA: failed multi-tool recovery; split on first failure; partial plan continuation
Legacy index:

keywords: runtime, decomp, inception, correctness, tooling, recovery, frontier, projection

Related: `260621-staged-replay-healing-indent-only-mismatches`; `260803-seed-prompt-operator-stance`; `260803-assistant-execution-authority`; `260803-language-exec-fenced-block-lane`; `260803-tool-intent-ingress-separation`

# First-Failure Multi-Tool Plan Recovery

## Objective

Define and implement first-failure semantics for multi-tool plans so partial
success becomes durable progress instead of forcing the operator or model to
reconstruct or replay the whole plan.

## Current Reality

`execute_plan_calls` currently continues through the full plan after a
`RuntimeError`. The result list can therefore mix successes, failures, and
later operations that ran despite an earlier dependency failure. Existing
repair and replay surfaces can stage targeted healing, but they are centered
on re-executing prior callable material by reference.

That behavior is a poor default when later operations depend on earlier state
or when the transcript should make the exact next manipulation visible.

## Desired Split

On the first failed operation in an ordered plan:

1. Every successfully completed operation before the failure is emitted as an
   ordinary result and remains completed.
2. The failed operation is materialized as one standalone, editable retry.
3. Operations after the failure do not execute; they remain staged in original
   order as the forward plan.
4. The visible recovery path carries the actual operation arguments needed for
   direct manipulation. Replay-by-reference may remain an explicit historical
   affordance, but it is not the preferred recovery mechanism.

The contract must distinguish an execution failure from an authorization
block, validation error, timeout, cancellation, or process-level interruption
where the runtime may not know whether an operation completed.

## Requirements Parent Questions

- Which durable or projected shape represents the standalone retry and the
  remaining forward plan without pretending either has executed?
- Can retry and remainder coexist while preserving one unambiguous active
  transcript frontier, or is an explicit staged-plan record needed?
- When the retry succeeds, does the remainder become the next frontier
  automatically, require an operator step, or return to the model for
  resynthesis?
- Which calls are safe to classify as completed after timeout or transport
  loss, and which require an indeterminate outcome?
- Should independent operations ever continue after a failure, and if so what
  explicit plan metadata is required rather than inferred?
- How do `/heal`, `/queue`, and `/replay` interoperate with the new direct
  retry/remainder shape without becoming its storage authority?

## Acceptance Criteria

- [ ] Ordered plan execution stops dispatching at the first failed operation.
- [ ] Pre-failure successes are rendered and durably recorded exactly once.
- [ ] The failed operation appears as one standalone retry whose arguments can
  be edited directly before execution.
- [ ] Unattempted operations remain visible and staged in original order as the
  forward plan, with no result records that imply they ran.
- [ ] Retrying the failed operation does not replay already completed work.
- [ ] Successful retry offers a deterministic path into the remaining plan.
- [ ] Failure classification covers ordinary tool failure, authorization
  staging, timeout, cancellation, validation failure, and indeterminate
  transport/process outcomes.
- [ ] Existing single-call behavior and explicit historical `/replay` behavior
  remain coherent.
- [ ] Tests cover failure at the first, middle, and final operation, including
  durable-history and transcript-projection assertions.

## Non-Goals

- General transaction rollback across arbitrary tools.
- Inferring dependency graphs from tool names or arguments.
- Silently repairing or changing a failed operation.
- Removing explicit replay/history inspection surfaces.

## Likely Ownership

The split belongs at the runtime plan-execution and frontier-consequence seam,
with tool result facts remaining in their existing durable record space.
Tool-specific repair suggestions may contribute edits, but must not own plan
lifecycle semantics.

## Allowed Write Surfaces

- `src/toas/runtime/` plan execution, frontier, and staged-consequence modules
- `src/toas/tools_cluster/execution.py`
- `src/toas/graph.py` only if a new durable staged-plan record is justified by
  the requirements decision
- focused tests under `tests/`
- contract documentation if a new durable record or projection shape is added
- this task file and mechanically generated `tasks/WORKBOARD.md` sections

## Required Completion Evidence

- a written retry/remainder object and projection contract;
- focused state-matrix tests for first/middle/final failure;
- representative before/after transcript plus `events.jsonl` evidence;
- proof that completed calls are not replayed;
- default suite result.

## Operator Input Welcome

Useful additions include real failed multi-call transcripts, preferred visible
retry/remainder layouts, examples where later calls were independent, and any
existing direct-manipulation artifacts that should replace replay references.
