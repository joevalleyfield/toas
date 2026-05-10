# Function-Intent Test Audit (Pass 1)

Date: 2026-05-10
Scope: active surfaces around `500`, `501`, `504`, `483`, `485`.

## Method
For each target function cluster:
- define intended behaviors (intent)
- check current tests for explicit assertions of those behaviors
- mark status: `covered`, `partial`, or `gap`

## Audit Matrix

### 1) `src/toas/tools_cluster/shell_streaming.py`
Functions:
- `run_streaming_subprocess`
- `_stream_debug_enabled`
- `_stream_debug`

Intent assertions:
- emits combined stdout and preserves output text: `covered`
- timeout raises deterministic tool-level error: `covered`
- debug toggle honors env truthy/falsey forms: `covered`
- debug writes JSONL to default path when env path absent: `covered`
- reader fallback/selector failure paths do not lose output or crash caller: `partial`

Notes:
- New tests added for primary timeout/debug/remainder paths.
- Still missing robust assertions for low-level selector/register/read exception branches under real thread behavior.

### 2) `src/toas/runtime/operator_command_prompt_workspace.py` (500 slices)
Functions:
- `_handle_lens` family including `_build_lens_packet_quality`, `_lens_doctor_result_from_quality`
- `_handle_shell` and `_handle_shell_config` helper extracts

Intent assertions:
- command usage validation and parse errors: `covered`
- lens packet/doctor behavior parity after extraction: `covered`
- shell config/list/mutation/reset output contracts: `covered`
- helper-level branch semantics (internal-only seams) remain behavior-equivalent: `partial`

Notes:
- Existing tests heavily cover top-level behavior contracts.
- Opportunity: add direct seam tests for extracted helper pairs where a bug could preserve line coverage but alter wording/order.

### 3) `tests/conftest.py` missing-files gate (`504`)
Functions:
- `pytest_sessionfinish`
- `pytest_terminal_summary`

Intent assertions:
- gate skips when `--no-cov` or no `.coverage`: `covered`
- gate failure does not suppress coverage report output: `covered`
- gate sets failing exit status in terminal summary path: `covered`

Notes:
- behavior now matches expected reporting contract.

### 4) intent arbitration fallback surface
File:
- `src/toas/runtime/intent_arbitration_edges.py`

Intent assertions:
- `yaml_position=any` with parse errors behaves deterministically: `covered`
- mixed candidate ordering by textual position: `covered`

Notes:
- recently closed one ambiguity branch via focused test.

## Gaps To Address Next
1. `shell_streaming` low-level reader exception branches:
- add controlled tests for `selectors.register/select` failure behavior and ensure caller receives deterministic output/error contract.

2. prompt-workspace extracted helpers (500):
- add direct seam tests for helper output phrasing/order where user-visible contract matters.

3. audit expansion:
- run pass 2 on `501` and `503` hotspots with same matrix format.

## Recommendation
Treat this audit as recurring alongside coverage ratchets:
- Ratchet line/file coverage.
- In parallel, ratchet `gap/partial` counts in this audit matrix.
