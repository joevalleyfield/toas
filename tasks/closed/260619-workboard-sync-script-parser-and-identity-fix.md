Filed as: 260619-workboard-sync-script-parser-and-identity-fix
FKA:
AKA: workboard sync script; sync parser bug; task identity fix; workboard generation
Legacy index:

keywords: tooling, implementation, historical, workboard, sync, parser, identity, naming

# Workboard Sync Script Parser and Identity Fix

Parent: `559`
Related: `681`; `260615-legacy-surface-retirement-inventory`; `260615-runtime-package-growth-boundary-audit`

## Current Reality

`tasks/scripts/sync_workboard.py` was misreading task metadata as task content
and collapsing distinct task handles into a shared numeric prefix.

## Desired Reality

The sync script should faithfully project open, inbox, and closed task files
into `tasks/WORKBOARD.md` without losing identity or substituting metadata for
task intent.

## Gap Analysis

- Generated workboard entries should preserve full task handles, not only the
  leading numeric prefix.
- Fallback summary extraction should ignore continuity fields and other task
  header metadata.
- The manual triage block should stay intentionally hand-curated, but it should
  no longer refer to closed tasks as active.

## Known Facts

- The board sync script is the source of the generated open and closed sections.
- `tasks/README.md` defines the current naming scheme and continuity fields.
- `tasks/WORKBOARD.md` is the operational board and should reflect current
  task files.

## Investigations

- Verified the sync script emits distinct board entries for similarly prefixed
  task stems.
- Verified metadata-only lines are skipped when falling back to the first
  content paragraph.
- Updated stale manual references in `tasks/WORKBOARD.md` and `docs/roadmap.md`.

## Models

```text
task files -> sync_workboard.py -> WORKBOARD.md
            -> preserve task stem identity
            -> ignore standard metadata in fallback summaries
```

## Transformations

- `sync_workboard.py` now skips standard header metadata when falling back to a
  task summary.
- `sync_workboard.py` now uses the full filename stem as task identity.

## Evidence

- generated board entries preserve distinct task handles
- fallback summaries no longer start with `Filed as:` / `FKA:` / similar
  metadata
- the workboard and roadmap references are aligned with the new task file

## Decisions

- Keep the manual workboard triage block hand-curated.
- Treat board synchronization bugs as tooling follow-up, not as task-model
  redesign.

## Open Fronts

- none; the follow-up is complete

## Next Actions

- none

## Done When

- generated board entries preserve distinct task handles
- fallback summaries no longer start with task-header metadata
- manual references in `tasks/WORKBOARD.md` and `docs/roadmap.md` are updated
- the sync script has been verified against representative task shapes

## Completion Summary

The workboard sync script now preserves full task stem identity and ignores
standard task-header metadata in fallback summaries. The generated workboard
sections were re-synced successfully, and stale planning references were
updated to point at this follow-up.
