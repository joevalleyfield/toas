Filed as: 260703-heads-selected-source-scope
FKA:
AKA: heads --sources; selected-source branch tips; source-qualified heads
Legacy index:

keywords: heads, graph, surface, source-selection, history

Parent: `260627-history-surface-user-intent-alignment`
Related: `260629-storage-scale-model-proof-contract`; `260627-split-storage-rebuild-and-projection-parity`

# Heads Selected Source Scope

## Current Reality

`graph` now has explicit `--sources` selection and source-qualified occurrence
identity. `heads` is the compact topology sibling to `graph`, but it still has
only its default current logical-history scope.

## Desired Reality

`toas heads --sources ...` should list branch tips over the explicitly selected
physical event-log sources, using source-qualified ids for multi-source scopes.

## Scope

- add `--sources <hot|segments|path> ...` parsing for `toas heads`
- preserve existing zero-arg `heads` behavior
- reuse selected-source integrity checks and source qualification from graph
- keep this topology-facing; do not stitch transcript or LLM-input surfaces

## Non-Goals

- `--stitch-diagnostics` for heads
- stitched alias display for heads rows
- changing default `heads` scope
- shared selection DSL

## Exit Evidence

- default `toas heads` output is unchanged
- `toas heads --sources segments hot` lists selected physical source tips with
  qualified ids
- same local ids across sources do not collapse into one head

## Outcome

Closed on 2026-07-03.

At closure time, this task left zero-arg `toas heads` behavior unchanged and
added `toas heads --sources ...` for explicitly selected physical event-log
sources. The selected-source mode renders multi-source branch tips with
source-qualified occurrence ids such as `000001:n1` and `hot:n1`.

The surface intentionally stays compact: it does not print stitched aliases or
stitch diagnostics yet. Same local ids across selected sources are expected
journal-local labels and remain separate branch-tip occurrences unless a future
surface explicitly asks for a stitched projection.

Verification:

- `./.codex-local/bin/uvt run pytest tests/test_operator_api.py tests/test_cli.py tests/test_cli_dispatch.py tests/test_cli_dispatch_ops.py tests/test_cli_surface_commands.py tests/test_cli_commands.py tests/test_daemon_ops.py tests/test_runtime_request_handler_edges.py tests/test_graph.py tests/test_history_scale_models.py -q --no-cov`
- `./.codex-local/bin/uvt run ruff check --select F src/toas/cli.py src/toas/cli_commands.py src/toas/cli_dispatch.py src/toas/cli_dispatch_ops.py src/toas/cli_surface_commands.py src/toas/cli_usage.py src/toas/graph.py src/toas/operator_api.py src/toas/runtime/request_ops.py tests/test_cli_dispatch.py tests/test_cli_dispatch_ops.py tests/test_cli_surface_commands.py tests/test_cli_commands.py tests/test_daemon_ops.py tests/test_operator_api.py --no-cache`

## Superseding Correction

`260703-heads-hot-default` supersedes the default-scope part of this outcome.
The selected-source mode remains valid, but zero-arg `heads` should follow the
hot-first topology convention rather than keeping stitched logical-history
behavior.
