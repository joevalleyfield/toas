# Shared Action History Taxonomy

## Purpose

Define the semantic dimensions that different action and execution records
should share, without requiring one universal record shape.

The goal is to make durable history extensible, resilient, logical, and
discoverable as new ingress lanes and authority profiles are added.

## Shared Dimensions

| Dimension | Meaning |
|---|---|
| Subject | The operation, capability, command, or state transition concerned |
| Provenance | Who or what produced it, and through which ingress |
| Context | Related message, objective, plan, workspace, or prior event |
| Authority | The basis on which it was permitted, rejected, or deferred |
| Effective policy | Grants, limits, environment, workspace, and timeout actually applied |
| Lifecycle | Recognized, normalized, accepted, attempted, completed, failed, blocked, or indeterminate |
| Execution identity | Request, attempt, retry, queue, or restaging relationship |
| Outcome | Success, failure, cancellation, timeout, blocked execution, and operation result |
| Evidence | Raw input, normalized form, diagnostics, provider details, and source references |
| Projection | How durable facts were rendered or exposed to a consumer |

These dimensions should let a downstream consumer answer:

- What was requested?
- Where did it come from?
- What authority applied?
- What policy was effective?
- Was it attempted?
- What happened?
- What is it related to?
- Is this evidence or projection?

## Current Record Families

Current record kinds can remain distinct while becoming comparable through the
shared dimensions:

- message events provide source, content, and lineage;
- explicit operator objectives provide optional task context;
- tool requests represent callable action requests;
- command requests represent direct-user action requests;
- tool and command results represent distinct outcome paths;
- execution queues represent staged execution state;
- model-call records provide provider interaction evidence;
- lens artifacts provide derived projection artifacts.

No record family should be reclassified merely because its name contains a
shared word. A declared objective is not a callable action; an execution
candidate is not a durable objective; an optional rationale is not authority.

## Authority Representation

`origin_role` is provenance, not authority.

The direct-user shell lane can intentionally have greater power than the
assistant callable lane. That distinction should remain visible downstream
through concepts such as:

```text
origin_role
ingress_kind
authority_basis
policy_source
effective_policy
execution_kind
```

The exact field names remain open. The requirement is that authority not be
recoverable only from which control-flow branch or Python function happened to
run.

## Record-Kind Principle

Shared taxonomy does not mean shared record kind. Source-specific records may
remain separate when they preserve meaningful ingress or authority semantics.
The commonality should live in semantic dimensions, relationships, and query
vocabulary rather than in a forced lowest-common-denominator payload.

## Design Rules

- normalize action meaning before capability execution;
- keep provenance, authority, effective policy, and outcome distinct;
- do not infer authority from a broad intent or objective;
- do not treat execution results as proof of underlying user purpose;
- preserve source-specific diagnostics and policy differences;
- make projections observational and non-executable;
- add a new record or identity only when current relationships cannot express
  the required meaning;
- prefer one shared vocabulary over another parallel naming system.

## Open Questions

- Which shared dimensions must be durable versus reconstructable?
- Is message linkage sufficient for tool requests, or are action/attempt ids needed?
- Which effective policy details are necessary for audit and replay decisions?
- How should retries and restaging relate to the original request?
- Which objective or plan relationships should be explicit rather than optional context?

