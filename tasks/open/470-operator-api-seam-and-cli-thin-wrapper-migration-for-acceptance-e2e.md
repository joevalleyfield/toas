# 470 Operator API Seam And CLI Thin-Wrapper Migration For Acceptance E2E

## Objective
Establish a first-class operator API surface equivalent to CLI semantics and migrate CLI to thin-over-API incrementally, so acceptance tests can validate operator behavior at the correct abstraction level.

## Why
Current acceptance scenarios (task `469`) are useful but mix low-level internals (`step`, `graph`) with user-facing behavior checks. This blurs what is truly end-to-end.

We need:
- a stable operator-facing API seam (faster and less brittle than subprocess-only CLI tests)
- CLI as a thin wrapper over that seam
- a small subprocess smoke layer to verify CLI parsing/formatting/wiring

## Scope
In scope:
- define acceptance test-layer taxonomy:
  - `acceptance-integration` (current mixed/internal seam)
  - `acceptance-operator-api` (target primary acceptance layer)
  - `acceptance-cli-smoke` (small black-box sanity layer)
- introduce operator API module(s) for step/history/heads/rebuild semantics (incremental)
- migrate CLI command handlers touched by this work to thin wrappers over operator API
- port `469` scenarios from direct low-level calls to operator API as seams land

Out of scope:
- complete full command surface migration in one pass
- deprecating current integration scenarios immediately

## Plan
1. Define minimal operator API contract for `step` (structured input/output)
2. Migrate CLI `step` path to call operator API and preserve stdout contract
3. Port `469` S1 scenario to operator API usage only
4. Extend operator API with history/head/rebuild query methods
5. Port `469` S2/S3 to operator API usage only
6. Add 1-2 subprocess CLI smoke tests per migrated command family
7. Keep refactor pressure aligned with `400` and coverage guardrails aligned with `374`

## Acceptance Criteria
- Operator API exists for at least `step` with explicit behavior contract
- CLI `step` command is thin-over-API with no behavior regression
- At least one `469` scenario runs through operator API seam instead of direct low-level internals
- CLI smoke tests verify wrapper path remains correctly wired
- Task `469` updated to reflect layer distinctions and migration progress

## Risks
- API seam may drift into internal implementation leakage
- Thin-wrapper migration could accidentally change stdout ordering/format
- Partial migration could temporarily increase conceptual complexity

## Mitigations
- Keep API contract compact and behavior-first
- Preserve existing CLI contract tests while migrating
- Land in small slices with explicit compatibility assertions

## Related
- `469` functional acceptance epic (consumer of this seam)
- `400` decomposition and boundary clarity arc
- `374` coverage-led refactor/testability arc

## Progress
- Added `src/toas/operator_api.py` with initial `step_once()` seam and structured `StepOutcome`.
- Migrated `cli.run_step_local()` to call `operator_api.step_once()` (thin wrapper path starts).
- Added seam/adapter tests:
  - `tests/test_operator_api.py` verifies `step_once()` delegates to `cli_session_commands.run_step_local()`.
  - `tests/test_cli.py::test_run_step_local_delegates_to_operator_api` verifies CLI local path delegates through operator API.
- Extended operator API with high-level query/build operations:
  - `heads_lines(events_path=...)`
  - `history_lines(events_path=..., limit=...)`
  - `rebuild_session(events_path=..., head_id=...)`
- Migrated CLI local handlers to thin wrappers over those API methods:
  - `run_heads_local()`
  - `run_history_local()`
  - `run_rebuild_local()`
- Began `469` seam lift by migrating `S1` to call `operator_api.step_once()` against a real repo-local session/events workspace (instead of direct `toas.step` invocation).
- Continued `469` seam lift:
  - `S2` now runs via `operator_api.step_once()` from repo-local transcript/events context (no direct `toas.step` call in scenario steps).
  - `S3` recovery checks now consume operator API query/build seams (`history_lines`, `heads_lines`, `rebuild_session`) instead of direct low-level graph calls.
  - implementation narration adjusted to operator-natural shell shorthand for deterministic non-LLM execution in acceptance replay mode.
- Added direct operator-API contract coverage for migrated query/rebuild seams:
  - `tests/test_operator_api.py` now validates `heads_lines()` selected-head formatting, `history_lines()` selected/bind/recent framing, and `rebuild_session()` transcript write + target label behavior.
- Added next CLI-thin migration slice for head selection:
  - Introduced `operator_api.select_head(events_path=..., head_id=...)` with structured `HeadOutcome`.
  - Migrated `cli.run_head_local()` to delegate to `operator_api.select_head()` (removing direct `write_head_record` call from CLI path).
  - Added/updated seam coverage:
    - `tests/test_operator_api.py::test_select_head_writes_head_record_and_message`
    - existing `tests/test_cli.py::test_run_head_is_invokable` continues to assert CLI contract parity.
- Added next CLI-thin migration slice for transcript/llm-input projection:
  - Introduced `operator_api.transcript_text(events_path=..., head_id=...)` returning structured `TranscriptOutcome`.
  - Introduced `operator_api.llm_input_messages(events_path=..., head_id=...)` returning structured `LLMInputOutcome`.
  - Migrated `cli.run_transcript_local()` and `cli.run_llm_input_local()` to delegate through operator API seams (CLI now handles only output projection/printing).
  - Removed now-redundant `cli_session_views` helpers for transcript/llm-input to avoid dual ownership of projection semantics.
  - Added direct seam coverage:
    - `tests/test_operator_api.py::test_transcript_text_projects_selected_head`
    - `tests/test_operator_api.py::test_llm_input_messages_projects_selected_head`
- Added next CLI-thin migration slice for prompt rendering/listing:
  - Introduced `operator_api.prompt_text(events_path=..., ref=..., mode=..., constraints=...)` returning structured `PromptOutcome`.
  - Introduced `operator_api.prompt_list_lines(prefix=...)` returning structured `PromptListOutcome`.
  - Migrated `cli.run_prompt_local()` and `cli.run_prompts_local()` to delegate to operator-api seams and keep CLI-side behavior as stdout projection only.
  - Added seam coverage:
    - `tests/test_operator_api.py::test_prompt_text_resolves_with_configured_constraints`
    - `tests/test_operator_api.py::test_prompt_list_lines_lists_assets`
- Added next CLI-thin migration slice for intents/session-path views:
  - Introduced `operator_api.intents_lines(events_path=...)` returning structured `IntentsOutcome`.
  - Introduced `operator_api.session_path_text(events_path=...)` returning structured `SessionPathOutcome`.
  - Migrated `cli.run_intents_local()` and `cli.run_session_path_local()` to delegate through operator API seams (CLI retains print-only behavior).
  - Added seam coverage:
    - `tests/test_operator_api.py::test_intents_lines_reports_none_when_missing`
    - `tests/test_operator_api.py::test_session_path_text_uses_resolved_config_path`
  - Removed now-dead `cli_session_views.run_intents_local()` helper to avoid duplicate ownership of intent formatting logic.
- Added next CLI-thin migration slices for analysis/index surfaces:
  - Introduced `operator_api.diff_lines(events_path=..., head_a=..., head_b=..., full=...)` returning structured `DiffOutcome`.
  - Introduced `operator_api.ancestry_lines(events_path=..., message_id=..., depth=..., full=...)` returning structured `AncestryOutcome`.
  - Migrated `cli.run_diff_local()` and `cli.run_ancestry_local()` to delegate through operator-api seams, preserving existing output shape (including bracketed provenance markers).
  - Introduced `operator_api.index_rebuild_message(events_path=...)` returning structured `IndexRebuildOutcome`.
  - Migrated `cli.run_index_rebuild_local()` to operator-api seam.
  - Added seam coverage:
    - `tests/test_operator_api.py::test_diff_lines_reports_common_ancestor`
    - `tests/test_operator_api.py::test_ancestry_lines_reports_tail`
  - Retired now-obsolete module/test pair:
    - deleted `src/toas/cli_analysis_commands.py`
    - deleted `tests/test_cli_analysis_commands.py`

## Motivation Shift
- Original acceptance-lane motivation from `469` is now largely satisfied (`469` closed).
- Remaining high-value motivation is runtime architecture hygiene:
  - reduce daemon/runtime self-shell subprocess paths where direct operator API parity is viable.
- This follow-on is tracked explicitly in task `489` so `470` does not become a catch-all umbrella.
