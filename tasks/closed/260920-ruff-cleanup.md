Filed as: 260920-ruff-cleanup
FKA:
AKA: lint cleanup; typing modernization; import normalization
Legacy index:

keywords: tooling, correctness, lint, typing, maintenance

Parent:
Related: `260829-ruff-cleanup`; `260920-lcp-direct-policy-deltas`

# Restore Repository Ruff Cleanliness

Clear current Ruff findings without changing runtime behavior, so normal
verification remains a trustworthy repository-wide gate.

## Scope

- Modernize built-in generic and union annotations in
  `scripts/canonical_prefix_collapse.py`.
- Normalize imports in that script and the transcript-policy integration test.

## Result

Ruff’s mechanical fixer applied 33 safe import/annotation fixes. Verified with
`./.codex-local/bin/uvt run ruff check .`: clean.

Status: Complete.
