# User-Mediated Action Roundtrip

## Purpose

Record the protocol boundary that separates assistant action proposals from
executed actions.

## Frontier Role Semantics

`## TOAS:USER` and `## TOAS:ASSISTANT` are user-controlled semantic labels
interpreted by `step`:

- `TOAS:USER` means the frontier contains user action-intent;
- `TOAS:ASSISTANT` means the user is presenting the assistant's proposed
  action-intent for processing.

The labels are not authentication credentials. They are part of the operator's
explicit transcript protocol and select the authority context for the step.

## Authority Profiles

```text
user frontier
    → user action-intent
    → intentionally unbounded user authority

assistant frontier
    → assistant action-intent presented by the user
    → user-configured assistant authority policy
```

The direct-user profile remains subject to ordinary argument validation and
operating-system permissions, but should not inherit assistant-specific
workspace, grant, or timeout restrictions. It is intentionally unbounded.

The assistant profile normally supplies bounded grants, workspace, and timeout
controls, but those controls are user-configurable. A blocked assistant action
may be staged for explicit user adoption, but that adoption is a new
user-mediated transcript step rather than an implicit privilege escalation.

## Roundtrip Invariant

There is currently no action execution without a user-submitted `step`.

Assistant output alone is not executable. Execution occurs only when the user
presents the relevant assistant frontier to `step`, at which point the
frontier role determines the applicable authority profile.

This preserves visible, one-layer-at-a-time interaction and prevents an
implicit model/tool loop from becoming the execution model.

## Consequences For Control Flow

The runtime may branch at frontier interpretation and authority selection:

```text
frontier role
    → action-intent extraction
    → authority profile selection
    → shared or profile-parameterized capability execution
    → durable request/result evidence
```

The branch should not be erased merely for structural symmetry. The desired
refinement is to make the intentional authority difference explicit and avoid
applying assistant policy accidentally to user action-intent.

## Regression Specimens

- user process execution through command syntax is unbounded;
- user process execution through structured callable syntax is unbounded;
- assistant process execution through structured callable syntax is bounded;
- user `read_file` outside the workspace is not rejected by assistant-style
  workspace policy;
- assistant `read_file` outside the workspace remains subject to assistant
  workspace policy;
- assistant blocked execution requires an explicit user adoption step before
  the unbounded user profile applies.

## Design Boundary

The user-mediated roundtrip is a core TOAS protocol invariant for this area.
The goal/plan/action intent vocabulary remains an analytical lens around that
protocol, not a requirement that every frontier carry a complete intent
hierarchy.
