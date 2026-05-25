# 566: `search_block` Near-Match Time Budget and Heuristic Fallback

## Why

`search_block` near-match behavior on match failure appears to perform exhaustive/brute-force scanning that can become too expensive for interactive usage.

## Goal

Bound near-match fallback to a strict interactive time budget (target: 1–2 seconds wall-clock) and replace exhaustive exploration with higher-signal heuristics.

## Scope

- Add a hard time budget for near-match search fallback.
- Ensure fallback exits deterministically when budget is exhausted.
- Prefer heuristic candidate ordering/pruning over exhaustive brute-force search.
- Return best-so-far (or explicit bounded failure) when budget expires.
- Add tests covering timeout enforcement and non-exhaustive behavior.

## Non-Goals

- Perfect recovery for every mismatch case.
- Unbounded exhaustive search for maximum recall.
