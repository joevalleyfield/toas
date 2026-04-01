## Goal

Make history and branch state inspectable without reading raw event logs directly.

## Scope

- Add CLI commands for readable event inspection
- Add CLI commands for lineage summaries and branch state
- Make selected head, bind state, and recent records legible

## Behavior

- Users can inspect history without manually parsing JSONL
- Branch and control state are visible in one operator-oriented view
- Inspection commands remain read-only

## Rules

- Inspection output should prioritize message-event space while still showing relevant non-message records
- Read-only inspection must not mutate transcript or history
- Output should stay simple enough for terminal use

## Non-Goals

- No interactive browser or TUI
- No graph visualization layer yet

## Done When

- There is a CLI path to inspect recent history and branch state
- Selected head and bind state are easy to see
- The behavior is covered by tests
