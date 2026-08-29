# Action Path: As-Is And Green-Field Crosswalk

## Purpose

Compare the organically evolved action path with a clean conceptual model,
then use the architectural pressures to guide incremental change rather than
replace working behavior for the sake of symmetry.

## Conceptual Green-Field Model

```text
ingress → normalized action → authority → execution → durable result → projection
```

This is a reasoning model. It does not require a new object hierarchy or one
record kind for every lane.

## Crosswalk

| Dimension | Organic current shape | Green-field tendency | Pressure | Direction |
|---|---|---|---|---|
| Ingress | YAML, shell, frontier arbitration, and native response fields | Explicit adapters into one downstream boundary | New lanes otherwise duplicate parsing and policy | Add an adapter seam while preserving recognition differences |
| Action shape | Normalized dictionaries with `tool_name`, `args`, and optional rationale | Provider-neutral typed action/plan | Dictionaries are flexible but weakly express invariants | Preserve the incumbent shape until a concrete need requires more structure |
| Authority | Role- and lane-sensitive execution paths, grants, workspace modes, and timeouts | Explicit authority context before shared execution | Role can become an implicit policy matrix | Separate provenance from effective authority without equalizing power |
| Execution | Registry, capability runners, runtime step paths, and replay paths | One capability executor | Refactoring risks semantic drift | Strengthen existing seams |
| Durable history | Tool, command, queue, result, model-call, and projection records | Common semantic dimensions with source-specific records | New lanes could create standards-plus-one records | Share taxonomy and relationships, not necessarily record kinds |
| Projection | Result rendering, recovery, and replay projections | Read-only views over durable facts | Rendering must not become execution | Preserve and test non-reexecution |
| Provider boundary | Provider adapters already expose native call data | Normalize before runtime semantics | Provider fields must not become authority | Add a provider-neutral bridge |
| Testing | Large behavioral suite around existing quirks | Cross-lane conformance scenarios | Rewrite would discard evidence | Treat existing tests as compatibility specification |

## Organic Strengths To Preserve

- direct-user and assistant authority are intentionally different;
- resilient text lanes survive blocked or rewritten provider channels;
- append-only history preserves prior facts;
- staged recovery and restaging already encode useful semantics;
- existing tests capture real failure and arbitration behavior.

## Main Architectural Pressure

The user/assistant distinction currently supplies both provenance and control
flow. The desired direction is to preserve the provenance and authority
difference while reducing accidental executor duplication:

```text
origin + ingress
    → authority profile
    → effective execution context
    → shared execution strategy
```

The direct-user shell lane may remain substantially more powerful. That power
should be represented as an explicit authority basis and effective policy,
not inferred only from the source role or the function selected.

## Issue Disposition

### Core seam strengthening

- tool-intent ingress and harness separation;
- executable fence lanes and activators;
- native provider ingress;
- JSON serialization as a conditional sibling.

### Execution and evidence support

- shell lane spawn semantics;
- Windows shell launcher and path resolution;
- transport equivalence certification;
- activity health telemetry;
- history and semantic restaging.

### Adjacent projections

- intent-tail/focus trace;
- conversation-map projection;
- projection discoverability;
- operator/driver working memory.

### Conditional or orthogonal

- transcript parallelism and broader orchestration;
- transcript LCP checkpoint optimization.

## Migration Posture

1. Preserve current normalized plans and record families.
2. Identify existing functions that already act as boundaries.
3. Introduce adapter or policy seams only where a second implementation needs them.
4. Add identity and provenance where native calls, retries, or restaging expose a real ambiguity.
5. Protect existing behavior with current tests and add cross-lane conformance tests.
6. Keep broader plan-intent projections out of the action execution prerequisite path.

