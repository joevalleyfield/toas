Filed as: 260627-history-affordances-semantic-restaging
FKA:
AKA: history affordances white paper; semantic restaging; refresh prior exploration; replay naming critique
Legacy index:

keywords: docs, exploration, inception, research, transcript, projection, history, naming

Parent: `260614-architecture-follow-through-coordination`
Related: `260626-transcript-parallelism-design-pressures`; `260524-exploratory-work-representation-model`

# History Affordances And Semantic Restaging

## Current Reality

TOAS already has many mechanical operations over durable history: projection,
rebuild, branching through transcript divergence, historical callable
selection, and queue-shaped design pressure around multiple projection surfaces.

What it does not yet have is a clear adopted product story for how
intelligence should make interesting use of that history. Existing language
such as "replay" is carrying too many meanings at once:

- literal re-execution of prior callable intent
- test or harness fixture playback
- vague product-level promise about history usefulness

That overload makes it difficult to tell which history operations are genuine
operator jobs and which are substrate mechanics.

## Desired Reality

TOAS should eventually expose history not only as auditability but as reusable
operator material.

The likely shape is:

- durable mechanical primitives remain explicit and append-only
- intelligence groups, selects, stages, compares, and summarizes prior work
- operator-facing language names real jobs such as restaging, refreshing,
  re-running, or continuing from prior work rather than overloading "replay"

## Questions

- Which prior work units are useful enough to surface as reusable material:
  single calls, ranges, consequence sets, exploratory bundles, or higher-level
  seeds?
- Should TOAS first support staging historical intent into a new frontier and
  only later add one-shot execution affordances?
- What minimal durable distinctions are needed between prior intent, prior
  result, stale observation, and adopted conclusion?
- How much of the utility will come from prompt/capability advertisement versus
  new explicit history-facing commands or record types?

## Exit Evidence

This task can leave inception when adjacent parallelism work or real operator
usage produces at least one concrete affordance worth specifying.

Useful evidence would include:

- a recurring pattern where prior exploratory steps need to be refreshed after
  world state changes
- a crisp distinction between "restage intent" and "re-run now"
- prompt or capability experiments showing that one framing reliably causes
  useful historical reuse
- a bounded design proposal for one history-facing affordance with explicit
  durable semantics

## Notes

This task is intentionally exploratory prose, not adopted product direction.
Its immediate value is to capture vocabulary, use-case pressure, and design
questions until adjacent parallelism work makes a concrete affordance worth
building.
