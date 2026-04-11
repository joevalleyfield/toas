# Recurring Maintenance

This namespace separates recurring maintenance process definitions from one-off implementation tasks.

## Layout

- `templates/`: recurring process definitions (scope, cadence/trigger model, procedure, acceptance)
- `runs/`: dated execution records for each recurring process run

## Relationship To `tasks/open` / `tasks/closed`

- Recurring runs may spawn implementation/remediation tasks in `tasks/open/`.
- Close those spawned tasks through normal `tasks/closed/` flow.
- Keep recurring run records lightweight: what ran, why it ran, what it spawned.
