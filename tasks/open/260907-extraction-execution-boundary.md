Filed as: 260907-extraction-execution-boundary
FKA:
AKA: extraction execution seam; intent workflow boundary; execution taxonomy
Legacy index:

Parent: `260823-projection-discoverability`
Related: `260906-extraction-help-facet`; `260803-tool-intent-ingress-separation`; `260829-action-intent-cluster-plan`

keywords: runtime, investigation, inception, extraction, execution, intent, authority, provenance

# Extraction/Execution Boundary

## Objective

Trace one representative mixed-intent recovery/execution path from candidate
extraction through the adjacent preview, adoption, authorization, and
execution transitions it actually traverses. Determine whether the current
configuration names and runtime ownership describe that path, or whether a
concrete non-help restructuring is warranted.

## Evidence already gathered

- The extraction help facet establishes candidate discovery, source-order and
  lane-boundary preservation, and non-execution as the extraction invariant.
- `extraction.intent_arbitration` affects execution-time candidate selection
  despite living under the extraction namespace.
- `extraction.shell_staging` and `extraction.projection_shape` affect the
  adjacent staging/projection transitions and must be considered where the
  representative path crosses them.
- Existing runtime records already preserve mixed-intent IDs, arbitration
  outcomes, replay candidates, and queue transitions; this task checks
  whether those records compose into a coherent operator path before proposing
  new records or config sections.

## Acceptance criteria

- Produce a compact boundary map for one representative mixed-intent path:
  extracted candidates → preview/selection → adoption or replay →
  authorization/queue where applicable → execution/result.
- Identify the owning runtime seam, state effect, authority requirement, and
  provenance at each traversed transition.
- Disposition `extraction.intent_arbitration`, `extraction.shell_staging`, and
  `extraction.projection_shape` in the context of that path: retain,
  rename/rehome, or defer with a reason.
- Decide whether an `execution` configuration domain is justified, or whether
  execution remains a behavioral/workflow topic with existing policy domains.
- Preserve the distinction between extraction, execution, and authorization;
  do not collapse them into one help topic or one runtime operation.

## Non-goals

- Do not implement new execution behavior or change authority semantics in
  this mapping task.
- Do not map every replay, queue, shell-staging, or projection-shape variant;
  follow only the transitions needed for the chosen representative path.
- Do not rename the public commands solely to resolve vocabulary discomfort.
- Do not create a universal help registry or broaden the asset migration.

## Verification

Use existing corpus records, runtime source, and targeted behavior tests. The
deliverable is a reviewed boundary/disposition note and a follow-on task only
if a concrete implementation seam is established.
