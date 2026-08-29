# Action-Intent Cluster Framing

## Purpose

Provide a shared planning vocabulary for the subsystem that receives bounded
action requests, applies authority, executes capabilities, records outcomes,
and exposes consequences at explicit TOAS step boundaries.

This is a cluster-level design note, not a TOAS-wide ontology or runtime
contract.

## Provisional Intent

Define a provenance-bearing path from recognized action requests to canonical
history and explicit TOAS step outcomes.

Accept those requests through supported ingress forms, normalize them into a
shared representation, apply the existing authority and capability rules,
record the request and outcome in canonical history, and expose the resulting
state at an explicit TOAS step boundary.

## Intent As A Local Analytical Lens

Intent operates at different scales:

```text
goal intent
    ↓ formulate / adopt
plan intent
    ↓ decompose / choose
action intent
    ↓ recognize / authorize / execute
outcome and evidence
    ↺ revise plan or clarify goal
```

These terms are useful for classifying the work, but they are not required to
be universal record types, a fixed runtime hierarchy, or a prerequisite chain.

- Goal intent is a desired end state or direction, possibly still nebulous.
- Plan intent is an adopted objective and trajectory for pursuing a goal.
- Action intent is a bounded operation request that an ingress can recognize.

Only recognized bounded action intent enters the execution path. Larger goal
and plan context may be absent, optional, or inferred, and must not silently
become execution authority.

## Local Vocabulary

- formulate a goal;
- adopt or revise a plan;
- decompose a plan into actions;
- recognize an action request;
- normalize an action request;
- resolve authority;
- execute an action;
- record request and outcome evidence;
- project resulting state.

Use qualified terms where scale matters. Avoid leaving `intent`, `resolution`,
`replay`, or `equivalence` unqualified.

## Boundary

The subsystem covers:

- action ingress and recognition;
- provider- and syntax-neutral normalization;
- authority and capability decisions;
- bounded execution;
- durable request and result evidence;
- visible consequence projection.

It does not yet own general goal formation, broad plan management, inferred
user psychology, automatic agent loops, or every plan-intent projection.

An explicit operator-maintained objective is optional context. It is not an
action request, an authority grant, or an inferred goal. Its replacement is
tracked separately in [260829: Declared Objective Lane](../../tasks/open/260829-declared-objective-lane.md).

## Design Principle

The goal is not to make every form of intent identical. The goal is to give
related action, authority, execution, and outcome facts a shared vocabulary so
new ingress lanes do not require new semantics by exception.

