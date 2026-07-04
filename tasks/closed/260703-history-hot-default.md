Filed as: 260703-history-hot-default
FKA:
AKA: history hot-first default; break stitched history default
Legacy index:

keywords: history, surface, hot-default, projection, source-selection

Parent: `260627-history-surface-user-intent-alignment`
Related: `260629-storage-scale-model-proof-contract`; `260627-split-storage-rebuild-and-projection-parity`; `260703-heads-hot-default`

# History Hot Default

## Current Reality

`toas graph` and `toas heads` now default to hot/current history and require
explicit source selection for broader physical inspection. `toas history` still
reads stitched logical history by default and refuses when cross-source local
ids need alignment proof.

That keeps the old logical-parity assumption alive on a core operator surface.

## Desired Reality

Zero-arg `toas history` should follow the same hot-first default convention:
show the root-to-head lineage through the hot event log. Future broader history
or stitched projection modes should be explicit rather than implicit.

## Scope

- change default `history_lines(...)` from stitched logical history to hot
  history
- keep output shape as a root-to-head lineage window
- update scale-model tests that still group `history` with stitched projection
  refusal surfaces
- update task/note language so hot-first is the default surface convention
- do not change `transcript` or `llm-input` in this slice

## Exit Evidence

- segmented hot/cold fixtures prove default `history` sees the hot lineage only
- same local ids across sources no longer make default `history` refuse
- transcript and LLM-input refusal expectations remain explicit for now

## Outcome

Closed on 2026-07-03.

`toas history` now follows the hot-first default convention. It validates and
reads the hot event log, then renders one root-to-head lineage window from that
hot scope. Cross-source same local ids no longer make default `history` refuse;
only transcript and LLM-input remain on the stitched compatibility/refusal path
in this slice.

This intentionally breaks the previous implicit stitched-logical-history
default. Broader history, selected-source history, or stitched projection modes
remain future explicit selector work.

Verification:

- `./.codex-local/bin/uvt run pytest tests/test_operator_api.py tests/test_history_scale_models.py tests/test_cli.py tests/test_cli_dispatch.py tests/test_cli_commands.py tests/test_runtime_request_handler_edges.py tests/test_graph.py -q --no-cov`
- `./.codex-local/bin/uvt run ruff check --select F src/toas/operator_api.py tests/test_operator_api.py tests/test_history_scale_models.py --no-cache`
