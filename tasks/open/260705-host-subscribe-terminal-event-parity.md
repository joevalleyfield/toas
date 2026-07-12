Filed as: 260705-host-subscribe-terminal-event-parity
FKA:
AKA: host stream terminal event synthesis; subscribe parity; llm_done terminal event contract
Legacy index:

keywords: runtime, hardening, inception, contract, transport, stream, parity, host

Parent: `260614-architecture-follow-through-coordination`
Related: `260602-transport-equivalence-certification`; `260620-host-stdio-reasoning-terminality-ux`; `260705-cancel-timeout-terminality-contract`

# Host Subscribe Terminal Event Parity

## Current Reality

The host `stream_subscribe` bridge can reach terminal run status without
receiving a final `llm_answer` end event. A peeled follow-on experiment tried
to repair that by synthesizing `llm_done` events in the live stdio host path,
while leaving the list-return path unchanged.

That pressure is real, but the attempted fix would introduce transport-specific
event semantics:

- live stdio subscribe would see synthetic terminal events
- non-streaming/list-return callers would not

The architecture notes make this pressure more specific:

- Activity Lifecycle owns status, stream events, cancellation, and terminality
- Session Host Supervision must not decide activity terminality
- Transport And Protocol adapters must not define semantic success
- child-lane done markers must not be fabricated into whole-run truth by a
  carrier path

That means the open question is not only "should subscribers get a terminal
answer-shaped event?" but also "which domain, if any, is allowed to originate
that event?"

## Desired Reality

TOAS should decide explicitly whether subscriber-visible terminal answer events
are:

- required lifecycle facts emitted by the underlying activity stream
- a presentation/projection convenience owned by an explicit lowering adapter
- or intentionally absent, with terminal status carried only by completion
  payloads

Whatever the answer is, the contract should preserve parity across equivalent
transport surfaces unless a deliberate divergence is documented and tested.
Host/transport adapters should not quietly become semantic owners just because
they are the nearest place to patch subscriber-visible behavior.

The recent Vim cancel/finalization spike adds a stronger downstream pressure:

- clients should not be rectifying terminal truth from replayed event lists,
  dedup state, transport fallbacks, and ad hoc catch-up probes
- once a run is terminal, host/runtime should be able to provide a canonical
  terminal shape that already reflects the owned semantic outcome
- client surfaces may still choose how to render that shape, but they should
  not have to decide what the terminal answer/run consequence *is*

In other words, this task is not only about whether terminal answer-shaped
events exist. It is also about whether terminal subscriber truth is owned
upstream strongly enough that Vim or any other client can stop doing semantic
reconstruction.

## Scope

- define the terminal-event contract for host `stream_subscribe` against the
  documented ownership model
- decide whether any terminal answer-shaped event belongs to Activity
  Lifecycle, Projection/Rendering, or nowhere
- define whether a canonical terminal subscriber snapshot/tail is an owned
  host/runtime consequence rather than a client-side reconstruction exercise
- keep transport-path parity and subscriber expectations explicit in tests
- reject host-bridge synthesis if it would make Session Host Supervision or
  Transport And Protocol the de facto owner of terminal semantics

## Non-Goals

- redesign of the whole streaming protocol
- unrelated host stdio refactors
- broad acceptance-suite restaging beyond the terminal-event question

## Progress Notes

- current Vim local-host cancel work exposed a smaller but real subscriber
  pressure: if the watch pump is idle in `harvest` with no pending ingress,
  accepting `cancelling` should immediately nudge the pump back to
  `subscribe_send` so terminal answer/status events are not delayed behind an
  otherwise quiet harvest window
- that nudge is useful as a client-surface correctness stopgap, but it does
  not settle the ownership question in this task: the stronger fix is still
  for host/runtime to provide canonical terminal subscribe truth without
  forcing clients to reconstruct or poll for it

## Exit Evidence

- [ ] terminal subscribe semantics are explicit for both event payloads and
  completion payloads
- [ ] client surfaces no longer need to reconstruct terminal truth from replay,
  dedup, fallback, and catch-up combinations
- [ ] parity expectations between live stdio and compatibility/list-return
  paths are tested
- [ ] any subscriber-visible terminal answer event is attributed to an owning
  domain consistent with the architecture notes
- [ ] host/transport code is not implicitly promoted into a terminality owner
  just to satisfy subscriber convenience
