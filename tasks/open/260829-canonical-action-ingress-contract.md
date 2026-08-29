Filed as: 260829-canonical-action-ingress-contract
FKA:
AKA: canonical tool intent; action ingress contract; normalized action boundary
Legacy index:

keywords: runtime, decomp, inception, contract, provenance, frontier, tooling

Parent: `260803-tool-intent-ingress-separation`
Depends on: `260829-user-authority-profile-propagation`
Related: `260803-language-exec-fenced-block-lane`; `260412-json-callable-lane-parser-and-policy`; `260530-shell-lane-spawn-semantics`

# Canonical Action Ingress Contract

Define the post-recognition boundary shared by structured, native, and direct
user action ingress without requiring a universal TOAS intent ontology or an
immediate replacement for the incumbent normalized plan dictionaries.

## Intent

Specify what an ingress adapter must hand to the runtime, what source and
provenance facts must remain alongside the callable arguments, and how the
recognized action becomes an explicit TOAS step consequence.

## Current Incumbent

`src/toas/graph.py::normalize_tool_plan` already provides a useful shared
starting shape:

```python
[{"tool_name": "read_file", "args": {"path": "README.md"}}]
```

It normalizes callable aliases and optional intention text before capability
validation. This task must first test whether that shape is sufficient for the
next ingress slice. A typed domain object is an option, not an assumed result.

## Scope

- define the adapter boundary after recognition/deserialization and before
  authority resolution;
- decide which action fields are semantic inputs versus source/provenance
  metadata;
- keep provider call ids, source spans, ingress lane, and raw diagnostic refs
  out of capability arguments;
- specify ordered-plan position and grouping identity where first-failure or
  staged remainder behavior depends on them;
- define user and assistant frontier transitions, including the fact that
  assistant output alone is not user authority;
- define deterministic arbitration when multiple ingress candidates are
  present in one frontier;
- identify the smallest implementation seam and its focused test corpus.

## Required Contract Questions

1. Can the incumbent normalized list-of-dictionaries represent every currently
   supported action without losing required identity or provenance?
2. If not, what is the smallest adjacent envelope or domain type that adds the
   missing invariant without moving provider fields into tool arguments?
3. Which facts must be durable request metadata, which belong only to
   diagnostics, and which are projection-only?
4. How does each adapter represent recognition failure, ambiguity, and a valid
   action that awaits the user-mediated `step` boundary?
5. What does “equivalent” mean for action lanes: same normalized arguments,
   same capability outcome, same durable facts, same projection, or a specified
   subset of those?

## Boundaries

- direct-user action selects the intentionally unbounded user profile;
- assistant action selects the user-configured assistant policy;
- authority is resolved after ingress and is never granted by source syntax,
  provider metadata, or a requested context field;
- adapters parse and normalize only; they do not execute, schedule retries,
  write durable results, or create hidden loops;
- explicit `step` remains the boundary at which the recognized consequence is
  resolved.

## Non-Goals

- implementing native provider calling;
- implementing executable-fence or JSON recognition;
- replacing all normalized dictionaries with a class hierarchy;
- redesigning durable record families;
- changing capability validation or first-failure execution semantics;
- making goal, plan, and action intent universal runtime record types.

## Done When

- a canonical action boundary is documented with valid, invalid, ambiguous,
  and awaiting-step examples;
- an ingress ownership matrix covers direct user, YAML, JSON, executable
  fences, and native provider calls;
- provenance and authority fields are explicitly separated from capability
  arguments;
- mixed-candidate arbitration and frontier transitions are deterministic;
- the decision to retain, wrap, or replace the incumbent normalized shape is
  explicit;
- any implementation follow-on has one owner, bounded write surfaces, and a
  focused test story.

## Current Status

This is a requirements child. No implementation should begin until the
contract questions are answered from current code and existing tests.
