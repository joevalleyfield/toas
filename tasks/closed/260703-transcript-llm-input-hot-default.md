Filed as: 260703-transcript-llm-input-hot-default
FKA:
AKA: transcript hot-first default; llm-input hot-first default
Legacy index:

keywords: transcript, llm-input, surface, hot-default, projection

Parent: `260627-history-surface-user-intent-alignment`
Related: `260629-storage-scale-model-proof-contract`; `260627-split-storage-rebuild-and-projection-parity`; `260703-history-hot-default`

# Transcript And LLM-Input Hot Default

## Current Reality

`graph`, `heads`, and `history` now default to hot/current history. `transcript`
and `llm-input` still read stitched logical history by default and refuse when
cross-source journal-local ids require alignment proof.

That leaves the old logical-parity assumption alive in the two main projection
surfaces.

## Desired Reality

Zero-arg `toas transcript` and `toas llm-input` should default to hot/current
history. They should keep their distinct projection semantics, but they should
not implicitly traverse stitched logical history or refuse merely because cold
and hot sources share local ids.

## Scope

- change default `transcript_text(...)` from stitched logical history to hot
  history
- change default `llm_input_messages(...)` from stitched logical history to hot
  history
- preserve explicit `head_id` behavior within the hot source
- preserve LLM-input envelope shaping over the selected hot lineage
- update scale-model tests and contract notes
- do not add source selectors for these projection surfaces yet

## Exit Evidence

- segmented hot/cold fixtures prove default transcript and LLM-input project
  hot history only
- same local ids across sources no longer make default transcript or LLM-input
  refuse
- fatal source-local hot corruption still refuses

## Outcome

Closed on 2026-07-03.

`toas transcript` and `toas llm-input` now follow the hot-first default
convention. Both validate and read the hot event log, then apply their existing
projection semantics over that hot lineage. `llm-input --envelope` continues to
shape the same hot lineage through the context packet path.

Cross-source same local ids no longer make default transcript or LLM-input
refuse. Broader transcript/model-input projections over selected sources or
stitched equivalence remain future explicit modes.

Verification:

- `./.codex-local/bin/uvt run pytest tests/test_operator_api.py tests/test_history_scale_models.py tests/test_cli.py tests/test_cli_dispatch.py tests/test_cli_commands.py tests/test_runtime_request_handler_edges.py tests/test_graph.py -q --no-cov`
- `./.codex-local/bin/uvt run ruff check --select F src/toas/operator_api.py tests/test_operator_api.py tests/test_history_scale_models.py --no-cache`
