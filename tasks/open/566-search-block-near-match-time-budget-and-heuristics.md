# 566: `search_block` Near-Match Time Budget and Heuristic Fallback
keywords: tooling, hardening, parked, performance, search, heuristics, budget, fallback

## Why

`search_block` near-match behavior on match failure appears to perform brute-force fallback work that can become too expensive for interactive usage.

## Goal

Keep near-match fallback cheap enough for interactive usage by construction, with only a short hard deadline as a safety fuse, and replace exhaustive exploration with higher-signal heuristics.

## Scope

- Add a short hard time budget for near-match search fallback.
- Ensure fallback exits deterministically when budget is exhausted.
- Prefer heuristic candidate ordering/pruning over exhaustive brute-force search.
- Return best-so-far (or explicit bounded failure) when budget expires.
- Add tests covering timeout enforcement and non-exhaustive behavior.

## Non-Goals

- Perfect recovery for every mismatch case.
- Unbounded exhaustive search for maximum recall.

## Progress

- 2026-06-21: in progress. Near-match mismatch diagnostics are being tightened to use a short safety-fuse budget plus aggressively pruned heuristic candidate ordering so failure reporting stays cheap on large files.
- 2026-06-21: aligned the edge-case test coverage with the richer `best_equal_length_region()` result shape so the heuristic metadata contract is asserted consistently across fallback paths.
