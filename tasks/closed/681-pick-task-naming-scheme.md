# Pick task naming scheme

Filed as: 651-pick-task-naming-scheme
FKA: 651-pick-task-naming-scheme
AKA: task handles; task ids; numerical tasks; git-friendly task names; task filename schema
Legacy index: 651, 681

keywords: docs, governance, historical, usability, naming, tasks

## Objective

Pick and document a task filename and continuity-field convention that avoids false numerical-id authority while preserving search and archaeology value.

## Current Reality

Tasks currently use numerical identifiers, including 3-digit numerical ids in many cases.

Those numbers have become misleading now that multiple workers can create or manipulate tasks concurrently. They look like they might imply global uniqueness, ordering, allocation, or parentage, but they do not reliably provide those properties in the current workflow.

The existing numerical identifiers may still have locator value. They are useful for search, continuity, and migration, but they should no longer be treated as the primary identity scheme.

## Desired Reality

Task filenames should use a small, git-friendly, human-readable handle that can be created without coordination between workers.

The scheme should be easy to mint manually or by an agent, easy to search with `rg`, stable enough for ordinary references, and honest about what it does and does not guarantee.

The naming convention should support task renames and semantic drift without losing continuity.

The result should be simple enough to document in `tasks/README.md` later.

## Gap Analysis

The old numerical scheme provides apparent structure but weak actual guarantees.

A purely random id would provide stronger collision resistance and stable machine identity, but it adds visual noise and solves a problem that does not appear central.

A slug-only scheme is very readable, but slugs can collide semantically, drift over time, or require awkward numbering such as `test-coverage-cleanup-pass-4`.

A date-based slug gives useful chronology, low friction, and enough practical disambiguation for the current workflow. If the same idea appears on the same day with the same slug, that is likely a meaningful overlap requiring merge, split, or refinement rather than just a naming failure.

## Known Facts

Multiple workers may create tasks concurrently.

Check-on-create cannot be assumed.

Collisions are not a major practical problem.

The task file path already gives task context, so a prefix like `tk_` is not necessary in `tasks/open/*.md` or `tasks/closed/*.md`.

`rg` search continuity matters.

Git and jj archaeology matter.

The task name may drift as the work becomes better understood.

Old task names should remain discoverable.

The final convention can be written into `tasks/README.md` by a coding/documentation agent later.

## Assumptions

A same-day same-slug collision is rare enough to tolerate.

When same-day same-slug collisions happen, they are useful signals that two tasks may need to be merged, split, or disambiguated.

Filename renames are acceptable.

Task identity does not need to be cryptographic.

The current filename can be treated as the current handle.

The original filename/handle can be preserved as ordinary text inside the task.

## Unknowns

Whether future automation will need a stricter machine id.

Whether task references will become dense enough that rename-stable opaque ids become more valuable.

Whether cross-repo or cross-worktree task synchronization will increase collision pressure.

Whether task handles will later become graph node ids or remain mostly human-facing file handles.

## Investigations

Considered using the jj change-id of the commit that adds the task.

Rejected as the primary task id because it couples task identity to VCS history. jj change-ids are attractive because they are stable across jj rewrites, but they are still VCS-origin metadata rather than task identity. Git-only emulation would require inventing a similar id anyway.

Considered random short ids such as:

```text
zrbftqzi-test-coverage-cleanup-pass-4.md
```

Useful, especially with a `k-z` alphabet to avoid SHA/date/number confusion, but the random part solves mostly soft problems: uncoordinated exact collision, non-semantic handles, and rename-stable references.

Considered slug-only:

```text
test-coverage-cleanup.md
```

Rejected as the default because slugs are semantic and semantics drift. Similar ideas can produce similar names, and reuse tends to force ad hoc numbering.

Considered month-only date slugs:

```text
2606-test-coverage-cleanup.md
```

Attractive and compact, but the day has enough utility to justify adding it back.

Settled on day-date slug handles:

```text
260606-test-coverage-cleanup.md
```

## Models

A task handle is not a perfect global id.

A task handle is a compact, git-friendly locator for a durable task artifact.

The task file itself is the source of continuity. The filename is the current handle. The body records prior handles and aliases.

Identity continuity should be ordinary text, not hidden state.

```markdown
Filed as: 260606-test-coverage-cleanup
FKA: 260606-coverage-cleanup
AKA: coverage markers; coverage ratchet; test cleanup
Legacy index: 669-12-4
```

This gives `rg` everything it needs without special flags or a strict parser.

## Forecasts

The date-plus-slug convention should remain comfortable for a while because it is easy to mint, easy to read, and easy to repair.

Most tasks will not need random suffixes.

The rare collision or near-collision will likely expose real overlap in work definition.

Semantic drift will be handled by renaming the file and preserving the original handle inside the task.

Old numerical references can be retained as `Legacy index:` fields until they naturally lose value.

## Risks

A handle may become stale after the task intent changes.

Mitigation: preserve the birth handle with `Filed as:` and previous handles with `FKA:`.

A same-day same-slug collision may occur.

Mitigation: disambiguate with a sharper slug, merge the tasks, or split the intent.

A future graph or automation system may need opaque stable ids.

Mitigation: add a stricter id later only if the need becomes real. Do not pay that tax now.

Agents may accidentally treat legacy numerical triples as authoritative.

Mitigation: call them `Legacy index:` and avoid making them the leading filename identity.

## Transformations

Adopt filenames of the form:

```text
tasks/open/YYMMDD-short-intent.md
tasks/closed/YYMMDD-short-intent.md
```

Examples:

```text
tasks/open/260606-task-naming-scheme.md
tasks/open/260606-test-coverage-cleanup.md
tasks/open/260606-projection-lane-docs.md
```

Use the current filename stem as the current handle.

Include continuity fields near the top of the task:

```markdown
Filed as: 260606-task-naming-scheme
FKA:
AKA: task handles; task ids; git-friendly task names
Legacy index:
```

Keep numerical triples only as legacy locator metadata, not as identity.

Use random suffixes only as an escape hatch for exploratory or intentionally hard-to-name work, not as the default.

## Evidence

The chosen scheme is directly responsive to the problems observed:

* multiple workers can create tasks without coordination;
* no check-on-create is required;
* exact collisions are rare and meaningful enough to handle manually;
* the date gives useful chronology and git/jj archaeology;
* the slug keeps the task human-readable;
* `Filed as:` preserves the original name through semantic drift;
* `FKA:` and `AKA:` preserve search continuity;
* `Legacy index:` lets old numerical references remain useful without pretending they are unique.

The scheme avoids a false uniqueness affordance while preserving the useful parts of the old system.

## Decisions

Use `YYMMDD-slug.md` as the default task filename scheme.

Treat the current filename stem as the current task handle.

Add `Filed as:` to every task to record the original handle.

Use `FKA:` for previous handles after renames.

Use `AKA:` for fuzzy search aliases and alternate phrasings.

Use `Legacy index:` for existing numerical task ids or triples.

Do not use `tk_` by default.

Do not use random ids by default.

Allow random shards only as an escape hatch when a task is intentionally exploratory, duplicated, or difficult to name.

## Open Fronts

Document the convention in `tasks/README.md`.

Decide whether to migrate existing task filenames immediately or only apply the scheme going forward.

Decide whether closed tasks should be renamed into the new scheme or left with legacy names plus metadata.

Decide whether task creation tooling should auto-fill `Filed as:` and date prefix.

Decide whether `AKA:` should remain freeform prose or use a light delimiter convention such as semicolons.

## Next Actions

Write the naming convention into `tasks/README.md`.

Update the task template to include:

```markdown
Filed as:
FKA:
AKA:
Legacy index:
```

Use the new scheme for the next newly-created task.

When touching old numerical tasks, add `Legacy index:` and optionally rename only if the task is already being edited.

Avoid bulk migration unless it clearly reduces friction.

## Status

**Closed.** Naming convention documented in `tasks/README.md`. Task template created at `tasks/task-template.md`. This task file updated with continuity fields as a working example.
