# 570: Retire Stateful Branch Selection And Make Step Transcript-Authoritative

## Why

Default `step` behavior still depends on durable branch-selection control state (`head`/`jump`/anchor-adjacent flows), which can diverge from the user-visible transcript frontier and violate least-surprise during iterative edit/step loops.

## Goal

Make default `step` transcript-authoritative:
- execution selection comes from transcript frontier
- non-frontier historical callable selection is explicit and transactional (`/replay`)
- long-lived operational state is minimized (config remains durable; branch selection does not linger as hidden execution truth)

## Scope

- define policy: default `step` ignores persistent branch-selection state unless explicitly requested in-command
- convert branch/history selection commands to transactional semantics (select + act in one operation)
- preserve explicit `/replay` historical selection behavior
- add migration/compat notes for existing artifacts and user flows
- add regression tests that prove no persistent hidden selection bleed into later steps

## Non-Goals

- changing durable event-history model
- removing explicit replay functionality
- redesigning transcript format

## Initial Validation

- repeated truncate/restore + step loops remain frontier-driven
- non-frontier callable content never executes in normal `step`
- explicit replay and history-preview workflows remain available and deterministic
