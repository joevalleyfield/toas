## Goal

Make lineage head selection and inspection explicit in the operator surface.

## Scope

- Add graph helpers for enumerating reachable heads and their recent lineage
- Add CLI commands for listing heads and selecting a working head
- Make the active head visible enough that branch-aware work is legible

## Behavior

- The operator can show known message-event heads
- A user can choose a head without mutating prior history
- Head selection is stored durably as a control record rather than hidden process state
- Later projection commands can target the selected head by default

## Rules

- Head selection is distinct from bind index selection
- Selecting a head does not rewrite transcript content
- Head inspection must operate in message-event space
- Control records for head selection do not perturb message-event numbering

## Non-Goals

- No interactive TUI
- No merge or conflict resolution workflow

## Done When

- There is a durable way to inspect current heads
- There is a durable way to select a current working head
- Projection helpers can consume that selected head without ad hoc CLI state
