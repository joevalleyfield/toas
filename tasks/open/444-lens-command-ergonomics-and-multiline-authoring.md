## Goal

Improve `/lens` authoring ergonomics so operators can reliably create/edit artifacts with multiline distillations and explicit fields.

## Why Now

The durable `/lens` lane exists, but current positional input is brittle for real artifact authoring and easy to misformat.

## Scope

- add flag-based `/lens set` form (for example `--title`, `--source`, `--use-when`)
- preserve compatibility with current positional `/lens set` form
- support multiline distillation authoring without shell-escaping pain
- keep parser behavior deterministic with clear usage errors
- update `/help` guidance with concrete examples

## Intended Behavior

- operators can author/update lens artifacts without quoting/ordering traps
- multiline distillation entry is practical in the single text-editor surface
- invalid forms fail with actionable usage guidance

## Constraints

- keep append-only history model intact
- no hidden mutation outside explicit `lens_artifact` records
- avoid ambiguous parser precedence across legacy/new forms

## Done When

- flag-based `/lens set` parsing is implemented and test-covered
- multiline distillation input path is implemented and test-covered
- legacy positional form remains supported or explicitly migration-gated
- help/docs include at least two concrete authoring examples
