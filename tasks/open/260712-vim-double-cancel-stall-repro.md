Filed as: 260712-vim-double-cancel-stall-repro
FKA:
AKA: vim 15-second cancel stall; synchronous cancel channel race; escape escape stall
Legacy index:

keywords: surface, investigation, active, correctness, vim, async, transport, cancel, stream, logging

Parent: `260614-architecture-follow-through-coordination`
Depends on: `260712-host-double-cancel-race-harness`; `260712-host-llm-contract-test-reconcile`
Related: `260705-cancel-timeout-terminality-contract`; `260705-host-subscribe-terminal-event-parity`; `260710-vim-run-wrapper-and-inner-panels`

# Vim Double-Cancel Stall Reproduction

## Objective

Reproduce and localize the approximately 15-second stall observed when Vim
sends a first cancel during generation and a second cancel just before normal
completion. Preserve the real persistent host-stdio protocol and the relevant
Vim request/subscription interaction rather than simulating the outcome with
mocked frames.

## Known Calibration

The bounded asyncio host client established a deterministic near-completion
search region and repeatedly produced both clean `cancelled` and `succeeded`
outcomes there without a long pause:

- first cancel fixed early at `0.25s`
- second cancel targeted at the leading shoulder of completion
- second-cancel RTT remained `0-2ms`
- maximum silent interval remained below `200ms`
- no trial crossed the `12s` stall threshold

That negative evidence makes Vim's synchronous local-host request loop sharing
one channel with timer/callback subscription consumption the primary
differential to investigate.

## Scope

- create a bounded headless-Vim experiment using the persistent stdio host and
  deterministic streaming LLM stand-in
- issue the first cancel early and sweep the second cancel across the
  calibrated leading edge of completion
- preserve Vim-shaped channel reads, subscription callbacks, RX buffering,
  response matching, and terminal-frame handling
- measure and log:
  - cancel dispatch to matching response
  - last frame to cancel dispatch
  - cancel dispatch to next frame
  - nonterminal completion to resubscribe acknowledgement
  - runtime terminal state to terminal frame observed by Vim, when available
- flag and retain evidence for silent gaps or request latency in the `12-18s`
  range
- determine whether a stall is caused by response consumption, unmatched-frame
  buffering, callback starvation, terminal-state recognition, or a different
  observable channel seam

## Non-Goals

- changing runtime cancellation semantics without reproduction evidence
- replacing Vim's persistent host integration
- broad Vim UI/dashboard redesign
- treating ordinary sub-100ms completion/cancel jitter as the target defect
- unbounded fuzzing

## Allowed Write Surfaces

- `vim/plugin/toas.vim` for narrowly scoped diagnostics or a proven fix
- `tests/vim/` and Vim integration tests under `tests/`
- `scripts/` for a bounded reproduction driver if needed
- protocol or runtime tests only when reproduction proves their contract is
  implicated
- this task file and generated `tasks/WORKBOARD.md` sections

Any production runtime change requires the task evidence to identify the
runtime-owned failure rather than only a Vim-side symptom.

## Acceptance Criteria

- [ ] the experiment uses a real Vim process and persistent host-stdio channel
- [ ] cancel timing is bounded, repeatable, and centered on the calibrated
  leading edge
- [ ] logs distinguish synchronous request reads from subscription callback
  consumption
- [ ] at least one 15-second stall is reproduced, or a bounded negative result
  clearly eliminates the Vim/channel hypothesis
- [ ] any reproduced stall has a frame/request timeline identifying the
  narrowest responsible seam
- [ ] any fix is covered at the Vim/channel boundary and does not weaken
  lifecycle-owned terminal truth
- [ ] the relevant focused checks and full default suite pass

## Required Completion Evidence

- exact reproduction command, timing range, repeat count, and stall threshold
- per-trial outcome and latency summary
- retained wire/timing excerpt for every reproduced stall
- comparison against the asyncio host-client negative baseline
- focused Vim/host verification results
- full default-suite result and coverage status
