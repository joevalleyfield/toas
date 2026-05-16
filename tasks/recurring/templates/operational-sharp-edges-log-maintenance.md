# Recurring: Operational Sharp-Edges Log Maintenance

## Purpose
Keep a durable log of empirical operator/runtime/tooling failures and sharp edges, with clear repro and triage state.

## Trigger
- Biweekly
- Or after any spike/acceptance run that reveals a new failure mode

## Inputs
- Sharp-edges log artifact
- Recent spike transcripts and failure notes
- Open runtime/tooling tasks

## Checklist
- Add newly observed sharp edges in canonical entry format
- Update status/progress of prior entries
- Link entries to tasks (open/closed) where applicable
- Prune duplicates and merge overlapping entries

## Output
- Dated run record in `tasks/recurring/runs/`
- Updated sharp-edges log with traceable status changes
