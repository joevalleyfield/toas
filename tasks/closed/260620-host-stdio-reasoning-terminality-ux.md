# 260620: host-stdio reasoning terminality UX

Filed as: 260620-host-stdio-reasoning-terminality-ux
FKA:
AKA: host stdio reasoning terminality; answerless streamed run UX; reasoning-only failure completion
Legacy index:

keywords: runtime, transport, closed, usability, stream, host-stdio, vim, reasoning

Parent: `260619-daemon-package-facade-shrinkage`
Related: `260620-retire-host-session-path-env-coupling`; `673`; `668`

## Why this exists

In the host-stdio/Vim path, we observed streamed reasoning reaching the user before the run terminated without a clean answer payload. The runtime invariant is correct, but the user experience looked busy and ambiguous instead of decisively terminal.

The behavior we want is:

- reasoning may stream
- the run must stop cleanly if no `llm_answer` payload arrives
- the user should get a clear terminal error explaining that the answer lane never closed
- the host should not keep spinning or require manual event-list spelunking to understand what happened
- if the stream ends after a thought block that is answer-complete in substance, TOAS may close it cleanly and step a trailing command intent
- when that recovery happens, TOAS should still say that the completion was exceptional

## What we know

- `src/toas/runtime/async_activity_store_impl.py` already fails succeeded runs that saw LLM activity but produced no answer bytes.
- `src/toas/runtime/async_step_runtime_worker.py` emits `llm_reasoning` and `llm_delta` on separate lanes.
- `src/toas/runtime/session_host_stream_bridge.py` currently finishes by emitting a completion frame and logging terminal-missing diagnostics when a terminal event never arrived.
- The confusing case came from the host-stdio/Vim path, not the CLI presenter path.
- `push_complete` frames did not carry terminal status authority, so Vim local-host follow could stay stuck at `cancelling` when completion arrived without a matching terminal event.
- Vim's nonblocking local-host watch pump was narrower than the manual follow path: it only treated explicit `llm_done`/`run_done` types as terminal and could miss `lane=end` terminal events that lacked a `type`.
- Even after that widening, the timer-driven run marker could still lag because the pump preserved `running` until a later `push_complete`, while the manual follow path already treated the terminal event itself as authoritative.
- Fresh cancel repro logs now point deeper than Vim projection: cancellation reaches the runtime, but reasoning-heavy LLM streams can continue because cooperative `BrokenPipeError` cancellation gets absorbed by generic stream-error salvage in `llm.py` instead of escaping to worker finalization.
- Live daemon-RPC repro against `llama-server` showed a second server-side gap: cancel reaches TOAS, but the upstream HTTP stream can stay established until natural completion because async cancel does not own the live stream handle.
- That gap is now narrowed: async cancel registers the live stream closer on the active run and invokes it immediately, which stops model work promptly even if the TCP connection lingers briefly before teardown.
- A synthetic host-stdio LLM stand-in matrix now covers deterministic reform shapes without waiting for a live model to drift: reasoning-only clean EOF, partial-answer parse/interruption salvage, and reasoning-lane cancel all have direct regression coverage.
- The async host worker can now recover a synthetic `llm_answer` from
  trustworthy final projection/reasoning output, emit an explicit warning note,
  and avoid the old `missing llm_answer payload` terminal failure when the
  stream substance is still recoverable.
- That recovery path now includes a narrow tail-command heuristic: if the final
  projection only contains a user command derived from the assistant tail, the
  worker strips that projected command suffix from accumulated reasoning text
  and still surfaces the preceding assistant content as the recovered answer.
- The recovery policy is now stream-policy aware instead of purely
  answer-lane-centric: when reasoning was already streamed to the user-facing
  surface, TOAS can treat that visible reasoning as the substantive completion
  without fabricating an answer lane; when reasoning stayed hidden, TOAS still
  promotes the best recoverable assistant content with an explicit “no answer,
  but we found this” note.
- Command-only tails are now treated more carefully: if hidden reasoning only
  supports a projected user command, TOAS preserves that command projection as
  the useful outcome but no longer fabricates a matching assistant answer just
  to satisfy the answer lane.
## Outcome

Closed 2026-06-22.

The host-stdio/Vim path now has an explicit substantive-recovery boundary plus
failure-surface visibility:

- visible streamed reasoning can complete exceptionally without fabricating an
  answer lane
- hidden reasoning can still synthesize best-effort assistant content when the
  recovered substance is trustworthy
- command-only tails stay command-only instead of turning into fake assistant
  answers
- when recovery is declined, failed runs now keep their partial content and
  append a compact visible cause line, so the user no longer needs to inspect
  log files to understand invariant failures like missing answer payload

## What changed

- Decide where the explicit terminal error should be surfaced in the host-stdio path.
- Ensure the bridge/runtime closes the stream decisively when the answer lane never appears.
- Preserve the useful partial reasoning that already streamed.
- Add focused regression coverage for answerless streamed completion in the host-stdio path.
- Decide the desired contract for malformed reasoning-only streams that currently resist clean terminal closure in the host-level stand-in path.
- Add a heuristic for tail command detection when explicit end-thinking markers are missing.
- Keep the heuristic humble: it only needs to answer “is that a command?” well enough to decide whether the tail should be stepped.
- Make sure successful recovery lands as `TOAS:ASSISTANT` plus an explicit note, not as a silent failure or a raw `TOAS:RUN` fallback.

## Checklist

- [x] Decide whether reasoning-only EOS should synthesize an answer, remain reasoning, or be promoted based on stream policy.
- [x] Identify the host-stdio boundary that should own exceptional terminal messaging for answerless runs.
- [x] Trace how EOS/finalization moves from `llm.py` into the async host path.
- [x] Add a tail-command heuristic for the missing end-thinking case.
- [x] Keep the heuristic local to the recovery path so it does not become a broad parser rewrite.
- [x] Emit a clear note whenever recovery or synthesis is used.
- [x] Add regression coverage for:
  - [x] reasoning streamed and answer recovered
  - [x] reasoning streamed and left visible without synthetic answer recovery
  - [x] thinking on but not streamed, with synthesis
  - [x] streamed thinking with no answer and a clear exceptional terminal message
  - [x] thought block ending in a command-like tail that should be stepped
- [x] Verify the host-stdio/Vim path no longer leaves the user in an ambiguous busy state.
- [x] Carry terminal status through `push_complete` so local-host follow can converge even when terminality is status-owned rather than event-owned.
- [x] Align Vim's local-host watch pump with lane/phase terminality so cancel/fail completion cannot hang waiting for explicit `*_done` event types.
- [x] Commit terminal marker status on authoritative terminal events in the timer-driven Vim watch path instead of waiting for a later completion frame.
- [x] Preserve cooperative `BrokenPipeError` cancellation semantics through `llm.py` instead of salvaging cancelled streams as partial completions.
- [x] Register and invoke an in-flight upstream LLM stream closer from async cancel so server-side generation stops promptly.
- [x] Add deterministic host-stdio stand-in coverage for reasoning-only clean EOF terminal failure shape.
- [x] Add deterministic host-stdio stand-in coverage for partial-answer interrupted-stream salvage shape.
- [x] Add deterministic host-stdio stand-in coverage for reasoning-lane cancel shape.
- [x] Recover a synthetic `llm_answer` from trustworthy final
  projection/reasoning output so host-stdio runs can succeed exceptionally
  instead of failing on missing streamed answer bytes.
- [x] Respect reasoning-stream visibility when deciding whether to synthesize an
  answer lane or instead preserve already-streamed reasoning as the substantive
  completion.

## Exit criteria

- [x] The user sees a clear terminal error instead of an ambiguous linger.
- [x] Async cancel stops upstream model work promptly.
- [x] Reasoning-only streamed runs stop promptly once the failure is known.
- [x] Tests cover the host-stdio completion shape and the no-answer failure path.
- [x] Successful recovery uses a consistent answer marker shape plus an explicit note.

## Sequencing Note

This is now the lead open host-stdio follow-up.

The host session-state cleanup is closed, so the remaining work here can now
focus on terminality UX and recovery semantics without competing with the
ambient-env retirement slice.
