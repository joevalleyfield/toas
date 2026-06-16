Filed as: 260614-retire-local-suffix-naming-inversion
FKA:
AKA: _local suffix; naming inversion; run_step_local; local_request_ops; cli_local_commands
Legacy index:

keywords: runtime, refactor, active, naming, cli, local, daemon, smell, conventions

# Retire Local Suffix Naming Inversion

## Problem

The `_local` suffix was introduced when the daemon was the primary execution path and local execution was the fallback. It marked the fallback variant.

Since the local-first flip (T534/T540), local execution is the default and the daemon is optional. The naming now encodes the old mental model: the primary implementation carries an apologetic suffix while the thin RPC-routing wrapper has the clean name.

The suffix has also spread into module names (`cli_local_commands`, `local_request_ops`) where it means "not-daemon-facing" rather than "fallback," creating two different semantics for the same qualifier.

## Desired Reality

The qualifier belongs on the variant, not the default. Primary implementations should have clean names. RPC-augmented wrappers, if they survive at all, should carry a suffix or be inlined.

## Scope

- `[ ]` Audit and classify all uses of `_local` as a suffix or module name component
- `[ ]` Rename/refactor primary implementations to drop the suffix or use `_direct`
- `[ ]` Update module names where the suffix has leaked
- `[ ]` Update all callers and tests
- `[ ]` Verify build, test suite, and 100% statement coverage

## Implementation Plan details

### 1. Rename Modules:
- `src/toas/cli_local_commands.py` -> `src/toas/cli_direct_commands.py`
- `src/toas/cli_local_surface_commands.py` -> `src/toas/cli_surface_commands.py`
- `src/toas/runtime/async_local_start_adapter.py` -> `src/toas/runtime/async_direct_start_adapter.py`
- `src/toas/runtime/local_request_ops.py` -> `src/toas/runtime/direct_request_ops.py`
- `src/toas/runtime/local_request_handler_edges.py` -> `src/toas/runtime/direct_request_handler_edges.py`
- `src/toas/daemon/facade_local_ops.py` -> `src/toas/daemon/facade_direct_ops.py`

### 2. Rename Test Modules:
- `tests/test_cli_local_commands.py` -> `tests/test_cli_direct_commands.py`
- `tests/test_cli_local_surface_commands.py` -> `tests/test_cli_surface_commands.py`
- `tests/test_daemon_local_ops.py` -> `tests/test_daemon_direct_ops.py`
- `tests/test_runtime_local_request_handler_edges.py` -> `tests/test_runtime_direct_request_handler_edges.py`

### 3. Rename Internal functions/symbols:
- Functions in `cli_direct_commands.py` and `cli_surface_commands.py` (e.g. `run_heads_local` -> `run_heads_direct`).
- Helpers in `cli_async_commands.py` (`_start_async_step_local` -> `_start_async_step_direct`, etc.).
- `build_local_request_handler_parts` -> `build_direct_request_handler_parts` in `direct_request_handler_edges.py`.
- `build_local_request_handler_runtime` -> `build_direct_request_handler_runtime` in `request_handler_assembly.py`.

## Coordination Note

This task belongs near the architecture follow-through tree.
The `_local` naming inversion is a symptom of old daemon-primary migration history leaking into current names.

## Done When

No production symbol uses `_local` to mean "primary implementation" or "default path."
All tests pass and coverage is maintained at 100%.
