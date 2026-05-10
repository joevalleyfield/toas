# 501 Shell Streaming Run Subprocess Phase Split And Coverage

## Objective
Further decompose `src/toas/tools_cluster/shell_streaming.py::run_streaming_subprocess` into explicit phases and raise direct coverage on the new module.

## Why
`run_streaming_subprocess` is now a top hotspot (~102 lines) with comparatively low coverage (~71%) after the 497 extraction.

## Scope
- split process setup, read-loop policy, timeout/drain, and final assembly into focused helpers
- preserve newline/size/latency flush semantics and debug logging behavior
- add focused tests to cover timeout, drain, and read-loop branches

## Done When
- `run_streaming_subprocess` is materially slimmer with explicit helper seams
- `tests/test_tools_shell_ops.py` or new focused module tests cover extracted branches
- targeted parity and full suite pass

## Related
- `400` decomposition umbrella
- `497` shell-ops split closure
- `483` streaming behavior fix baseline

## Progress
- extracted explicit streaming subprocess phases from `run_streaming_subprocess`:
  - `_spawn_streaming_process`
  - `_emit_stdout_chunk`
  - `_reader_thread_target`
  - `_wait_for_process`
  - `_drain_if_reader_alive`
  - `_completed_process`
- preserved newline/size/latency flush semantics and timeout/drain behavior while slimming facade flow
- validation:
  - `uv run pytest tests/test_shell_streaming.py -q --no-cov`
  - `uv run pytest tests/test_tools_shell_ops.py -q --no-cov`
