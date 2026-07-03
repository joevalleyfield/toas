Filed as: 260703-heads-hot-default
FKA:
AKA: heads hot-first default; break stitched heads default
Legacy index:

keywords: heads, graph, surface, source-selection, hot-default

Parent: `260627-history-surface-user-intent-alignment`
Related: `260629-storage-scale-model-proof-contract`; `260627-split-storage-rebuild-and-projection-parity`; `260703-heads-selected-source-scope`

# Heads Hot Default

## Current Reality

`toas graph` defaults to hot/current topology and uses `--sources` for broader
physical source inspection. `toas heads` has the same explicit `--sources`
surface, but its zero-arg path still reads stitched logical history.

That preserves an old parity idea rather than the newer hot-first convention.

## Desired Reality

`toas heads` should default to the hot event log, matching the graph topology
surface. Broader source inspection should be explicit through `--sources`.

## Scope

- change zero-arg `heads` from stitched logical history to hot/current history
- keep `heads --sources ...` behavior intact
- update tests and task language that still frame default `heads` as current
  logical history
- do not change `history`, `transcript`, or `llm-input` in this slice

## Exit Evidence

- a segmented hot/cold fixture proves default `heads` sees the hot leaf set
  only
- `heads --sources segments hot` still renders selected physical source tips
  with source-qualified ids
- task language records hot-first as the shared topology-surface default

## Outcome

Closed on 2026-07-03.

`toas heads` now follows the hot-first topology convention already used by
`toas graph`. Zero-arg `heads` reads the hot event log, validates that source
locally, and reports the hot branch tips. Broader physical inspection remains
explicit through `toas heads --sources ...`.

This intentionally breaks the previous stitched-default behavior. The old
"current logical history" parity language was replaced with hot/default versus
explicit selected-source wording in the task notes and mismatch matrix.

Verification:

- `./.codex-local/bin/uvt run pytest tests/test_operator_api.py tests/test_cli.py tests/test_cli_dispatch.py tests/test_cli_dispatch_ops.py tests/test_cli_surface_commands.py tests/test_cli_commands.py tests/test_daemon_ops.py tests/test_runtime_request_handler_edges.py tests/test_graph.py tests/test_history_scale_models.py -q --no-cov`
- `./.codex-local/bin/uvt run ruff check --select F src/toas/cli_usage.py src/toas/operator_api.py tests/test_history_scale_models.py tests/test_operator_api.py --no-cache`

The broader Ruff pass including `tests/test_cli.py` still hits the known
pre-existing unused-local backlog in that file.
