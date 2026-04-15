## Goal

Improve `daemon.py` testability and coverage around async watch timing, lane selection, and fallback transitions.

## Why Now

`daemon.py` is large and under-covered (~61%) while carrying most runtime coordination risk.

## Scope

- add focused tests for async watch lifecycle and completion transitions
- test lane-selection/fallback boundaries (default/warm/cold/synchronous where applicable)
- test cancellation and timeout edge behavior at daemon orchestration layer
- extract minimal helper seams to reduce closure-heavy logic where tests currently struggle

## Intended Behavior

- daemon orchestration paths are less opaque and easier to reason about
- fallback behavior is validated by explicit tests instead of manual probing

## Constraints

- no semantic changes to step contracts or RPC output shape
- avoid large architectural rewrites in this slice

## Done When

- targeted daemon orchestration tests are merged and stable
- coverage improves in key daemon coordination paths
- at least one closure-heavy/test-hostile code seam is simplified

## Outcome

- added focused daemon orchestration tests for async wait/cancel terminal transitions, managed-backend lifecycle edge cases, payload-validation boundaries, safe-op error mapping, request workdir switching, and CLI command dispatch paths
- improved coverage in `daemon.py` from ~61% to `73%` without changing daemon RPC/step semantics
- verification: `uv run pytest -q` passing with strengthened overall coverage
