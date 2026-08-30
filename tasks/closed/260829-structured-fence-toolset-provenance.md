Filed as: 260829-structured-fence-toolset-provenance
FKA:
AKA: structured fence toolset; toolset marker; callable namespace provenance
Legacy index:

keywords: runtime, implementation, active, correctness, provenance, tooling

Parent: `260803-language-exec-fenced-block-lane`
Depends on: `260829-action-plan-envelope`; `260412-json-callable-lane-separate-parser-and-policy-arc`
Related: `260803-tool-intent-ingress-separation`; `260829-compound-tool-request-records`

# Structured Fence Toolset Provenance

Give structured YAML/JSON callable fences a durable, extensible toolset
imprint without changing the inert callable payload shape.

## Scope

- parse an optional `toolset=<name>` fence attribute;
- resolve omitted structured-lane toolsets to `toas`;
- accept the currently supported toolset set `{toas}` and fail closed for
  unknown values;
- carry the resolved toolset at the action-plan boundary;
- record it as `tool_request` metadata while preserving the payload shape.

## Non-Goals

- adding another tool registry or executor;
- changing authority or adoption semantics;
- requiring explicit toolset selection while only `toas` is supported;
- assigning a toolset to language execution lanes whose language already
  identifies the capability family.

## Acceptance

- equivalent YAML/JSON structured calls default to and record `toolset=toas`;
- explicit `toolset=toas` behaves identically;
- unknown or malformed toolset attributes remain inert/unsupported;
- toolset metadata survives request recording without entering callable args;
- existing single-plan and compound request payload compatibility remains.

## Outcome

Implemented structured-fence toolset validation and provenance. YAML and JSON
structured plans now resolve an omitted toolset to `toas`, accept explicit
`toolset=toas`, and remain unsupported for unknown or malformed toolset
attributes. The resolved value travels through the `ActionPlan` boundary and
is recorded as `tool_request` metadata without changing callable payloads.

Verification: 211 focused runtime, activation, arbitration, action-plan,
history, and graph tests passed; Ruff passed for all changed files.
