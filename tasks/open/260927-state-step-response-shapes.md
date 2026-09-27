Filed as: 260927-state-step-response-shapes
FKA:
AKA: state-step model response examples; natural tool call shapes
Legacy index:

keywords: runtime, exploration, active, contract, projection, observability

Parent: `260926-state-step-requirements`
Related: `260927-state-step-raw-response`; `260927-state-step-lenient-response`

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

## Next Evidence

Use these samples to choose the next narrow normalization increment. Keep
instruction improvements as a related but separately observable axis.

Status: Ready.
