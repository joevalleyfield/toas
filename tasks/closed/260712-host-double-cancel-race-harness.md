Filed as: 260712-host-double-cancel-race-harness
FKA:
AKA: near-completion cancel exerciser; vim cancel race repro; host protocol ui trace
Legacy index:

keywords: tooling, implementation, historical, correctness, async, transport, watch, cancel, stream, vim

Parent: `260614-architecture-follow-through-coordination`
Related: `260705-cancel-timeout-terminality-contract`; `260705-host-subscribe-terminal-event-parity`; `260710-vim-run-wrapper-and-inner-panels`

# Host Double-Cancel Race Harness

## Objective

Make the Vim-observed cancel-near-completion experiment reproducible without
remote-controlling Vim. Extend the demo host-stdio client so it exercises the
same wire protocol and reports the outer run plus inner LLM/tool/projection
state while issuing two independently timed cancel requests.

## Scope

- use `step_async` and `stream_subscribe` over the persistent stdio host
- allow a first cancel relative to run start and a second relative to the first
- keep receiving frames while cancel requests are in flight
- print compact timestamped run/lane transitions and terminal completion truth
- cover timer ordering, request payloads, and terminal race behavior without a
  real model dependency
- document a practical invocation for repeated manual runtime trials

## Non-Goals

- replace Vim as the reference UI
- make the demo trace a polished operator frontend
- define or repair runtime terminality semantics inside the client

## Exit Evidence

- [x] the demo client can reproduce first/second cancel races over host stdio
- [x] trace output distinguishes the outer run from LLM/tool/projection lanes
- [x] terminal status comes from producer/host completion payloads
- [x] focused tests cover success-before-second-cancel and second-cancel-before-success
- [x] README includes a repeatable manual invocation

## Completion Evidence

- extended `cli_demo_async_client.py` with independently timed first and second
  cancellation requests that stay concurrent with `stream_subscribe` receipt
- added timestamped `ui` traces for outer run frames and inner semantic lanes;
  terminal exit status is read from `push_complete`
- deliberately waits for scheduled cancels after an early natural completion,
  preserving the operator's ability to exercise both sides of the race
- documented a repeatable host-stdio invocation in `README.md`
- verification:
  - `100 passed` with targeted 100% coverage for
    `toas.cli_demo_async_client`
  - Ruff passes for implementation and focused tests
  - real-host time-as-ally cancellation integration passes
  - the gated cancellation integration reproducibly reaches outer
    `push_complete` without an inner end-status event; this is existing gap
    evidence for related task `260705-host-subscribe-terminal-event-parity`,
    not client-side truth the harness should synthesize

## Sweep Follow-Through

- added `scripts/cancel_race_sweep.py`, which:
  - starts a deterministic local streaming LLM stand-in
  - creates a fresh temporary TOAS workspace per trial
  - sweeps either or both cancel timings with explicit bounds and repeats
  - reports response/terminal outcomes and observed transition points
- the first live sweep found a demo-client parity defect: it treated
  `push_complete complete=false reason=request_deadline` as terminal success
  instead of resubscribing as Vim does
- fixed the demo client to resubscribe after explicitly incomplete completion
  frames; focused client coverage remains 100%
- bounded refinement with a 50ms second-cancel gap found the interesting band:
  - first cancel at `2.50s`: 3/3 terminal `cancelled`
  - first cancel at `2.55s`: 2/3 `cancelled`, 1/3 `succeeded`
  - first cancel at `2.60s`: 1/3 `cancelled`, 2/3 `succeeded`
  - first cancel at `2.65s` and later: 3/3 terminal `succeeded`
- after the resubscribe fix, second-cancel response status and outer
  `push_complete` terminal status agreed in every refined trial
- focused verification: `103 passed`; Ruff clean

## Fifteen-Second Stall Search

- corrected the search target after calibration: first cancel fixed at `0.25s`,
  second cancel swept across the earlier shoulder of the clean completion
  boundary
- added second-cancel dispatch timestamps, response RTT measurement, maximum
  inter-UI-event gap measurement, and configurable stall threshold reporting
- retained Vim's `15s` cancel request timeout in the exercise client
- coarse absolute second-cancel search at `2.40s` through `2.56s` found the
  expected clean outcome crossover but no long gaps (`0/9` stalls)
- concentrated search ran 25 trials from `2.40s` through `2.44s` absolute:
  - both `cancelled` and `succeeded` occurred at the same timing point
  - second-cancel RTT remained `0-2ms`
  - maximum observed silent UI interval was `151ms`
  - `0/25` trials crossed the `12s` stall threshold
- negative evidence: the async demo host client does not reproduce the Vim
  15-second stall even when it repeatedly realizes the intended near-terminal
  interleaving
- remaining high-value differential is Vim's synchronous
  `s:toas_local_host_request()` cancel loop sharing one channel with the
  timer/callback subscription consumer; that loop has a literal `15.0s`
  deadline and is not represented by the asyncio demo client's reader task
