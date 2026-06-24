Filed as: 260624-graph-provenance-coverage-gap-closure
FKA:
AKA: graph provenance coverage gap; operator api lineage stats coverage; git sha helper coverage
Legacy index:

keywords: graph, hardening, active, correctness, coverage, provenance, diagnostics

Related: `260624-message-timestamps-and-toas-provenance`; `260624-cli-message-timestamp-assertion-cleanup`
Status: closed

# Graph Provenance Coverage Gap Closure

## Current Reality

The near-full-suite coverage report still leaves a tiny miss in the same
graph/provenance area: the git SHA helper fallback/success branches in
`graph.py` and the provenance fallback path in operator lineage stats.

## Desired Reality

The graph/provenance hardening slice should be fully covered by direct,
deterministic tests so the durable history diagnostics surface does not retain
small unexercised branches.

## Plan

- add direct tests for `_toas_git_sha` success and failure behavior
- add direct tests for `_lineage_stats` with unknown and empty provenance cases
- rerun the full suite coverage report to confirm the reported gap is closed

## Closure

Closed by `tests: close graph provenance coverage gap`.

Added deterministic unit coverage for git SHA resolution success/blank/failure
paths and for lineage-stat handling of empty and provenance-missing histories.
The full-suite coverage report now reaches 100%, confirming the reported gap is
closed even though unrelated environment-sensitive tests still fail in this
sandbox.
