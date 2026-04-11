# Gentle Complexity Pressure For Maintainability

## Objective

Apply steady, low-friction pressure against structural complexity so the codebase stays understandable for:

- human operators (especially slower context-switching workflows)
- smaller models with limited context/reasoning budget

The aim is not stylistic purity. The aim is keeping change surfaces legible and reducing cognitive overhead.

## Principles

- Prefer gradual tightening over hard flips.
- Favor actionable checks over noisy checks.
- Keep exceptions explicit and documented.
- Treat complexity signals as design prompts, not automatic failures at first.

## Initial Pressure Set

Use lint/type checks to surface complexity drift with relaxed thresholds, then tighten over time:

- argument count
- branch count
- statement count
- cyclomatic complexity

These should begin as audit-visible signals and only become hard gates after repeated stability.

## Operational Pattern

1. Collect complexity signals in recurring maintenance runs.
2. Spawn remediation tasks when complexity impacts readability or reviewability.
3. Allow targeted exceptions with rationale when boundaries are intentionally large.
4. Periodically re-evaluate thresholds and enforcement level.

## Relationship To Recurring Maintenance

This objective should be referenced by recurring maintenance templates/runs (task 343 namespace work) so checks stay intentional and do not degrade into ad hoc style churn.
