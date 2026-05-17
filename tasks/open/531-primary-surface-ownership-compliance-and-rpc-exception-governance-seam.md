# 531 Primary-Surface Ownership Compliance and RPC-Exception Governance Seam

## Goal
Define and implement explicit compliance checks for primary operator surfaces so ownership-first behavior is testable and any RPC-only exceptions are deliberate, documented, and removable.

## Why
`525` needs concrete guardrails after `526` inventory and `530` lifecycle hardening. Without explicit checks, RPC-era drift can re-enter primary paths (`step`, `step --async`, `watch`, `cancel`) silently.

## Scope
In scope:
- codify ownership-first expectations for primary surfaces
- add/adjust tests that assert local/operator-API-first execution behavior where available
- document any unavoidable RPC exceptions with rationale and removal path
- keep Vim-facing behavior parity (no regression in streaming/cancel surfaces)

Out of scope:
- daemon removal in one pass
- transport/protocol redesign
- broad frontend strategy changes (`490`)

## Done When
- primary-surface compliance checks exist and pass
- RPC-only exceptions are explicitly documented and justified
- roadmap reflects the new active `525` slice
- full suite passes

## Related
- `525` post-envelope runtime ownership and primary-path de-daemonization
- `526` RPC dependency inventory and exception governance
- `530` shared terminality policy seam

## Progress
- implemented first compliance slice:
  - added explicit ownership-first guard tests for `step` direct-intent modes:
    - `run_step(stdin_mode=True)` never attempts RPC, even when RPC is otherwise preferred
    - `run_step(control=...)` never attempts RPC, even when RPC is otherwise preferred
  - codifies `step` primary-surface policy boundary: direct transcript/control injection is always local/operator-owned
  - validates this as a no-regression contract for future `525` migration slices
  - validated with:
    - `uv run pytest -q tests/test_cli.py --no-cov`
    - `uv run pytest -q -n 14`

## Compliance Matrix (Current)
- `step`:
  - ownership expectation: local/operator-owned by default, with RPC as optional transport optimization when allowed
  - explicit local-only submodes: `--stdin`, `--control` must never RPC
  - test anchors:
    - `tests/test_cli.py::test_run_step_stdin_mode_never_attempts_rpc_even_when_preferred`
    - `tests/test_cli.py::test_run_step_control_mode_never_attempts_rpc_even_when_preferred`
    - `tests/test_cli.py::test_run_step_prefers_rpc_when_available`
    - `tests/test_cli.py::test_run_step_falls_back_to_local_when_rpc_fails`
- `step --async`:
  - ownership expectation: currently RPC-backed lifecycle activity
  - current exception rationale: async run/watch/cancel state is daemon run-store owned in current architecture
  - removal path: migrate async activity ownership to primary runtime host surface under `525` follow-on slices
  - test anchors:
    - `tests/test_cli_async_commands.py::test_run_step_async_happy_path_prints_run_id_and_status`
    - `tests/test_cli_async_commands.py::test_run_step_async_requires_rpc_enabled`
- `watch`:
  - ownership expectation: currently RPC-backed lifecycle stream consumer
  - current exception rationale: reads daemon-owned async run-store output/event state
  - removal path: move watch stream source to ownership-first runtime host surface while preserving envelope compatibility
  - test anchors:
    - `tests/test_cli_async_commands.py::test_run_watch_requires_rpc_enabled`
    - `tests/test_daemon_run_store.py::test_watch_follow_protocol_shape_parity_across_watch_flag`
- `cancel`:
  - ownership expectation: currently RPC-backed lifecycle mutation
  - current exception rationale: mutates daemon-owned async run state and cancellation lifecycle
  - removal path: move cancellation authority to ownership-first runtime host surface with bounded terminality retained (`530` seams)
  - test anchors:
    - `tests/test_cli_async_commands.py::test_run_cancel_requires_rpc_enabled`
    - `tests/test_daemon_run_store.py::test_cancel_protocol_shape_parity_across_cancel_flag`
