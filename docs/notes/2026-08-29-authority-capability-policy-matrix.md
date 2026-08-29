# Authority And Capability Policy Matrix

## Purpose

Make intentional authority differences explicit without turning every
origin/ingress/capability combination into a separate control-flow path.

This note is a planning artifact for the action/execution/history subsystem.
It does not prescribe a new executor, record kind, or field naming yet.

## Core Distinction

`origin_role` describes provenance. It does not, by itself, describe power.

Effective authority is a function of at least:

```text
origin role + ingress kind + capability + workspace/configuration
    → authority profile
    → effective execution context
    → runner
```

The direct-user lane is intentionally unbounded. The assistant callable lane
uses an assistant execution policy that is normally bounded but configurable
by the user. The goal is not to equalize them, but to make the selected policy
inspectable downstream.

Boundedness is useful for the assistant/tool authority profile and for testing
that profile. It is not a production restriction on direct-user actions: an
operator who wants to exercise the bounded policy can enter or construct the
assistant context directly, so imposing those bounds on the operator lane adds
friction without adding meaningful protection. Assistant policy controls are
user-configurable and should remain extensible; direct-user policy could be
made configurable as well, but no current use case justifies that complexity.

## Provisional Matrix

| Ingress | Origin | Capability family | Authority profile | Effective behavior | Current record path |
|---|---|---|---|---|---|
| direct command syntax | user | any directly requested capability | operator/unbounded | no TOAS-imposed assistant-style bounds; ordinary capability validation and OS limits still apply | `command_request` / `command_result` |
| direct YAML callable | user | any directly requested capability | operator/unbounded | should not inherit assistant tool restrictions | often `tool_request` / `tool_result` |
| textual callable | assistant | process execution | configured assistant tool policy | command grants, workspace checks, assistant timeout as configured | `tool_request` / `tool_result` |
| native provider call | assistant/provider | registered capability | not yet fully connected | should enter shared normalization and policy path | currently transport-edge `tool_calls` |
| user or assistant | file access | capability-specific workspace policy | workspace mode and roots | outside-workspace access currently depends on workspace mode | `tool_request` / `tool_result` |
| user or assistant | write/patch | capability-specific write policy | workspace and write safeguards | separate from process-execution authority | `tool_request` / `tool_result` |

## `read_file` Observation

`read_file` uses the shared workspace path resolver. The intended authority
rule is that a direct-user request is unbounded, so an outside-workspace path
should not be rejected merely because it came through the user lane. The
current user path delegates non-process capabilities through assistant-style
execution machinery, making this an implementation bug rather than a desired
capability-specific restriction.

For assistant requests, workspace behavior is policy-configurable. Strict mode
may reject an outside-workspace path; unbounded mode may allow it when the user
has selected that policy. Strict mode is therefore not the definition of
assistant compliance; applying the configured assistant policy is.

The relevant distinction is:

```text
direct-user capability request: intentionally unbounded within TOAS
assistant capability request: governed by user-configured assistant policy
ordinary capability validation and operating-system permissions: still apply
```

This work can expose and resolve the mismatch without adding a new exception
for `read_file`: the user authority profile should be selected before the
capability-specific runner, rather than inferred from whether the capability
happens to be process execution.

Role labels in transcript content are not authentication credentials, but they
are intentional semantic protocol boundaries. `TOAS:USER` marks user
action-intent; `TOAS:ASSISTANT` tells `step` that the user is presenting the
assistant's proposed action-intent for processing under assistant policy. The
user controls this roundtrip by design. There is currently no action execution
without the user submitting a step, and the role boundary determines which
authority profile that submitted frontier receives.

## Process-Execution Naming Pressure

The `shell` capability currently covers:

- argv execution;
- command-string execution;
- shell-launcher selection;
- script execution;
- command allowlists;
- cwd and environment shaping;
- timeout and subprocess handling.

Its semantic center is therefore closer to process execution than interactive
shell use. `exec` or `process_exec` may be clearer future vocabulary, but the
existing name is an incumbent across callable syntax, tests, prompts, and
result renderers. Naming should be evaluated alongside the taxonomy, not
changed independently for appearance.

## Downstream Evidence Requirements

For any executed request, a downstream consumer should be able to distinguish:

- source role and ingress;
- capability family;
- authority basis;
- policy source;
- effective workspace, grants, timeout, and environment rules where relevant;
- whether execution was attempted;
- terminal outcome and failure classification;
- request, attempt, retry, or restaging relationships.

The evidence may be represented through existing specialized records plus
shared fields or relationships. A universal record kind is not required.

## Planning Consequences

- Keep direct-user capability execution unbounded by design.
- Do not infer authority solely from `user` versus `assistant`.
- Treat `user` provenance as selecting the unbounded operator authority profile,
  subject to ordinary validation and operating-system permissions.
- Treat assistant execution policy as user-configurable, with boundedness as a
  normal profile rather than an immutable ceiling.
- Preserve the user-mediated roundtrip: assistant action-intent is not
  executable until the user presents it to `step` at an assistant frontier.
- Treat transcript role labels as semantic protocol inputs, not authentication
  claims.
- Use `read_file` as a focused regression specimen for the accidental bounds
  currently applied outside the process-execution branch.
- Treat native provider integration as an ingress connection problem until it demonstrates a missing policy or identity seam.
- Treat process-execution renaming as a taxonomy decision with compatibility impact.
- Group tests by authority policy and capability behavior, not only by current control-flow function.

## Next Evidence Slice

Compare the following cases using the existing test suite and durable record
shapes:

1. direct-user process execution through command syntax;
2. direct-user process execution through structured callable syntax;
3. assistant process execution through structured callable syntax;
4. direct-user `read_file` inside and outside the workspace;
5. assistant `read_file` inside and outside the workspace;
6. explicit OS or capability validation failures that remain applicable to both.

The result should identify which differences are intentional policy, which are
incidental control flow, and which are absent from downstream evidence.
