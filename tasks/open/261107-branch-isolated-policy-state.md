Filed as: 261107-branch-isolated-policy-state
FKA:
AKA: branch policy isolation; active policy state head filter; lineage scoped policy overrides
Legacy index:

keywords: policy, graph, lineage, branch-isolation, config, active

Parent: `260920-effective-policy-provenance-inspection`
Related: `260920-branch-projected-policy-program`; `260920-lcp-direct-policy-deltas`

# Branch-Isolated Policy State Resolution

## Intent

Ensure that `active_policy_state` and runtime context resolution only consider
policy overrides belonging to the active branch lineage, preventing dead or
sibling branches in `events.jsonl` from silently leaking overrides into the
active working session.

## Context & Motivation

In task `260920-effective-policy-provenance-inspection`, TOAS established the
invariant that policy is branch-isolated and that the system must "select an
explicit transcript head or the active frontier without reading unrelated sibling
records as policy." That task introduced `branch_policy_records(events, head_id=...)`
in `graph.py` to partition policy records by `source_id in lineage_ids`.

However, the primary runtime policy resolver, `active_policy_state(events)` in
`src/toas/graph_control_state_edges.py`, and its callers in
`step_context_runtime.py` and `operator_command_config_help.py`, were never wired
to filter by branch or lineage. Instead, `active_policy_state` sequentially
processes every `policy_override` record across all of `events.jsonl`.

When a session rewrites or branches from an earlier ancestor, policy overrides
from abandoned sibling forks (such as `n774` setting `session.telemetry_decorations compact`)
silently apply to the active branch, causing `/config show session --sources`
to attribute policy to unlinked sibling events.

## In Scope

1. **Head & Lineage Filtering in `active_policy_state`**:
   - Add `head_id: str | None = None` and `lineage_ids: set[str] | None = None`
     parameters to `active_policy_state` and related helpers (`active_config_overrides`,
     `active_shell_grants`, `active_target_selection`).
   - If message events are present in `events`:
     - Determine active lineage message IDs for the target `head_id` (or terminal message event).
     - Filter supported policy records so that records linked via `related_to` / `source_id`
       are only active when their source message is in the active lineage.
     - Unlinked legacy fallback records remain active as fallback.
   - If no message events exist (e.g. synthetic test lists of pure policy records),
     preserve existing behavior.

2. **Runtime Context Wiring**:
   - Update `resolve_runtime_generation_context` in `src/toas/runtime/step_context_runtime.py`
     to accept `head_id: str | None = None` and pass it to `active_policy_state`.
   - Update `build_runtime_context` / session command entry points in
     `src/toas/cli_session_commands.py` to supply `head_id` from the resolved runtime context lineage.
   - Update `_config_show_result` / `_effective_config_values` in
     `src/toas/runtime/operator_command_config_help.py` to use `head_id` from `context.working`.

3. **Verification**:
   - Add unit and integration tests proving that policy overrides on a branched/abandoned
     sibling fork do not leak into the active branch.
   - Ensure 100.00% statement coverage under `./scripts/check.sh`.

## Out of Scope

- Changing the schema of `policy_override` event payloads in `events.jsonl`.
- Altering file-based configuration loading hierarchy.

## Acceptance Criteria

1. **Sibling Branch Isolation**: Policy overrides written on an abandoned sibling
   branch do not apply to an active branch diverged before that sibling.
2. **Provenance Attribution**: `/config show --sources` reports sources only from
   the active branch lineage, config files, or defaults, never naming sibling nodes.
3. **Backward Compatibility**: Calling `active_policy_state` on pure policy record lists
   without message trees preserves existing behavior.
4. **Coverage & Checks**: Passes `./scripts/check.sh` with 100.00% statement coverage.

## Implementation Plan

1. **Phase 1: Lineage Isolation in `active_policy_state`**
   - Update `active_policy_state` in `graph_control_state_edges.py` to accept `head_id: str | None = None` and `lineage_ids: set[str] | None = None`.
   - Filter `policy_override`, `shell_scope_grant`, `target_selection` by `lineage_ids` when message events exist in `events`.
   - Update `active_config_overrides`, `active_shell_grants`, `active_target_selection` to forward `head_id`.
   - Unit tests in `tests/test_graph_control_state_edges.py`.

2. **Phase 2: Runtime Generation Context & CLI Wiring**
   - Wire `head_id` through `resolve_runtime_generation_context` and `cli_session_commands.py`.
   - Wire `head_id` from `context.working` in `operator_command_config_help.py`.
   - Tests in `tests/test_runtime_config_show_sources.py` and `tests/test_cli_session_commands.py`.

3. **Phase 3: Verification & QA**
   - Recreate the exact scenario from `toas-dogfood` in a regression test.
   - Full suite `./scripts/check.sh` pass.
