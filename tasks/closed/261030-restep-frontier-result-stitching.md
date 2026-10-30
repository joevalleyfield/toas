Filed as: 261030-restep-frontier-result-stitching
FKA:
AKA: restep result stitching; existing frontier message result persistence; empty catalog selection error
Legacy index:

keywords: runtime, implementation, closed, models, restep, session, persistence, selection

Parent:
Depends on: `260906-endpoint-model-discovery`; `260906-model-catalog-refresh`
Blocks:
Blocked by:
Related: `261029-openai-model-probe-auth-header`

# Restep Frontier Result Stitching and Empty Catalog Selection Error

Persist result records and side effects when restepping an existing message at
the frontier, and distinguish between missing models / empty catalogs versus
ambiguous matches in model selection.

## Current Reality

1. When an operator restepps an existing turn (e.g. trimming a failed or
   stale `## TOAS:RESULT` from `session.md` and running `toas step` again
   after code or environment changes):
   - The user message matches the existing tip in `log`, so `new_from_transcript`
     is empty (`[]`).
   - The execution consequences produce new result nodes (`role == "result"`),
     meaning `persisted_message_nodes` is empty and `materialized` is `[]`.
   - In `persist_step_outputs_runtime()`, `source_message_id` defaults to
     `materialized_head_id` (`None`), and `stitch_frontier_records()` returns
     immediately because `not materialized`.
   - As a result, no `command_request` / `command_result` or `tool_request` /
     `tool_result` records are written to `events.jsonl`, and side effects
     like `config_override` from `/models refresh` are written without a
     `related_to: source_message_id` link.
   - On the next turn, `_branch_config_from_direct_declarations()` fails to find
     the catalog update for that turn, leaving the known endpoint model catalog
     empty (`models: (none)`, `last refresh: (never)`).

2. In `discovered_model_selection()` (`src/toas/runtime/model_setup.py`),
   any match count other than 1 (`len(matches) != 1`) raises:
   `ValueError(f"model is not uniquely identified in {endpoint_id}: {model}\nuse /models known {endpoint_id} for selection commands")`
   When `len(matches) == 0` (such as when the catalog is empty or the model
   does not exist), it misleadingly claims the model is "not uniquely identified",
   causing users to suspect prefix or substring ambiguity when the catalog
   simply has no matches.

## Desired Reality

1. When `run_step` produces consequences for a frontier turn where `materialized`
   is empty (re-executing an existing message), `persist_step_outputs_runtime()`
   identifies the existing frontier message in the active lineage/bound log as
   `source_message_id` and allows `stitch_frontier_records()` to write the
   corresponding result records and linked side effects.
2. In subsequent turns, `_branch_config_from_direct_declarations()` successfully
   finds the linked `config_override` and reconstructs the refreshed catalog.
3. In `discovered_model_selection()`, when `len(matches) == 0`, raise a clear
   error indicating the model was not found in the endpoint catalog (distinguishing
   between an empty catalog and a nonexistent model), and reserve
   "not uniquely identified" specifically for ambiguous matches (`len(matches) > 1`).

## Acceptance Criteria

- When restepping an existing frontier turn, command and tool results are
  persisted to `events.jsonl` with proper linkage to the frontier message ID.
- Config updates emitted by restep consequences (such as `/models refresh`)
  persist with `related_to` set to that frontier message ID and successfully
  reconstitute in subsequent steps.
- `discovered_model_selection()` raises a distinct error when `len(matches) == 0`
  (e.g. `f"unknown model in {endpoint_id}: {model}\n..."` or `f"no known models for endpoint {endpoint_id}\nhint: use /models refresh {endpoint_id} first"`).
- `discovered_model_selection()` raises `not uniquely identified` only when
  `len(matches) > 1`.
- Tests verify restep persistence and error distinction.
- Full test suite passes without regressions.

## Completion

- `persist_step_outputs_runtime` in `src/toas/runtime/step_result_runtime.py` now resolves `frontier` from `materialized_lineage` when `materialized` is empty (during a restep), deriving `source_message_id` and passing `frontier` to `stitch_frontier_records`.
- `stitch_frontier_records` in `src/toas/runtime/session_step_edges.py` now accepts `frontier` and persists command and tool records for the existing frontier message when `materialized` is empty.
- Side effects (`config_override` from `/models refresh`) are now correctly linked with `related_to` set to the frontier message ID, allowing `_branch_config_from_direct_declarations` to reconstitute the catalog on subsequent steps.
- `discovered_model_selection` in `src/toas/runtime/model_setup.py` now distinguishes between an empty catalog (`no known models for endpoint ...`), a missing model (`unknown model in ...`), and ambiguous matches (`model is not uniquely identified in ...`).
- Added targeted tests in `tests/test_model_setup.py`, `tests/test_runtime_step_result_runtime.py`, `tests/test_runtime_session_step_edges.py`, and `tests/test_endpoint_state_continuity.py`. Full test suite and `./scripts/check.sh` pass at 100.00% statement coverage.

## Status

Closed 2026-10-30.
