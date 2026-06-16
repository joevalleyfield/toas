Filed as: 260615-legacy-surface-retirement-inventory
FKA:
AKA: legacy retirement; compatibility debt inventory; transitional surface cleanup
Legacy index:

keywords: transport, investigation, inception, architecture, legacy, surface, retirement, adapter

# Legacy Surface Retirement Inventory

## Current Reality

TOAS still has surfaces retained for old callers, old import paths, old daemon
or RPC shapes, and transition-period response fields. Some are real legacy
debt. Some are edge adapters with legitimate interface constraints. The word
`compatibility` has often blurred those cases.

Parent: `260614-architecture-follow-through-coordination`

Related: `260614-legacy-and-fidelity-adapter-precedence`

## Desired Reality

Legacy surfaces should have a retirement story. For each legacy surface, TOAS
should know:

- who still relies on it
- what newer path replaces it
- what evidence would permit removal
- whether removal is safe now, should wait for a caller migration, or should be
  parked

Fidelity-lowering adapters should not be swept into this inventory as legacy
unless they are also transitional.

## Alignment Target

This task should inventory existing legacy transition surfaces. It should not
remove them directly and should not create new compatibility paths.

The first useful slice is a table of live legacy surfaces and their consumers,
with retirement evidence or a reason to keep them.

## Known Facts

- `docs/runtime-ownership.md` now distinguishes legacy surfaces from
  fidelity-lowering edge views.
- Public facades such as `tools.py`, `cli.py`, and selected daemon/package
  exports still preserve old contracts.
- Some legacy response fields remain while envelope-aware consumers exist.

## Unknowns

- Which legacy surfaces still have real current consumers.
- Which legacy fields are only kept by habit or historical caution.
- Which tests prove a legacy path still matters versus only pin old shape.
- Whether any removal should be bundled with naming cleanup under
  `260614-retire-local-suffix-naming-inversion`.

## Evidence

Ready to leave inception when:

- legacy surfaces are inventoried separately from fidelity-lowering adapters
- current consumers or tests are named for each retained surface
- retirement candidates are split into focused follow-ups only when bounded
- no entry uses `compatibility` as the justification by itself
