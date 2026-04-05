## Goal

Improve the operator's ability to inspect, navigate, and debug the branching history — ancestry inspection, branch summaries, selective rebuild, and divergence debugging.

## Why Now

The current branch UX is minimal: `toas heads` lists known heads, `toas head <id>` selects one, `toas transcript` projects from the selected head. There is no way to see how heads relate, summarize what happened on a branch, or debug why two lineages diverged. As sessions accumulate branches this becomes a real operator friction point.

## Scope

Sub-tasks to be elaborated when this arc becomes active:

- **head ancestry inspection**: show the lineage path from a head back to its root or to a common ancestor with another head; useful for understanding branch origin
- **branch summaries**: a brief human-readable summary of what happened on each branch (turn count, last message preview, callable executions)
- **selective rebuild targets**: `toas rebuild` currently rebuilds from the full projected lineage; allow targeting a specific ancestor node or a specific turn count
- **divergence debugging**: given two heads, show where their lineages diverged and what the first differing message was

## Design Notes

This arc is further out and the sub-tasks are less defined than 270–282. Elaborate and decompose into numbered tasks (291, 292, ...) when the arc becomes the active next move.

The core primitive needed for most of this work is an efficient ancestry walk over `events.jsonl` — given a node ID, reconstruct its full parent chain. That walk exists implicitly in `_lineage_events` in `graph.py` but is not exposed as a standalone utility.

## Constraints

- no new record types required; this arc is read-only inspection over existing durable history
- sub-tasks should be independently landable
- avoid deep CLI surface changes; prefer extending existing commands (`toas heads`, `toas history`) before adding new top-level commands
