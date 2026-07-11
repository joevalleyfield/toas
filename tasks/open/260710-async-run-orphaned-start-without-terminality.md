Filed as: 260710-async-run-orphaned-start-without-terminality
FKA:
AKA: started-only async run; alive-but-inert stdio loop; missing run terminality; orphaned run status
Legacy index:

keywords: runtime, investigation, active, correctness, async, transport, watch, cancel, stream, vim, terminality, logging

Parent: `260614-architecture-follow-through-coordination`
Related: `260705-cancel-timeout-terminality-contract`; `260705-host-subscribe-terminal-event-parity`; `260710-vim-run-wrapper-and-inner-panels`

# Async Run Orphaned Start Without Terminality

## Current Reality

We observed a real async run that reached `started` and then stayed open with no
further meaningful progress until the operator explicitly cancelled it from Vim.

The important distinction is:

- Vim did not invent the stuck state
- the stdio/watch loop remained alive the entire time
- the elapsed clock merely made the latent missing-terminality condition obvious

This is more specific than "transport hung" or "Vim missed an event". The
transport and watch machinery were still able to send and receive traffic; the
run just remained open in an inert state.

## Concrete Evidence

Observed run:

- `run_id`: `27739aaa9eaa`

Durable history shape around the incident included:

- `{"kind": "run", "payload": {"run_id": "27739aaa9eaa", "status": "started", "workdir": "/Users/tim/Documents"}}`

with no matching durable terminal run record before cancel.

Neighboring records showed unrelated successful runs and a tool result tied to a
frontier message id rather than to the orphaned run id:

- `tool_request` / `tool_result` related to `n20459`
- successful `run` records for `bfb4df831105` and `1ea6fd6b5b1b`

Host stdio logs showed:

- `21:50:59` `step_async` ack for `27739aaa9eaa`
- `21:51:00` Vim subscribe/watch activity began
- no useful run-closing traffic for several minutes
- `21:54:43` operator cancel finally forced terminality
- `21:54:44` Vim received `status=cancelled` plus a `run_done` event and
  stopped the watcher

The Vim wire log phase summary included a very large `ack_to_sub_send` gap,
which reinforced that the run stayed open for a long time rather than merely
rendering stale UI.

## Why This Matters

This bug sits at the run-lifecycle boundary, not the presentation boundary.

If a run can remain:

- transport-live
- watcher-live
- subscribe-live
- status-open
- but semantically inert

then every consumer needs either:

- reliable terminality guarantees upstream, or
- explicit stall proxies that make "alive but doing nothing" legible

The Vim elapsed clock is useful precisely because it exposes this missing
invariant.

## Working Hypotheses

- a run can be recorded as `started` but fail to emit a matching terminal run
  record on some paths
- tool completion or internal worker completion may not always force run
  terminality for the same `run_id`
- there may be a path where activity ownership moves or drains without a final
  `run_done`
- cancel currently acts as the fallback mechanism that repairs the missing
  closure

## Design Notes

This task should stay focused on runtime truth, not on Vim chrome.

Questions the task should answer:

- under what paths can a run remain `started` / `running` without later
  terminality?
- what is the intended contract between tool completion, projection completion,
  and `run_done` emission?
- which lifecycle facts are durable in `events.jsonl` versus only visible in
  host activity streams?
- should host subscribe/poll be able to prove that a run is quiescent-but-open,
  or is "open forever unless terminal event emitted" the current contract?

## Suggested Next Evidence

- capture one or more minimal repros that produce `started` without terminal
  closure
- identify the runtime ownership point responsible for guaranteed `run_done`
  emission
- compare durable history, host subscribe output, and in-memory run-store state
  for the same incident
- decide whether the fix is "always emit terminal run record" or "surface an
  explicit intermediate state instead of indefinite running"

## Exit Evidence

- [ ] a concrete runtime path for started-without-terminality is identified
- [ ] intended terminality contract is written down for async runs
- [ ] it is clear whether the missing fact belongs in durable history, host
  activity stream, or both
- [ ] at least one focused follow-on seam is identified for implementation
