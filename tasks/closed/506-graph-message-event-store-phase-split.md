# 506 Graph Message/Event Store Phase Split

## Objective
Decompose high-branch durable history paths in `src/toas/graph.py` into focused helper seams so message-event append/query/lineage operations are easier to reason about and test.

## Why
`graph.py` remains one of the largest/highest-pressure modules (`~1000+` lines) and still dominates both complexity and coverage-miss noise; it is now the top decomposition target under `400`.

## Scope
- split one cohesive cluster from `graph.py` (message/event append or query path) into focused helper units/modules
- keep durable record semantics and on-disk history invariants unchanged
- add targeted tests for extracted helper branches and error paths
- preserve existing API surface for callers during this slice

## Done When
- selected `graph.py` cluster is materially slimmer and delegated to cohesive seams
- targeted graph tests and full suite pass with parity
- task progress is stitched with exact touched boundaries

## Related
- `400` decomposition umbrella
- `374` coverage-led refactor pass

## Progress
- extracted graph index record/read/seek/find/rebuild operations from `src/toas/graph.py` into new focused module `src/toas/graph_index_edges.py`
- preserved public graph API (`read_index`, `seek_index_by_position`, `find_index_by_id`, `rebuild_index`, `INDEX_RECORD_SIZE`) via thin delegation wrappers in `graph.py`
- added targeted seam tests in `tests/test_graph_index_edges.py` for round-trip records, missing/invalid/truncated index behavior, seek OSError handling, and rebuild filtering of invalid/non-message rows
- extracted message/lineage projection cluster from `src/toas/graph.py` into new focused module `src/toas/graph_message_edges.py` (`strip_reasoning_blocks`, `has_reasoning_blocks`, message-event selection/map, lineage-or-message selection, message view/lineage projection, and `project_llm_input_from_messages`)
- preserved existing `graph.py` API surface via thin delegating wrappers so callers/tests keep stable imports while decomposition proceeds
- extracted control-state/config-accumulation cluster from `src/toas/graph.py` into new focused module `src/toas/graph_control_state_edges.py` (`active_bind_index`, `active_head_id`, `active_command_context`, `active_workspace_scope`, `active_shell_scope_grants`, `active_config_overrides`, `deep_merge`, `deep_delete`)
- preserved existing `graph.py` API surface for these control/config helpers via thin delegation wrappers to keep callers stable during staged decomposition
- extracted core control/config writer helpers from `src/toas/graph.py` into new focused module `src/toas/graph_record_writers.py` (`write_jump_record`, `write_head_record`, `write_anchor_record`, `write_command_context_record`, `write_workspace_scope_record`, `write_config_override_record`, `write_shell_scope_grant_record`)
- preserved existing `graph.py` API surface for these writer helpers via thin delegation wrappers and retained `append_nodes` ownership at the graph boundary
- closeout note: before task closure, run a wrapper-flattening cleanup pass so extracted helper implementations are imported/called directly where practical; keep wrappers only where needed to preserve intended `toas.graph` public API stability, and remove unnecessary private/internal wrapper layers first
