Filed as: 260927-state-step-lenient-response
FKA:
AKA: tolerate model response formatting; state-step response normalization
Legacy index:

keywords: runtime, implementation, historical, contract, projection, observability

Parent: `260926-state-step-requirements`
Related: `260927-state-step-raw-response`; `260927-state-step-alpha-loop`

# Tolerate Common State-Step Response Variants

## Objective

Accept common, unambiguous response forms produced by the configured model
without weakening state-patch or capability validation. Use the captured raw
response as the first compatibility example, and improve the model instructions
separately as further evidence accumulates.

## Initial Scope

- Parse JSON wrapped in one conventional outer Markdown code fence, optionally
  tagged `json`.
- Accept `tool` as an alias for `tool_name` on entries in `tool_calls`.
- Preserve the original model content in audit records.
- Reject conflicting `tool` and `tool_name` values; leave unknown tools and
  invalid arguments to existing validation and execution paths.
- Do not change state semantics, patch merging, tool authority, or execution
  timing.

## Acceptance Criteria

- The captured fenced response can be accepted after only the `tool` field is
  normalized to the runtime's canonical call shape.
- Plain JSON behavior remains unchanged.
- Raw response content remains byte-for-byte available in model audit records.
- Tool calls still execute only on a later explicit step through existing
  capability paths.

Status: Complete.

Implementation: The state-step response parser accepts a single outer
Markdown fence tagged `json` (or untagged). Tool-call key normalization now
uses the shared tool-plan canonicalizer; see
[`260927-state-step-normalize-call-shapes`](260927-state-step-normalize-call-shapes.md).
The original content remains on the model-call audit record. Conflicting
aliases are rejected; tool execution remains deferred to a later explicit step.
