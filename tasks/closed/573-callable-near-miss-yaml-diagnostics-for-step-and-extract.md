# 573: Callable Near-Miss YAML Diagnostics For Step And Extract

## Goal

Surface explicit, actionable errors when assistant content looks like callable/tool intent but YAML parsing fails, instead of silently falling through to blank frontier behavior.

## Why

During task `661` work, assistant frontier blocks that looked valid at a glance could fail extraction due to YAML parse issues (notably long inline `argv` lists). This led to low-signal behavior (`## TOAS:USER` blank turn) that obscured the actual failure mode.

## Scope

- Improve `/extract` skipped-block diagnostics for callable-looking YAML parse failures.
- Improve normal `step` frontier handling so callable-looking assistant parse near-misses produce explicit user-visible errors.
- Keep extraction strict: no auto-execution or silent coercion of invalid YAML.

## Changes Implemented

1. `/extract` near-miss hinting
- File: `src/toas/runtime/frontier_resolution.py`
- For callable-looking YAML parse failures, append an actionable hint when inline `argv` list shape is detected:
  - `hint: use block list style for argv, one item per line`

2. Normal step near-miss error surfacing
- File: `src/toas/runtime/step_runtime.py`
- Added assistant-frontier near-miss detection for callable-looking content with parse-error-only skipped candidates.
- When detected and no callable intent is extracted, emit explicit result content:
  - `[ERROR] callable-looking assistant block is not valid YAML for extraction`
  - followed by first parse-error detail line.
- This replaces silent blank-turn fallback for this failure shape.

## Non-Goals

- Relaxing parser strictness to auto-accept malformed YAML.
- Executing tool calls from invalid callable blocks.

## Done When

- `/extract` provides actionable parse-error hints for callable-looking YAML near-misses.
- Normal `step` emits explicit errors for callable-looking assistant parse near-misses instead of blank user turns.
- Strict execution boundary remains intact.

## Progress Log

- 2026-05-30: Added `/extract` parse-error hinting for inline `argv` near-miss shape in callable-looking YAML blocks.
- 2026-05-30: Added normal `step` assistant-frontier near-miss diagnostics for callable-looking YAML parse failures, preserving strict no-auto-exec behavior.
