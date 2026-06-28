Filed as: 260628-task-template-intent-line
FKA:
AKA: template intent line; task lead-paragraph slot; template board-label slot
Legacy index:

keywords: docs, tooling, template, workboard, follow-on

# Task Template Intent Line

Give the task template a one-line intent slot under the title so authored tasks
carry a non-redundant workboard label by construction.

## Current Reality

`tasks/task-template.md` goes straight from `# Title` to `## Current Reality`,
so there is no home for a one-line statement of intent. The board label parser
now prefers, in order, an explicit `## Goal`/`## Objective`, then the intro
paragraph under the title, then the clean title (see
`260628-workboard-objective-parser-shape-tolerance`). With no intro slot, a
template-authored task falls back to the title, which is just the slug re-spaced
and redundant with the task id already shown.

The bare template also lags the working template shape (annotated guidance,
consolidated `Known Facts / Assumptions / Unknowns` and `Models / Forecasts /
Risks` sections).

## Desired Reality

The template carries a one-line intent slot directly under the title, with brief
guidance, so a filled-in task surfaces an informative board label for free. The
template otherwise matches the current working shape (annotated, consolidated).

## Transformations

- add an intent line under `# Title` in `tasks/task-template.md`
- align section guidance/consolidation with the working template shape
- preserve the continuity frontmatter block

## Evidence

- the template renders an intent line that the workboard parser would surface as
  the label (lead-paragraph path), not the slug-title
- the pipeline scaffold in `src/toas/tasks.py` is intentionally left alone (it
  only has the title at capture time)

## Decisions

- Keep this to the manual template; do not change `create_standalone_task`,
  which cannot fill an intent line meaningfully at capture time.

## Next Actions

- update `tasks/task-template.md` and confirm via the workboard parser behavior.
