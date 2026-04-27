## Goal

Add write-time validation and diagnostics for durable lens artifacts so weak or invalid entries are rejected early.

## Why Now

`344` quality gates currently catch weak packets at generation time; adding validation at author-time prevents noisy feedback loops and reduces bad durable state.

## Scope

- validate `/lens set` payloads before writing `lens_artifact` records:
  - non-empty `title` and `distillation`
  - at least one `source_pointer`
  - source pointer existence in current message lineage
- add duplicate-title semantics diagnostics (replace vs conflict clarity)
- return precise, actionable error text with correction hints
- add regressions for pass/fail validation paths

## Intended Behavior

- invalid lens artifacts fail fast before durable write
- diagnostics point directly to the field(s) that need correction
- durable lens state remains cleaner and easier to trust

## Constraints

- preserve current replace-by-title semantics unless explicitly changed
- no destructive rewrites of existing durable history
- diagnostics should remain compact and deterministic

## Done When

- write-time validation is wired into `/lens set`
- source pointer existence checks are implemented and tested
- diagnostic coverage includes missing/invalid/ambiguous field cases

## Progress

- 2026-04-26: Landed write-time validation slice:
  - `/lens set` now validates `source_pointers` against known message IDs from current events/working lineage before emitting durable `lens_update` writes.
  - invalid source IDs now fail fast with compact diagnostics and a sample of known message IDs.
  - duplicate-title sets now emit explicit replacement diagnostics in result content (`replacing existing title`) while preserving replace-by-title semantics.
  - added regression coverage for pass/fail validation paths and replacement-note behavior.
