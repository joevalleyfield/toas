Filed as: 559-workboard-as-control-surface
FKA: 559-workboard-as-control-surface
AKA: workboard control; bidirectional sync; workboard ui
Legacy index: 559

keywords: surface, exploration, parked, usability, workboard, control-surface

Related: `260524-exploratory-work-representation-model`

# Workboard as Control Surface

If the Workboard is to be a primary interface for project management, it needs to support bidirectional interaction. The operator should be able to update the Workboard, and have those changes reflected in the underlying task files or system state.

## Goal
Transform `WORKBOARD.md` from a passive report into an active control surface that allows the operator to influence system behavior.

## Scope
- Define an "editable" format for `WORKBOARD.md` (e.g., using comments or specific markers).
- Update `sync_workboard.py` to parse and apply edits from the Workboard back to task files or system configuration.
- Implement a simple CLI interface for updating the Workboard (e.g., `toas workboard update`).
- Ensure that manual edits in the Workboard are preserved and not overwritten by automated syncs (unless explicitly requested).

## Non-Goals
- Full GUI integration.
- Real-time collaboration features.

## Proposed Direction
1. **Dual-Mode Parsing:** The script should distinguish between "generated" sections (auto-synced) and "controlled" sections (manually edited).
2. **Control Commands:** Support simple commands in comments, e.g., `<!-- CONTROL: set_status=525, status=blocked -->`.
3. **Sync Strategy:** When syncing, read control commands, apply them to the underlying data (if possible), and then re-generate the auto-synced sections.
4. **Audit Log:** Maintain a log of all control commands and their effects.

## Validation
- Test the bidirectional sync with a sample task.
- Verify that control commands are applied correctly.
- Ensure that manual notes in "controlled" sections are preserved.

## Progress

- 2026-06-07: Ran a roadmap/workboard hygiene pass after closed-task drift was noticed. Regenerated managed Workboard sections and cleaned manual active/open claims so closed tasks are historical context rather than active queue entries.
- 2026-06-14: Re-triaged tasks/workboard/roadmap after follow-on drift: kept task files in place, repaired active-vs-parked lifecycle metadata for `510`, `675`, and `676`, removed closed `680` from roadmap parked work, simplified the manual Workboard arc map around active umbrellas only, and relabeled the generated Workboard inventory from "Now" to "Open Queue."

## Related
- `557` Exploratory work representation model
- `sync_workboard.py` (existing automation)
