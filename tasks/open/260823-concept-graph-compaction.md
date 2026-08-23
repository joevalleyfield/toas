Filed as: 260823-concept-graph-compaction
FKA:
AKA: concept graph in TOAS; compaction prompt transparency; compact handoff prompt; projection prompt surfaces
Legacy index:

keywords: projection, exploration, inception, prompt, transcript, compact, graph, transparency

Related: `260823-intent-tail-focus-trace`; `260823-conversation-map-projection`

# Concept Graph And Compaction Transparency

Define the first TOAS-native prompt/projection affordances for two already
valuable operations: producing a `concept-graph` without importing an outside
prompt, and optionally exposing the compaction prompt in the transcript when
`/compact` is used.

## Current Reality

`concept-graph` currently exists as an externally supplied prompt/procedure. It
is useful, but using it requires smuggling the prompt into the conversation
instead of invoking a TOAS-owned operation.

`/compact` already performs a mode-shifting continuation operation whose prompt
is currently opaque. The user cannot choose to see the compaction handoff
prompt represented in the transcript, even though that prompt is part of the
operation's meaningful behavior.

These are related as prompt/projection surfaces but are not the same operation:

- `concept-graph` reorganizes transcript material around concepts,
  relationships, loose ends, and active fronts;
- `compact` preserves the executable context needed for near-term continuation.

Neither should be derived from the other.

## Immediate Objectives

### TOAS-native concept graph

Land `concept-graph` as something TOAS can perform using an explicit,
TOAS-owned prompt or prompt surface, rather than requiring the user to paste an
outside instruction each time. Preserve the graph's output contract and its
distinction between observed, inferred, decided, and unresolved material.

### Optional compaction prompt visibility

Give the user optionality over whether the prompt used by `/compact` is
explicitly represented in the transcript. Preserve the existing opaque/default
behavior unless a visible form is requested or otherwise deliberately enabled.

The design should account for the current cache-sensitive mode shift: the
compaction request appends a tail while preserving the transcript prefix. It
should not assume that making the prompt visible is semantically free.

## Non-Goals For Inception

- defining a general inference architecture for every future projection;
- making `concept-graph` a richer form of `compact`, or vice versa;
- requiring a new scheduler, observer, or conversation-map surface;
- deciding all future prompt-authoring or prompt-versioning policy.

## Open Decisions

- whether visible compaction prompts are transcript events, a rendered view of
  the request, or both;
- how a TOAS-native concept-graph prompt is selected, versioned, and exposed;
- whether the visible and opaque compaction paths must produce byte-identical
  continuation requests apart from transcript representation.

## Exit From Inception

Promote bounded follow-ons when the concept-graph invocation surface and the
compaction visibility behavior each have a concrete prompt source, transcript
representation, and focused evidence story.
