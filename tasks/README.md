# Tasks

This directory holds active, closed, and recurring task files.

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
