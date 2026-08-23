Filed as: 260823-concept-graph-compaction
FKA:
AKA: concept graph in TOAS; compaction prompt transparency; compact handoff prompt; projection prompt surfaces
Legacy index:

keywords: projection, exploration, historical, prompt, transcript, compact, graph, transparency

Related: `260823-intent-tail-focus-trace`; `260823-conversation-map-projection`

# Concept Graph And Compaction Transparency

Define the first TOAS-native prompt/projection affordances for two already
valuable operations: producing a `concept-graph` without importing an outside
prompt, optionally exposing the compaction prompt in the transcript when
`/compact` is used, and exposing the existing non-Vim continuation path through
the CLI.

## Current Reality

`concept-graph` currently exists as an externally supplied prompt/procedure. It
is useful, but using it requires smuggling the prompt into the conversation
instead of invoking a TOAS-owned operation.

`/compact` already performs a mode-shifting continuation operation whose prompt
is currently opaque. The user cannot choose to see the compaction handoff
prompt represented in the transcript, even though that prompt is part of the
operation's meaningful behavior.

The runtime implements successor continuation in
`runtime.session_rotation.continue_session` and serves it through the
`session_continue` request operation. The first implementation slice now also
exposes that operation through the normal `toas` CLI.

These are related as prompt/projection surfaces but are not the same operation:

- `concept-graph` reorganizes transcript material around concepts,
  relationships, loose ends, and active fronts;
- `compact` preserves the executable context needed for near-term continuation.

Neither should be derived from the other.

## First-Slice Implementation

The first implementation slice is complete and verified:

- `concept-graph` uses the TOAS-owned, versioned
  `concept-graph/projection_v1` prompt, is available through the convenience
  operator and prompt discovery, and records its generated graph as a durable
  transcript/history projection.
- `/compact` retains its opaque default. `/compact --verbose` adds the exact
  compaction prompt as an ordinary durable `TOAS:USER` message before the
  generated handoff, while preserving the existing continuation request and
  cache-sensitive mode shift.
- Compact handoff recognition accepts both the existing opaque form and the
  visible-prompt form.
- `toas session continue` exposes the existing non-Vim continuation path and
  delegates to the same runtime implementation used by other transports.
- Focused coverage and the full suite pass, including the existing transport
  and history invariants.

This task remains open as the design home for the deferred affordances below;
the first slice itself is not waiting on them.

## Immediate Objectives

### TOAS-native concept graph

Land `concept-graph` as something TOAS can perform using an explicit,
TOAS-owned prompt or prompt surface, rather than requiring the user to paste an
outside instruction each time. Preserve the graph's output contract and its
distinction between observed, inferred, decided, and unresolved material.

The initial operator behavior should preserve the established use: the
generated concept graph enters the transcript. This supports both retrospective
inspection alongside a handoff and deliberate placement before `/compact` so
the compaction model can use the graph as conceptual framing.

### Optional compaction prompt visibility

Give the user optionality over whether the prompt used by `/compact` is
explicitly represented in the transcript. Preserve the existing opaque/default
behavior unless a visible form is requested or otherwise deliberately enabled.

The design should account for the current cache-sensitive mode shift: the
compaction request appends a tail while preserving the transcript prefix. It
should not assume that making the prompt visible is semantically free.

### CLI continuation exposure

Expose the existing continuation behavior through a normal CLI entry point.
Keep its current recognition and safety contract: continuation is allowed only
when the predecessor ends in a valid compact transition, and the CLI should
share the runtime implementation rather than create a second continuation
path.

### Deferred continuation affordances

Keep the following in scope as documented future possibilities without making
them part of the first slice:

- materialize the concept graph as a named artifact under `.toas/` so successor
  construction can reuse it without manual copying;
- use the concept graph to improve successor transcript naming beyond the
  current first-sentence truncation heuristic;
- decide whether and how staged handoff reconstitution should include a graph
  artifact before or after restoration commands.

## Non-Goals For Inception

- defining a general inference architecture for every future projection;
- making `concept-graph` a richer form of `compact`, or vice versa;
- requiring a new scheduler, observer, or conversation-map surface;
- deciding all future prompt-authoring or prompt-versioning policy;
- changing the manual meaning of swapping `TOAS:USER` to `TOAS:CONTROL`.

## Open Decisions And Follow-On Boundary

The first slice resolved its source and representation contracts. The
remaining decisions are intentionally follow-on work:

- how a concept graph should be materialized as a named `.toas/` artifact and
  reused during successor construction;
- whether staged handoff reconstitution should consume that artifact, and at
  what point relative to restoration commands;
- how graph material should inform successor transcript naming;
- how discoverability and progressive disclosure should expose these prompt and
  projection surfaces as the family grows.

## Exit Criteria

The first slice exits inception when each operation has an observable contract:
the concept graph is TOAS-owned, versioned, durable, and transcript-visible;
compact visibility is opt-in while the default remains unchanged and both
forms remain continuation-safe; and CLI continuation delegates the existing
runtime path. Focused tests plus a green full suite provide the evidence.

Those criteria are now met. Artifact lifecycle, successor reuse, naming, and
progressive disclosure should be separate follow-on tasks rather than reasons
to enlarge this implementation slice.

## Closure

Closed after the first implementation slice landed in TOAS and the deferred
work was split into focused follow-on tasks. This file remains the historical
design record for the original combined slice.
