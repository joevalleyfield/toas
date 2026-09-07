Filed as: 260907-endpoint-normalizer-naming
FKA:
AKA: endpoint normalization naming cleanup
Legacy index:

Parent: `260907-endpoint-command-cutover`
Depends on: `260907-endpoint-command-cutover`
Blocks:
Blocked by:
Related: `docs/notes/2026-09-06-endpoints-models-and-targets.md`

keywords: endpoint, backend, config, normalization, documentation

# Remove Residual Endpoint Normalizer Backend Names

Remove remaining backend vocabulary from endpoint materialization locals and
align the current endpoint/model design note with the canonical command
surface. Preserve backend names that describe actual lifecycle or policy.

## Progress Evidence

Completed: endpoint materialization locals now use endpoint terminology, and
the current endpoint/model design note records `/config endpoint` and
`/endpoint` as canonical while explicitly limiting compatibility to legacy
`llm.backends` config-file input.

Verification: the endpoint command cutover full suite passed with 3208 tests,
14 deselected, and 100% coverage; the working copy is clean after commit.
