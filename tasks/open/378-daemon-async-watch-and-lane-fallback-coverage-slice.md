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
