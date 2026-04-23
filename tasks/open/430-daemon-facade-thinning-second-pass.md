## Goal

Continue thinning `src/toas/daemon/__init__.py` by moving remaining lifecycle and compatibility wrapper clusters into focused daemon package modules.

## Why Now

After first-pass extraction, `code_survey` still reports `daemon/__init__.py` at 479 lines. The transition facade remains larger than needed and still hides mutable lifecycle logic.

## Scope

- identify remaining non-trivial logic in `daemon/__init__.py` and move into focused modules
- retain `toas.daemon` import/run compatibility during transition
- reduce wrapper complexity and centralize dependency wiring patterns
- add focused tests for extracted modules and compatibility seams

## Intended Behavior

- daemon package facade is predominantly exports/wiring
- operational logic lives in dedicated modules with direct tests

## Constraints

- preserve daemon CLI/runtime behavior and RPC/local parity
- keep compatibility aliases until downstream call sites are migrated

## Done When

- `daemon/__init__.py` is materially smaller and mostly facade code
- moved logic is covered by focused module tests
- full suite passes
