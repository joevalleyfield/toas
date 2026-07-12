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

- [x] the experiment uses a real Vim process and persistent host-stdio channel
- [x] cancel timing is bounded, repeatable, and centered on the calibrated
  leading edge
- [x] logs distinguish synchronous request reads from subscription callback
  consumption
- [x] at least one 15-second stall is reproduced, or a bounded negative result
  clearly eliminates the Vim/channel hypothesis
- [x] any reproduced stall has a frame/request timeline identifying the
  narrowest responsible seam
- [x] any fix is covered at the Vim/channel boundary and does not weaken
  lifecycle-owned terminal truth
- [x] the relevant focused checks and full default suite pass

## Required Completion Evidence

- exact reproduction command, timing range, repeat count, and stall threshold
- per-trial outcome and latency summary
- retained wire/timing excerpt for every reproduced stall
- comparison against the asyncio host-client negative baseline
- focused Vim/host verification results
- full default-suite result and coverage status

## Completion Evidence

### Built Surface

- added `scripts/vim_cancel_stall_sweep.py`
- each trial launches a real Vim process, sources the real plugin, starts a
  nonblocking `ToasStepHere()` run, and invokes both synchronous
  `ToasCancel()` calls from Vim timers
- each trial uses a fresh temporary transcript/history and the real persistent
  host-stdio child channel against a deterministic streaming LLM stand-in
- added gated Vim wire diagnostics (`g:toas_cancel_race_diag`) that distinguish:
  - channel callback receipt
  - synchronous cancel direct reads
  - cancel request wait begin/end

### Commands And Bounds

Smoke:

```bash
./.codex-local/bin/uvt run python scripts/vim_cancel_stall_sweep.py \
  --second-start-s 2.42 --second-stop-s 2.42 --second-step-s 0.02 \
  --repeats 1 --timeout-s 22 --stall-threshold-s 12
```

Coarse boundary sweep:

```bash
./.codex-local/bin/uvt run python scripts/vim_cancel_stall_sweep.py \
  --second-start-s 2.38 --second-stop-s 2.50 --second-step-s 0.02 \
  --repeats 2 --timeout-s 22 --stall-threshold-s 12
```

Concentrated leading-edge sweep:

```bash
./.codex-local/bin/uvt run python scripts/vim_cancel_stall_sweep.py \
  --second-start-s 2.41 --second-stop-s 2.45 --second-step-s 0.01 \
  --repeats 5 --timeout-s 22 --stall-threshold-s 12
```

Reader confirmation:

```bash
./.codex-local/bin/uvt run python scripts/vim_cancel_stall_sweep.py \
  --second-start-s 2.42 --second-stop-s 2.42 --second-step-s 0.01 \
  --repeats 3 --timeout-s 22 --stall-threshold-s 12
```

### Result

- 43 real-Vim trials completed
- both clean `cancelled` and `succeeded` outcomes occurred inside the calibrated
  search region
- `0/43` trials crossed the 12-second stall threshold
- worst observed second-cancel RTT was approximately `280ms`
- worst observed wire-log gap was approximately `252ms`
- confirmation trials observed both channel consumers in each run:
  - `81-83` callback reads
  - `2-3` synchronous cancel direct reads
  - `2` synchronous cancel waits
- comparison baseline remains consistent with the asyncio client result:
  neither client reproduced the 15-second stall around the clean completion
  boundary

This bounded result strongly rejects generic contention between Vim's
synchronous cancel reader and timer/callback subscription reader as sufficient
to cause the observed pause. Remaining differentials are the real model/backend
workload and the literal interactive Escape dispatch path.

### Verification

- focused real-Vim/host tests: `5 passed`
- Ruff: clean for the new driver
- full default suite: `2680 passed, 9 deselected`
- coverage: `100%`
- no lifecycle or runtime semantics changed
