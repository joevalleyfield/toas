# 560 Attention-Focused Workboard Layout

## Why
The current Workboard lists all open tasks, which can overwhelm the operator with low-priority or stale items. The "Strategic Priorities" section is manual and often disconnected from the auto-generated list.

The Workboard should actively filter and prioritize tasks based on the operator's current context and strategic goals, acting as an "attention filter" rather than a simple inventory.

## Goal
Design and implement an "Attention-Focused" layout for the Workboard that highlights high-impact tasks and suppresses noise.

## Scope
- Define criteria for "High-Attention" tasks (e.g., recent activity, strategic alignment, blocking dependencies).
- Update `sync_workboard.py` to categorize tasks into "Focus," "Context," and "Archive" based on these criteria.
- Redesign the Workboard markdown structure to emphasize the "Focus" section.
- Allow manual override of the "Focus" list.

## Non-Goals
- Complex ranking algorithms.
- Real-time attention tracking.

## Proposed Direction
1. **Focus Criteria:**
   - Recently modified (last 7 days).
   - Part of a "Strategic Priority" (from `roadmap.md` or manual Workboard section).
   - Blocking other high-priority tasks (from inferred dependencies).
2. **Layout:**
   - `## 🎯 Focus`: Top 3-5 high-attention tasks.
   - `## 📋 Context`: Other active tasks, grouped by theme.
   - `## 📦 Archive`: Stale or low-priority tasks (collapsed by default).
3. **Automation:**
   - Script automatically populates "Focus" based on criteria.
   - Operator can pin/unpin tasks in "Focus."

## Validation
- Run the script on the current state.
- Verify that the "Focus" section contains the most relevant tasks.
- Check that the layout is readable and actionable.

## Related
- `557` Exploratory work representation model
- `558` Auto-inferred task dependencies
- `559` Workboard as control surface
