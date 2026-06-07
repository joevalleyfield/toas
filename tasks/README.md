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
- include one lifecycle token so open/parked/historical status is grep-friendly
- prefer stable topic keywords over prose

## Controlled Vocabulary

Use these values for the structured portion of `keywords:`

- `domain`: `runtime`, `projection`, `config`, `transport`, `tooling`, `surface`, `docs`, `exploration`
- `mode`: `implementation`, `hardening`, `decomp`, `migration`, `governance`, `investigation`, `explore`
- `lifecycle`: `active`, `parked`, `blocked`, `follow-on`, `historical`
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

## Notes

- Keep `tasks/WORKBOARD.md` as the operational board.
- Use this file as the canonical vocabulary reference for task-file `keywords:`.
