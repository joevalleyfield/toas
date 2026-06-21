# 260620: host-stdio reasoning terminality UX

Filed as: 260620-host-stdio-reasoning-terminality-ux
FKA:
AKA: host stdio reasoning terminality; answerless streamed run UX; reasoning-only failure completion
Legacy index:

keywords: runtime, transport, investigation, active, usability, stream, host-stdio, vim, reasoning

Parent: `260619-daemon-package-facade-shrinkage`
Related: `260620-retire-host-session-path-env-coupling`; `673`; `668`

## Why this exists

In the host-stdio/Vim path, we observed streamed reasoning reaching the user before the run terminated without a clean answer payload. The runtime invariant is correct, but the user experience looked busy and ambiguous instead of decisively terminal.

The behavior we want is:

- reasoning may stream
- the run must stop cleanly if no `llm_answer` payload arrives
- the user should get a clear terminal error explaining that the answer lane never closed
- the host should not keep spinning or require manual event-list spelunking to understand what happened

## What we know

- `src/toas/runtime/async_activity_store_impl.py` already fails succeeded runs that saw LLM activity but produced no answer bytes.
- `src/toas/runtime/async_step_runtime_worker.py` emits `llm_reasoning` and `llm_delta` on separate lanes.
- `src/toas/runtime/session_host_stream_bridge.py` currently finishes by emitting a completion frame and logging terminal-missing diagnostics when a terminal event never arrived.
- The confusing case came from the host-stdio/Vim path, not the CLI presenter path.

## What needs to change

- Decide where the explicit terminal error should be surfaced in the host-stdio path.
- Ensure the bridge/runtime closes the stream decisively when the answer lane never appears.
- Preserve the useful partial reasoning that already streamed.
- Add focused regression coverage for answerless streamed completion in the host-stdio path.

## Exit criteria

- The user sees a clear terminal error instead of an ambiguous linger.
- Reasoning-only streamed runs stop promptly once the failure is known.
- Tests cover the host-stdio completion shape and the no-answer failure path.
