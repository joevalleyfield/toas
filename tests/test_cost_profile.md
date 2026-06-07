# Test Cost Profile

## Timing Workflow

Full-suite parallel (wall-clock):

```bash
uv run pytest -n 14 -q --no-cov --durations=40 --durations-min=0
```

Serial per-test precision:

```bash
uv run pytest -q --no-cov --durations=40 --durations-min=0.5
```

JUnit aggregation:

```bash
uv run pytest -n 14 -q --no-cov --junitxml=/tmp/toas-pytest-times.xml
```

## Snapshot (2026-06-07)

Wall time: ~22.7s (parallel), ~95s (serial). 1979 passed.

## Test Classification

### Justified Slow (timing, stdio, subprocess contracts)

These tests genuinely validate slow I/O, cancellation, or subprocess contracts. They stay as-is.

| Test | Duration | Why slow |
|------|----------|----------|
| `test_host_stdio_user_lane_tool_pacing_shape` | 19.1s | Validates real-time stdio pacing with 30s timeout |
| `test_vim_driver_phase2_async_smoke` | 11.3s | Real Vim process lifecycle |
| `test_subscribe_timeout_returns_3` | 2.0s | Validates timeout behavior (2s sleep) |
| `test_host_stdio_with_llm_standin_cancel_stream_shape` | 0.8s | Real stdio cancellation contract |
| `test_host_stdio_with_llm_standin_cancel_stream_shape_time_ally` | 0.8s | Real stdio timing contract |
| `test_local_async_lifecycle_contract_step_watch_cancel` | 0.5s | Real async lifecycle with cancellation |
| `test_contract_plugin_burst` | 0.55s | Vim plugin contract |
| `test_integration_subprocess_path_emits_tool_progress_and_terminal_event` | 1.05s | Real subprocess lifecycle (daemon) |
| `test_managed_backend_start_health_fail` | 1.05s | Real subprocess (managed backend) |
| `test_run_streaming_subprocess_collects_stdout` | 1.03s | Validates real streaming subprocess I/O |

### Justified Slow (runtime session subscribe)

The session host process subscribe tests use real async I/O with 0.75s timeout for each:

| Test | Duration | Why slow |
|------|----------|----------|
| `test_handle_stream_subscribe_request_forwards_resume_cursor_fields` | 0.75s | Async I/O timeout |
| `test_handle_stream_subscribe_request_ignores_watch_chunk_without_semantic_events` | 0.75s | Async I/O timeout |
| `test_handle_stream_subscribe_request_since_seq_never_regresses_from_upstream_next_seq` | 0.75s | Async I/O timeout |
| `test_handle_stream_subscribe_request_defaults_follow_mode_when_absent` | 0.75s | Async I/O timeout |
| `test_handle_stream_subscribe_request_times_out_as_incomplete_when_no_terminal` | 0.75s | Async I/O timeout |
| `test_handle_stream_subscribe_request_sets_incomplete_when_no_terminal_event` | 0.75s | Async I/O timeout |

### Remediated: Shell routing tests (~1s each, ~7 in test_tools.py, ~12 in test_step.py)

These tests were validating **command routing/parsing** logic, not subprocess execution.
The subprocess was just a vehicle to prove the routing worked.

**Remediation approach**: Mock `run_subprocess` at the `shell_ops` seam so the test
validates the argv construction, cwd, and env without forking a real process.

Tests in `test_tools.py`:
- `test_user_shell_auto_executes_with_shell_when_command_needs_shell`
- `test_user_shell_needs_shell_hint_preserves_escaped_grouping`
- `test_user_shell_allows_unrestricted_command`
- `test_user_shell_allows_empty_string_argument`
- `test_user_shell_allows_cwd_outside_workspace`
- `test_execute_shell_call_user_command_with_shell_operator_without_argv`
- `test_execute_shell_call_user_accepts_command_without_argv`

Tests in `test_step.py`:
- `test_user_tail_shell_is_unbounded_while_callable_shell_is_bounded`
- `test_user_callable_shell_with_sh_c_uses_unbounded_user_shell_lane`
- `test_user_callable_shell_with_tool_name_shape_uses_unbounded_user_shell_lane`
- `test_user_shell_script_plan_executes_in_user_context`
- `test_user_tail_yaml_multiline_command_executes`
- `test_assistant_shell_respects_durable_shell_scope_grant_events`
- `test_assistant_shell_respects_config_shell_allowed_commands`
- `test_callable_executes_bounded_shell_tool`
- `test_callable_shell_uses_command_cwd_when_args_omit_cwd`
- `test_user_loose_command_yaml_executes_without_canonicalization`
- `test_user_shell_respects_transcript_env_modifiers`
- `test_user_tail_with_shell_shorthand_executes_result_without_generation`

Tests in `test_tools_shell_ops.py`:
- `test_run_user_shell_needs_shell_hint_and_command_mode`
- `test_execute_shell_call_user_command_without_argv`

Tests in `test_cli.py`:
- `test_run_step_local_behavior_e2e_consequence_attaches_from_rewritten_tail_matrix[...]`
- `test_run_step_streaming_callable_result_includes_user_and_result_markers`
- `test_run_step_uses_persisted_command_context_for_user_shell`

**Status**: Done.

### Remediation Approach

Created `fake_shell_subprocess` fixture in `tests/conftest.py` that patches
`toas.tools_cluster.shell_ops.run_subprocess` with a side_effect function
that echoes argv/cwd back into the result dict. Tests validate the command
routing (argv construction, cwd resolution, env passing) without forking
a real process.

For tests that check actual subprocess output (e.g., stdout content),
assertions were adjusted to validate the routing semantics instead:
- argv correctness instead of stdout content
- cwd through mock call kwargs instead of stdout
- env through mock call kwargs instead of stdout

The remaining ~1s tests in the cluster are genuinely testing subprocess
I/O (e.g., `test_run_streaming_subprocess_collects_stdout` validates
real streaming I/O, `test_integration_subprocess_path_emits_tool_progress`
validates real subprocess lifecycle).
