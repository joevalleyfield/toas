Filed as: 260927-state-step-normalize-call-shapes
FKA:
AKA: state-step tool-call aliases; normalize model tool calls
Legacy index:

keywords: runtime, implementation, active, compatibility, contract, tooling

Parent: `260926-state-step-requirements`
Depends on: `260927-state-step-response-shapes`
Related: `260927-state-step-lenient-response`

# Normalize Natural State-Step Tool Call Shapes

## Objective

Normalize tool-call shapes observed in raw state-step model responses through
TOAS's shared tool-plan canonicalizer before accepting or executing the calls.
Keep the canonical runtime call shape as `tool_name` plus `args`.

## Observed Forms

- `tool` with `args`
- `name` with `arguments`
- `tool_name` with `parameters`
- `operation` with `arguments`

## Acceptance Criteria

- The aliases above normalize to the same canonical call representation.
- Conflicting name or argument aliases fail with a clear validation error.
- Both newly inferred calls and already-pending calls use the same normalizer.
- Raw response content remains unchanged in audit; tool execution remains on a
  later explicit step through existing capability and permission paths.

Status: Complete.

Implementation: State-step now delegates response call normalization to the
shared plan normalizer at inference and pending-call execution. The shared
normalizer accepts `tool_name`, `operation`, `name`, and `tool`, plus
`args`, `arguments`, `params`, and `parameters`, and emits `tool_name`/`args`.
Conflicting aliases are rejected. Existing pending calls are normalized when
executed without rewriting their immutable history record.
