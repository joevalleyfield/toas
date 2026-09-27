Filed as: 260927-state-step-response-shapes
FKA:
AKA: state-step model response examples; natural tool call shapes
Legacy index:

keywords: runtime, exploration, historical, contract, projection, observability

Parent: `260926-state-step-requirements`
Related: `260927-state-step-raw-response`; `260927-state-step-lenient-response`; `260927-state-step-normalize-call-shapes`

# Learn From Natural State-Step Response Shapes

## Objective

Use unaltered response previews to learn which response forms the model
naturally produces under the current lightweight instructions. Treat repeated
forms as evidence for a gradually broader accepted contract, while preserving
raw samples and existing tool authority/execution boundaries.

## Initial Observations

The previewed state-step response from 2026-09-27 used a fenced JSON object and
this tool-call shape:

```json
{"tool": "search", "args": {"query": "open issues"}}
```

A later response to the unchanged state used another fenced JSON object and
this shape:

```json
{"name": "shell", "arguments": {"command": "pwd && ls -la"}}
```

The response-only preview printed both forms unaltered and executed neither.
The first form's `tool` alias is accepted by
[`260927-state-step-lenient-response`](260927-state-step-lenient-response.md).
The `name`/`arguments` form has not yet been normalized to TOAS's canonical
`tool_name`/`args` call shape.

A repeat against the same unadvanced state again used a fenced JSON object,
but proposed no tools. Its patch added an uncertainty that repository and
issue-tracker context were missing, and replaced the next steps with asking for
that context and identifying the issue source.

A further repeat again used fenced JSON and proposed one call with the earlier
`tool`/`args` spelling, this time `code_survey` with empty arguments. Its patch
recommended identifying the repository, inspecting its structure, and
searching for issue-tracking references. No proposal was accepted and no call
was executed.

Normal stepping then provided additional evidence. The model proposed
`name`/`arguments`, `tool_name`/`parameters`, and `operation`/`arguments`
shapes. The `name` form failed execution with a missing `tool_name`; the
`parameters` key was ignored and capability help defaulted to the core topic.
The shared YAML canonicalizer already supports `operation`/`arguments`, while
the response-shapes follow-on extends it to the other observed aliases.

The latest accepted proposal contained four `operation`/`arguments` calls
(`get_structure`, two `search` calls, and a read-only `shell` listing). State-
step now passes both new and pending calls through the shared normalizer; the
accepted batch remains pending execution in the current local session.

## Disposition

The samples selected a shared-normalizer follow-on:
[`260927-state-step-normalize-call-shapes`](260927-state-step-normalize-call-shapes.md).
Instruction improvements remain a separately observable axis.

Status: Complete — observed response forms and selected a bounded
normalization increment.
