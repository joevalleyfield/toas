# 342: Recurring surface audit for help/command/tool interfaces

## Summary
Establish a recurring maintenance task to review TOAS user-facing help text, command surface behavior, and tool surface advertisement/shape, then spawn targeted remediation tasks when drift or ambiguity is found.

## Problem
Surface semantics evolve quickly (new commands, flags, modes, tool aliases, policy changes). Help/docs/tool-advertisement can drift from actual behavior, creating operator friction and model confusion.

## Goals
- Define a periodic audit cadence.
- Standardize what gets reviewed and how findings are recorded.
- Require remediation tasks for any actionable drift.

## Recurrence
- Cadence: every 2 weeks (or at least once per milestone).
- Triggered additionally after major surface changes (CLI/rpc/tool schema/prompt protocol updates).

## Audit Scope
- `toas help` usage text and command docs alignment.
- `README.md` command surface sections and examples.
- Prompt/tool advertisement language (especially operation/arguments aliases and multi-op guidance).
- Runtime error messaging clarity for blocked/disallowed operations.
- Vim/daemon interaction notes where they impact command behavior expectations.

## Procedure
1. Run surface walkthrough (`toas help`, `/help`, key command paths).
2. Compare behavior vs docs/prompt assets/tool hints.
3. Record findings with concrete file/line references and observed behavior.
4. For each actionable finding, open a task in `tasks/open/` with clear acceptance criteria.
5. Close the audit iteration only after findings are either:
   - converted into remediation tasks, or
   - explicitly marked as intentional/no-op with rationale.

## Acceptance Criteria
- A documented recurring audit process exists in tasks.
- Audit outputs consistently spawn remediation tasks when needed.
- Drift does not accumulate silently across help/command/tool surfaces.
