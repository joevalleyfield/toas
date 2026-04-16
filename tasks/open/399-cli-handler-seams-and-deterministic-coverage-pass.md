## Goal

Take the first `cli.py` slice under `396`: improve command-handler seam clarity and cover deterministic branch paths without changing CLI contracts.

## Why Now

`cli.py` has broad branching (`87%`) and many low-signal uncovered lines; isolating a handler cluster improves maintainability and test ergonomics.

## Scope

- select one command/handler cluster with high branch density
- add focused tests for argument-validation and output-contract branches
- extract small pure helpers where it reduces coupling/duplication
- keep command surface and user-visible behavior stable

## Intended Behavior

- clearer handler boundaries and less incidental coupling
- improved confidence in edge-case CLI flows
- measurable `cli.py` coverage increase in touched paths

## Constraints

- no global CLI rewrite
- maintain existing command names, flags, and stdout contracts

## Done When

- selected handler cluster has additional deterministic coverage
- any needed seam refactor lands with passing suite
- roadmap/task stitching reflects progress under `396`

