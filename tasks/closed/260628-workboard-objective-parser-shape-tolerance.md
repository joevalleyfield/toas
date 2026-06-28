Filed as: 260628-workboard-objective-parser-shape-tolerance
FKA:
AKA: workboard label parser tolerance; sync_workboard objective extraction; arc map title rendering
Legacy index:

keywords: tooling, workboard, parser, sync, hardening, follow-on

Related: `260619-workboard-sync-script-parser-and-identity-fix`; `260627-workboard-relationship-tree-builder`

# Workboard Objective Parser Shape Tolerance

## Current Reality

`tasks/scripts/sync_workboard.py` renders each task's board label from a parsed
`objective`. The extraction is brittle across task shapes:

- `_extract_section` matches headings with `re.search(rf"## {heading}")`, so the
  intent `Why` matches `## Why It Matters` and `## Why Now` and pulls that
  section's prose as the "objective" (e.g. `260628-acceptance-live-prompt-realism`
  rendered a "This is consistent with TOAS's transcript-authoritative design..."
  sentence; `260614-vim-test-cost-audit` rendered its `## Why Now` body).
- the fallback grabs the H1 line literally including the `# ` prefix (the skip
  only compares against `# {stem}`, never the human title), so most tasks render
  as `# Title` rather than `Title`.

Net: inconsistent labels (some `# Title`, some accidental section prose) for no
reason other than which sections a task happens to use.

## Desired Reality

The parser should be tolerant of alternate task shapes so we do not have to
tighten task files to a single template:

- default the label to the clean human title (the first `# ` H1 whose text is
  not the filename stem, with the `# ` stripped)
- only override with an explicit `## Objective` / `## Goal` section when an
  author opts into a richer one-line summary
- match section headings exactly (full heading text, case-insensitive) so
  `Why` never matches `Why It Matters` / `Why Now`

## Refinement (reopened 260628)

First pass made the label default to the clean human title. But the title is
just the slug re-spaced, so for tasks without a `## Goal`/`## Objective` it is
redundant with the task id already shown. The disciplined task-pipeline tasks
(legacy `558`/`560`, e.g. `260524-attention-focused-workboard-layout`) carry a
rich `## Goal`, and `tasks.py` `create_standalone_task` scaffolds that section —
that is why those render extra information.

To recover extra information without forcing every task to a `## Goal` template,
add a lead-paragraph fallback: the intro prose between the `# H1` and the first
`##` section. New priority: `## Objective`/`## Goal` -> lead paragraph -> clean
title -> stem. E.g. `260614-vim-test-cost-audit` then renders its real intro
objective instead of the slug-title.

## Exit Evidence

- [x] `parse_task` returns the clean human title for tasks with `## Why It
  Matters` / `## Why Now` / `## Current Reality` shapes (no accidental prose, no
  leading `# `)
- [x] an explicit `## Objective` / `## Goal` section still wins when present
  (`_extract_section` now matches headings exactly, case-insensitive)
- [x] a targeted test covers these shapes
  (`test_parse_task_objective_tolerates_alternate_shapes`)
- [x] re-running the workboard sync yields consistent labels across the board
  (no stray `# ` prefixes)
- [x] a task with an intro paragraph (and no `## Goal`) renders that paragraph,
  not the slug-redundant title; truly bare tasks still render the clean title
  (e.g. `260614-vim-test-cost-audit` now shows its intro objective;
  `260628-acceptance-live-prompt-realism` keeps its title)
- [x] test covers the lead-paragraph shape
  (`test_parse_task_objective_tolerates_alternate_shapes`)
