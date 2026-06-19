Filed as: 260619-daemon-package-facade-shrinkage
FKA:
AKA: daemon package facade; daemon __init__ cleanup; import surface shrinkage
Legacy index:

keywords: runtime, investigation, active, legacy, surface, daemon, facade, transport

# Daemon Package Facade Shrinkage

Parent: `260614-architecture-follow-through-coordination`
Related: `260615-legacy-surface-retirement-inventory`

## Current Reality

`src/toas/daemon/__init__.py` still acts as a package-level facade and legacy
import surface for daemon adapter modules.

## Desired Reality

The daemon package should be as thin as possible, with any remaining package
facade behavior justified by concrete import or compatibility needs.

## Gap Analysis

- We need current import consumers named explicitly.
- We need to distinguish transport-adapter behavior from actual facade
  necessity.
- We need a bounded shrinkage target rather than a vague "remove legacy"
  goal.

## Known Facts

- `src/toas/cli.py` lazily imports `daemon` through a package surface.
- `docs/runtime-ownership.md` treats `daemon/__init__.py` as a package facade
  around daemon adapter modules.
- Daemon transport and server behavior should remain adapter-oriented, not
  semantic ownership.

## Unknowns

- Which imports can be redirected to concrete daemon modules directly.
- Whether any public package-level symbols still need to be preserved.
- How much of the facade can be trimmed without breaking CLI or tests.

## Investigations

- Enumerate the package-level symbols and their consumers.
- Identify direct-module imports that could replace package facade access.
- Determine which parts, if any, must remain for compatibility.

## Evidence

Ready to leave active work when:

- the actual package-facade consumers are named
- any keep-vs-remove decisions are bounded by tests
- the daemon package no longer carries unrelated legacy convenience exports

