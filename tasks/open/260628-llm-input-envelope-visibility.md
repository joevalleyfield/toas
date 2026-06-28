Filed as: 260628-llm-input-envelope-visibility
FKA:
AKA: llm-input exact request mode; packet-inclusive llm input; model request visibility
Legacy index:

keywords: surface, investigation, follow-on, auditability, llm-input, projection, packet, usability

Parent: `260627-history-surface-user-intent-alignment`
Related: `260614-architecture-follow-through-coordination`; `260627-history-affordances-semantic-restaging`

# LLM-Input Envelope Visibility

## Current Reality

`toas llm-input` currently reflects the shared core message-body projection used
before generation:

- control content is dropped
- assistant reasoning blocks are stripped
- adjacent user messages are coalesced

That is valuable and mostly honest, but live generation may still add
deterministic packet/envelope/system material around that projected body before
the provider request is made.

For auditability, the unresolved question is whether the current surface is
complete enough as "show me what the model sees," or whether TOAS should offer
a stronger "show me the exact request shape" mode.

## Desired Reality

TOAS should keep the shared core message projection explicit while deciding
whether to expose an optional stronger envelope-inclusive view.

The likely contract shape is:

- default `llm-input`: projected conversation body
- optional stronger mode: include packet/system shaping that live generation
  adds above that shared body

## Focus

- decide whether the existing message-body view is sufficient for current
  operator diagnosis
- if not, define the smallest useful envelope-inclusive extension
- keep the distinction between "core message projection" and "full request
  packet" explicit in help/output wording
- avoid creating a misleading diagnostic surface that silently mixes the two
  without explanation

## Questions

- Should the first stronger mode show only the final message list, or also
  packet-quality/lens metadata provenance?
- Should the stronger view live under `toas llm-input --envelope`, another
  flag name, or a sibling diagnostic surface?
- What parts of packet shaping are stable enough to surface as operator-facing
  contract versus implementation detail?

## Exit Evidence

- explicit disposition on whether envelope-inclusive visibility is needed now
- if yes, one bounded contract for exposing it
- help/docs language that makes the difference between core message projection
  and full request shaping obvious
- focused implementation slice or explicit deferral note justified by operator
  diagnostic value
