Filed as: 260823-concept-graph-artifact-reuse
FKA:
AKA: materialized concept graph; concept graph artifact; successor graph reuse
Legacy index:

Parent: `260823-concept-graph-compaction`
Related: `260823-handoff-successor-focus-naming`; `260823-projection-discoverability`; `260825-visible-transcript-turn-ids`

keywords: projection, graph, follow-on, contract, usability, transcript

# Materialize And Reuse Concept Graphs

Define and implement the next projection boundary for `concept-graph`: retain
the generated graph as a named `.toas/` artifact that can be inspected and
optionally reused when constructing a successor transcript.

## Motivation

The current first slice durably records the graph projection and appends it to
the transcript, but using it across a session boundary still requires manual
copying or reconstruction. A materialized artifact could preserve the useful
conceptual framing without conflating it with compact's executable handoff.

The intended user-facing behavior is transcript replay through successor
construction. A reused graph should reappear as the same visible assistant
turn it had when generated, preceded by its visible user instruction when that
instruction was present. A reused handoff should likewise preserve its
`/compact` or verbose shape, including an intervening visible instruction turn
when present. Graphs and handoffs may occur in either order, and successor
construction must preserve that order.

The successor operation stages transcript content; it does not execute staged
reconstitution commands or manufacture their results. A handoff at the tail
therefore remains easy to continue directly, while later graph or other turns
remain available for the user to revisit and execute before continuing at the
frontier.

The core operation is editor-neutral. Vim may provide cursor-aware shortcuts
and staging ergonomics, but transcript replay and durable provenance must not
depend on Vim state.

## Open Shape

- decide whether the artifact is a latest projection, an append-only history of
  projections, or both;
- preserve source message/head identity and prompt provenance;
- define the default continuation anchor and replay window for the latest
  recognized handoff; explicit selection of an older turn is deferred to
  `260825-visible-transcript-turn-ids`;
- define the `ToasContinue` controls for including prior graphs by default,
  ignoring recognized graphs, or excluding a graph at the replay tail;
- define content-based artifact naming and collision disambiguation.

## Operational Contract

Successor recognition and staging operate on the reconciled transcript shape.
The event graph may be used as an implementation index or provenance source
when its post-LCP state corresponds to the transcript, but it is not an
independent authority. If graph and transcript state disagree, the transcript's
visible content, ordering, and frontier control staging; the discrepancy may
be reported or recorded, but hidden graph state must not override the
transcript.

The default continuation anchor is the latest valid handoff shape found by
walking backward from the transcript frontier. Explicit selection of an older
handoff is outside this task and belongs to the visible-turn-ID follow-on. The
replay window starts at the beginning of the selected handoff/graph bundle and
extends through the frontier, preserving graph, handoff, visible prompt,
reconstitution-command, result, and later-user turns in their existing order.
No staged command is executed as part of successor creation.

The normal transcript is not expected to accumulate multiple actionable
handoffs. An editor-specific variant may later truncate at a chosen handoff,
run a step, and restore the removed tail, analogous to the existing `\\S`
workflow; that is a UI/editor affordance rather than a requirement for the
editor-neutral or CLI continuation path.

Recognition is structural and user-controlled, not semantic. Concept-graph
content produced by another prompt, model, or manual process becomes eligible
when the user places `/concept-graph` at the end of the preceding user turn and
the graph occupies the following assistant turn. Handoff content follows the
same principle: `/compact` plus the existing handoff-shape recognition makes a
user-authored or otherwise externally produced handoff eligible. Verbose forms
may place a visible instruction turn between the marker and the following
assistant projection, as already supported for verbose compaction. This ability
to intentionally present compatible transcript shapes is desirable; the
content need not carry a graph or handoff claim from hidden history.

A leading graph belongs to the replay bundle only when its `/concept-graph`
user marker, optional visible instruction turn, and assistant graph turn form a
contiguous recognized shape immediately before the selected handoff. A leading
handoff needs no separate bundle rule: the replay window from that handoff
through the frontier carries later graph or other turns with it. Any
recognized handoff is a valid fork point, even when the resulting continuation
is trivial or contains little more than the seed, handoff, and graph. The user
owns whether that fork is useful. `ToasContinue` includes a recognized leading
graph by default; an explicit `--ignore-preceding-graph` control may skip the
leading-graph lookup, and an explicit `--exclude-tail` control may stop replay
at the handoff so nothing after it is staged.

Cancellation is only required before successor-file or durable-successor
mutation, using the normal surface-specific confirmation/name flow. The
append-only history model does not need a post-creation undo operation.

Materialized graph artifacts should use a stable, content-derived readable
name, with a deterministic counter or equivalent collision disambiguator before
the content digest when the same or equivalent content is materialized more
than once. For example: `runtime-history-reuse-2-a31f7c.md`.

Durable reuse data is event bookkeeping: it records which replay operation
included which graph material, for provenance and later inspection. It is not a
separate authority, a hidden selection state, or a claim that an external
consumer must verify before continuation.

The artifact is a materialized, inspectable representation of graph content,
not a competing source of runtime truth. Reuse should be observable in the
successor transcript and/or its durable history, while absence or staleness of
an artifact must leave ordinary compact continuation valid.

## Exit Criteria

An artifact lifecycle and reuse contract are documented, source-linked, and
covered by focused tests. Ordinary compact continuation remains valid when no
graph artifact exists, and reuse is observable in the successor transcript or
its durable history.

Focused tests must cover graph-before-handoff and handoff-before-graph order,
verbose and opaque generation-instruction forms, latest-handoff recognition
when the handoff is not at the transcript tail, `--ignore-preceding-graph` and
`--exclude-tail`, user-controlled reconstitution staging, and
transcript/graph disagreement without hidden graph precedence.

## Implementation Evidence

- Concept-graph results are materialized as readable Markdown under
  `.toas/concept-graphs/`, using a content-derived slug, counter, and digest.
  Projection records retain the artifact path and content digest alongside
  source message/head and prompt provenance.
- Successor construction recognizes the latest transcript-local `/compact`
  handoff, including visible verbose prompt forms with either `/compact` or
  `/compact --verbose`, and replays a contiguous preceding graph bundle plus
  the transcript tail in its existing order.
- `--ignore-preceding-graph` skips only the leading graph lookup. `--exclude-tail`
  ends replay at the handoff. Both controls are available through CLI, RPC, and
  Vim surfaces, without persisting selection state.
- Reconstitution commands remain staged user content and are never executed by
  successor creation. A successor remains an intentional fork with no
  post-creation undo protocol.
- Focused coverage passes, Vim continuation coverage passes, and the full
  Python suite passes with 100% coverage: 2,895 passed, 9 deselected.

## Closure

Closed after implementing the artifact lifecycle and transcript replay contract.
Older explicit handoff selection and visible turn-ID selection remain deferred
to `260825-visible-transcript-turn-ids`.
