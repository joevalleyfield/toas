Filed as: 260803-first-failure-plan-recovery
FKA:
AKA: failed multi-tool recovery; split on first failure; partial plan continuation
Legacy index:

keywords: runtime, implementation, historical, correctness, tooling, recovery, frontier, projection

Related: `260621-staged-replay-healing-indent-only-mismatches`; `260803-seed-prompt-operator-stance`; `260803-assistant-execution-authority`; `260803-language-exec-fenced-block-lane`; `260803-tool-intent-ingress-separation`

# First-Failure Multi-Tool Plan Recovery

## Status

Completed on 2026-08-03.

## Retry / Remainder Contract

The recovery projection keeps one unambiguous active frontier without adding a
new durable record kind:

- completed prefix operations remain ordinary result nodes and durable
  `tool_result` records;
- the failed operation is projected as the only ordinary executable YAML
  fence, preserving its complete editable call shape;
- the untouched suffix is projected in a `yaml staged` fence, which is visible
  Markdown but intentionally outside callable YAML extraction;
- after the standalone retry succeeds, the runtime promotes the staged suffix
  to an ordinary executable plan as the next user frontier;
- if the retry fails, the same direct retry plus staged suffix is projected
  again, without replaying the completed prefix.

The original `tool_request` continues to record the requested ordered plan.
Only attempted operations produce `tool_result` records. Retry and promoted
remainder frontiers produce their own request/result records, so durable
history distinguishes requested, attempted, and completed work without a
sidecar plan store.

## Objective

Define and implement first-failure semantics for multi-tool plans so partial
success becomes durable progress instead of forcing the operator or model to
reconstruct or replay the whole plan.

## Prior Reality

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

- [x] Ordered plan execution stops dispatching at the first failed operation.
- [x] Pre-failure successes are rendered and durably recorded exactly once.
- [x] The failed operation appears as one standalone retry whose arguments can
  be edited directly before execution.
- [x] Unattempted operations remain visible and staged in original order as the
  forward plan, with no result records that imply they ran.
- [x] Retrying the failed operation does not replay already completed work.
- [x] Successful retry offers a deterministic path into the remaining plan.
- [x] Failure classification covers ordinary tool failure, authorization
  staging, timeout, cancellation, validation failure, and indeterminate
  transport/process outcomes.
- [x] Existing single-call behavior and explicit historical `/replay` behavior
  remain coherent.
- [x] Tests cover failure at the first, middle, and final operation, including
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

## Completion Evidence

- `execute_plan_calls` now stops on either a returned `ok: false` result or the
  first raised execution failure. First/middle/final state-matrix tests prove
  that the suffix is never dispatched.
- Returned and raised failures carry `failure_kind` and `outcome`. Validation,
  authorization, ordinary execution, timeout, transport, and child-process
  cases are distinguished; timeout/transport/process loss is
  `indeterminate`. `KeyboardInterrupt` propagates and does not dispatch the
  suffix.
- Representative projection for `echo(completed)`, `missing`,
  `echo(unattempted)` is: two ordinary results, then one adopted user frontier
  whose executable YAML contains only `missing` and whose `yaml staged` fence
  contains only `echo(unattempted)`.
- Representative durable history records the full requested plan once as a
  `tool_request` related to the original message, followed by exactly two
  `tool_result` records (`echo`, `missing`) related to that same message. The
  adopted recovery is a separate message event; no result exists for
  `echo(unattempted)`.
- A successful retry test proves that execution receives only the retry call
  and then projects the staged suffix as the next ordinary YAML frontier.
  Existing explicit replay coverage remains green.
- Focused execution/frontier coverage: 44 passed, 100% for
  `toas.tools_cluster.execution` and `toas.runtime.frontier_resolution`.
- Full suite: 2,751 passed, 9 deselected, 100% coverage.

## Operator Input Welcome

Useful additions include real failed multi-call transcripts, preferred visible
retry/remainder layouts, examples where later calls were independent, and any
existing direct-manipulation artifacts that should replace replay references.
