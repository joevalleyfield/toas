## Goal

Deliver a first-pass docs reshape that compresses roadmap history and introduces a capability-oriented user doc.

## Why Now

The target docs shape is agreed, and a concrete first pass will make future refinement incremental rather than speculative.

## Scope

- rewrite `docs/roadmap.md` into a compact structure:
  - Now
  - Next
  - Open arcs
  - Recently closed
  - compressed historical capability-story bullets
- create `docs/capabilities.md` focused on current operator-visible capability shape
- add light cross-links between roadmap, vision, and capability docs

## Intended Behavior

- operators can understand near-term direction from roadmap in one screenful
- operators can find current capability shape without digging through task history
- older implementation arcs are summarized, not itemized

## Constraints

- use lists and short narratives; avoid table-heavy presentation
- keep recently closed items only where they materially inform current planning
- keep doc language aligned with durable record model and runtime mode semantics

## Done When

- `docs/roadmap.md` reflects compressed forward-looking shape
- `docs/capabilities.md` exists with a practical first pass
- links between core docs are in place and non-circular
