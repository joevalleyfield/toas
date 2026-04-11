# Hierarchical Context Lifecycle And Lensing

## Insight

Context management should be hierarchical in two dimensions:

- **state hierarchy**: where information lives and how durable it is
- **meaning hierarchy**: how information is distilled into useful abstractions

The goal is not primarily shorter prompts. The goal is better throughput and better decisions by supplying the right information at the right abstraction level to the right process at the right time.

## Why It Matters

- User-only curation becomes a bottleneck.
- Flat context streams mix high-value and low-value detail.
- Model quality depends more on context shape than raw context volume.
- Replay/debug integrity requires preserving durable truth while allowing aggressive derived refinement.

## State Hierarchy

1. **Raw truth** (`events.jsonl`)
   - Immutable durable history.
   - Never rewritten by compaction/refinement.
2. **Working projection** (`session.md` and equivalent projections)
   - Operator-facing control surface.
   - May be edited, but history semantics remain append-only/branching.
3. **Derived memory**
   - Summaries, indexes, maps, outlines, task clusters, semantic tags.
   - Explicitly derived from raw truth/projection with provenance.
4. **Execution packets**
   - Just-in-time, step-scoped context bundles for a specific model/process.
   - Disposable, reproducible from lower layers.

## Meaning Hierarchy

1. **Atoms**: concrete facts/snippets/events.
2. **Clusters**: related atoms grouped by task/theme/intent.
3. **Lenses**: goal-specific views over clusters (what matters now).
4. **Strategy frame**: highest-level framing for current phase and success criteria.

## Autonomy Gradient

Default toward automation where risk is low:

- **automatic**:
  - derive/update summaries and maps
  - build execution packets
  - apply low-risk refinement in derived layers
- **user-gated**:
  - mutation of user-authored transcript text
  - destructive pruning of material that is hard to recover
  - policy changes controlling refinement/compaction behavior
- **LLM/overwatch-assisted**:
  - propose refinements
  - score packet quality
  - escalate when confidence is low

## Artifact Shape For Lensing

Derived artifacts should be compact and composable:

- **title**
- **3–6 line prose distillation**
- **source pointers** (event ids / ranges / anchors)
- **use-when cue** (what question/phase this artifact is for)

This keeps lens assembly fast and avoids overfitting to one model/backend.

## Compaction vs Refinement

- **semantic compaction**: distill for throughput while preserving decision-critical signal.
- **refinement**: improve structure/clarity/retrievability of derived artifacts.

Both are derivation workflows, not history mutation workflows.

## Guardrails

- Keep provenance for every derived artifact.
- Prefer reversible derivations.
- Make frontier-time failures explicit when packet quality is insufficient.
- Treat hidden/implicit rewrites as bugs.

## Open Questions

- Which refinement operations are safe enough for silent auto-apply?
- What quality signals should gate packet assembly (coverage, conflict, staleness)?
- How to compare candidate lenses and choose one under token/latency budgets?
- How to expose this in Vim/CLI without adding operator friction?
