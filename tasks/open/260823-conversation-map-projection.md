Filed as: 260823-conversation-map-projection
FKA:
AKA: conversation map; intent map; map-as-file; trajectory map; intent tracking projection
Legacy index:

keywords: projection, surface, exploration, inception, transcript, provenance, markdown, intent, graph

Related: `260823-concept-graph-compaction`; `260823-intent-tail-focus-trace`

# Conversation Map Projection

Explore an inspectable conversation-map projection that reifies intent-tracking
events, focus changes, and related provenance without adding cognitive load to
ordinary interaction.

## Current Reality

The normal transcript is currently the primary user-facing surface. That is
becoming a limitation as inferred focus, trajectory, and prioritization become
valuable to observe.

TOAS already manipulates durable history and the filesystem through active
intent and tool use. Intent-tracking events naturally map to a text
representation, making a text file a reasonable initially available
projection. This does not make the filesystem the governing architecture.

## Desired Direction

Reify intent tracking as a readable map that can evolve semi-mechanically and
provide an observer surface for cognitive structure. The map should support:

- current and changing intent/focus;
- links and anchors back to source transcript surfaces or durable events;
- provenance distinguishing direct extraction from inference;
- accumulated trajectory and loose structure without requiring continuous
  narration by the user or agent.

The event log remains the durable source. Markdown or Markdown-like encoding is
the initial projection because it is readable, editor-friendly, link-friendly,
and reusable by existing tools. YAML or JSON may become alternate structural
projections when a consumer needs stricter parsing.

## Non-Goals For Inception

- creating a second conversation or unsolicited push channel;
- deciding whether the map is user-editable or generated-only;
- committing to a scheduler, ambient service, or final visualization;
- making the map a replacement for `compact` or `concept-graph`.

## Exit From Inception

Promote a bounded follow-on when one map entry shape, one source-anchor form,
and one projection/update path are concrete enough to inspect in an existing
editor or tool workflow.
