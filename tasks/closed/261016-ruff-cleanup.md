Filed as: 261016-ruff-cleanup
FKA:
AKA: lint cleanup; ruff check cleanup; PLR0913 facades
Legacy index:

keywords: tooling, correctness, lint, maintenance

Parent:
Related: `260920-ruff-cleanup`

# Restore Repository Ruff Cleanliness

Clear current Ruff findings without changing runtime behavior, so normal
verification remains a trustworthy repository-wide gate.

## Scope

- Add `src/toas/cli.py` and `src/toas/tools.py` to `[tool.ruff.lint.per-file-ignores]`
  for `PLR0913` (too many arguments in dispatch/facade functions).

## Result

`uv run ruff check src tests`: clean.

Status: Complete.
