# Tasks

This directory holds active, closed, and recurring task files.

## Filename Naming Scheme

Use `YYMMDD-short-intent.md` for all new task files.

```text
tasks/open/260606-task-naming-scheme.md
tasks/closed/260606-test-coverage-cleanup.md
```

Rules:

- `YYMMDD` = year (2-digit) + month + day of creation. Easy to mint, gives chronology.
- `short-intent` = kebab-case slug describing the task. Keep it under ~40 chars.
- Same-day same-slug collision is rare; when it happens, disambiguate the slug or merge/split the tasks.
- Do not use `tk_` prefix. Do not use random ids by default.
- Random suffixes (e.g. `zrbftqzi-...`) are an escape hatch for intentionally exploratory or hard-to-name work only.

## Continuity Fields

Include these near the top of every task file:

```markdown
Filed as: 260606-task-naming-scheme
FKA:
AKA: task handles; task ids
Legacy index:
```

- `Filed as:` records the original handle at creation. Never change this line.
- `FKA:` lists previous handles after renames, separated by semicolons.
- `AKA:` lists search-friendly aliases and alternate phrasings, separated by semicolons.
- `Legacy index:` holds old numerical task ids (e.g. `681`) for backward search continuity.

Renames are acceptable when task intent drifts. Preserve the original name via `Filed as:` and prior names via `FKA:`.

## Relationship Fields

Tasks may be linear when the work is genuinely independent, but active planning
should preserve tree or graph shape when the work has structure.

Use lightweight relationship lines in prose near the top of the file:

```markdown
Parent: `260614-architecture-follow-through-coordination`
Blocks: `260614-example-dependent-task`
Blocked by: `260614-example-prerequisite`
Related: `260614-example-adjacent-task`; `400`
```

Guidelines:

- `Parent:` means the task is a child of an umbrella or coordination task.
- `Blocks:` and `Blocked by:` mean order matters.
- `Related:` means adjacency matters, but order does not.
- Prefer explicit manual relationships for active architecture or coordination
  work; do not wait for automation to infer them.
- Avoid forcing a tree when the work is really a graph. A task can have one
  parent for navigation while still naming multiple related or blocking tasks.
- Keep relationship fields light for inception tasks; name only the links that
  would help a future reader choose or sequence work.

## Migration

- Apply the new scheme to all newly created tasks.
- When touching an existing numerical task, add `Legacy index:` and optionally rename if the task is already being edited.
- Do not bulk-migrate existing tasks unless it clearly reduces friction.

## Keyword Convention

Use a single `keywords:` line near the top of each task file.

Format:

```md
keywords: runtime, implementation, active, compatibility, async, transport, watch, cancel
```

Rules:

- keep values flat and comma-separated
- use lowercase tokens
- make the value set disjoint where practical
- include one lifecycle token so open/inception/parked/historical state is
  grep-friendly
- prefer stable topic keywords over prose

## Controlled Vocabulary

Use these values for the structured portion of `keywords:`

- `domain`: `runtime`, `projection`, `config`, `transport`, `tooling`, `surface`, `docs`, `exploration`
- `mode`: `implementation`, `hardening`, `decomp`, `migration`, `governance`, `investigation`, `explore`
- `lifecycle`: `active`, `inception`, `parked`, `blocked`, `follow-on`, `historical`
- `objective`: `correctness`, `maintainability`, `contract`, `usability`, `performance`, `compatibility`, `research`

## Open Themes

These are freeform theme keywords that can be used as needed:

- `async`
- `transport`
- `watch`
- `cancel`
- `stream`
- `transcript`
- `frontier`
- `projection`
- `graph`
- `shell`
- `vim`
- `config`
- `parity`
- `coverage`
- `decomposition`
- `logging`
- `search`
- `patch`
- `workboard`
- `naming`
- `docs`
- `ipc`
- `provenance`
- `authority`
- `boundaries`
- `defaults`
- `policy`

## Lifecycle Notes

- `inception` means a task captures a known pressure or intended future work
  area before it is ready to declare an operating status, owner, sequence, or
  implementation plan.
- Inception tasks should be light. They should explain why the pressure exists
  and what evidence would let the task leave inception.
- Do not pair `inception` with `active` or `parked` unless the task has been
  explicitly promoted or deferred after a real triage pass.

## Requirements Parent Pattern

Some work areas benefit from a named split between design truth and
implementation slices:

```text
requirements parent / gap-closing follow-ons
```

Use this pattern when one task is primarily defining:

- a user-facing model
- a contract or invariant
- an audit/mismatch matrix
- a design decision that multiple smaller changes may implement later

Under this pattern:

- the parent task owns the requirements, object model, mismatch analysis, and
  prioritization logic
- follow-on tasks own bounded code/docs/tests that close one concrete gap
- the parent stays the design reference instead of becoming the implementation
  bucket

Guidance:

- keep work in the parent task while the main output is still "what should this
  area mean?" or "what are the gaps?"
- open a follow-on when one seam has a clear owner, acceptance shape, and test
  story
- prefer multiple focused follow-ons over one broad "implement the design"
  child
- update the parent task with links/disposition notes as follow-ons are opened
  so it remains the dispatch point

Relationship guidance:

- follow-ons should usually declare `Parent:` back to the requirements parent
- the parent may list important implementation children under `Related:` or
  prose notes if they are not strictly blocking one another

Live example:

- `260627-history-surface-user-intent-alignment` acts as a requirements parent
  for history-surface semantics, while implementation slices should land as
  narrower follow-ons once the per-surface gaps are concrete.

## Notes

- Keep `tasks/WORKBOARD.md` as the operational board.
- Use this file as the canonical vocabulary reference for task-file `keywords:`.
