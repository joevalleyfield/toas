# Surface Family And Design-Parent Discipline

Two adjacent design lessons are worth preserving from the recent
history-surface work.

## 1. Shared Implementation Should Follow Shared User Meaning

When several commands or surfaces are closely related, start by naming the
shared object from the user's point of view.

Only after that should implementation sharing become a design goal.

This prevents a common failure mode:

- implementation helpers appear shared
- shared helpers start suggesting a shared product story
- surface semantics drift toward internal convenience rather than operator
  meaning

The healthier order is:

1. define the shared object
2. define each projection of that object
3. define the shared default anchor for those projections
4. only then look for shared implementation seams

For the history-surface family, that means:

- `graph` is the selected history graph
- `history` is one root-to-head lineage through that graph
- `heads` is the leaf set of that graph

That wording is much safer than looser phrases like "flattened history" or
"current selected lineage" because those phrases can accidentally introduce the
wrong semantics and then leak outward into code, docs, and future planning.

## 2. Design Truth Tasks Should Not Quietly Become Execution Buckets

Some tasks are best used as design parents:

- they define the object model
- they define the user-facing contract
- they record mismatches between current reality and desired reality
- they provide the source of truth for later implementation slices

Those tasks become less useful when they quietly absorb concrete implementation
work.

The more durable pattern is:

- keep one parent task for requirements and contract truth
- open bounded follow-ons once one seam has a clear owner, acceptance shape,
  and test story
- keep the parent as the dispatch point instead of turning it into a generic
  implementation bucket

This is especially important for surface families. Once one command starts
changing, it becomes very easy to smuggle sibling work into the same task
without re-checking whether the family model is still coherent.

## Practical Guardrails

- Prefer words that are narrower and more literal than words that are broader
  and more impressive.
- If a default exists, make it derive from an already-authoritative truth
  source rather than inventing a new ambient authority.
- If learning one surface should help a user predict another, write that down
  explicitly as a family requirement.
- If a task is still answering "what should this mean?", it is probably still a
  design parent, not yet the implementation task.
