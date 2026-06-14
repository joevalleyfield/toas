# 548 Stdlib Logging Migration For Runtime Diagnostics
keywords: runtime, migration, active, maintainability, logging, diagnostics, observability

## Goal
Adopt Python standard library `logging` as the primary diagnostics surface for runtime/host debug emission, rooted in `OperatorConfig` so the config precedence ladder governs log level and output destination.

## Why
Current diagnostics are fragmented across ad hoc file/env pathways (`TOAS_DAEMON_STREAM_DEBUG`, `TOAS_RPC_DEBUG_LOG`, `TOAS_HOST_STREAM_DEBUG`, six `TOAS_DEBUG_*` vars in `llm.py`). A unified `logging` foundation consolidates routing, respects the config precedence contract, and makes debug output available without hunting for per-module env vars.

## Decisions

- `DiagnosticsPolicy` lives in `OperatorConfig` (`config.py`), parallel to `RuntimePolicy` and `ShellPolicy`. Fields: `log_level: str = "WARNING"`, `log_file: str | None = None`.
- Bootstrap (`configure_logging`) is called after config is loaded, before any runtime work. Bootstrap failures are not caught — they propagate as exceptions.
- Per-module loggers use `logging.getLogger(__name__)`. No new env-var channels.
- Existing `TOAS_*_DEBUG` env vars are deprecated in place during this pass; their reading code is removed as each module is migrated. Operators switch to `diagnostics.log_level = "DEBUG"` in `toas.toml`.
- `model_backend_lifecycle.py` already uses `logging.getLogger(__name__)` (seeded in the backend lifecycle refactor).

## Current Debug Channels

| Channel | Env var(s) | Location | Shape |
|---|---|---|---|
| Daemon RPC request log | `TOAS_RPC_DEBUG_LOG` | `daemon/facade_helpers.debug_log` | string → append to file |
| Async activity store stream debug | `TOAS_DAEMON_STREAM_DEBUG`, `TOAS_DAEMON_STREAM_DEBUG_LOG` | `runtime/async_activity_store_impl._debug_log` | dict → jsonl |
| Session host stream debug | `TOAS_HOST_STREAM_DEBUG`, `TOAS_HOST_STREAM_DEBUG_LOG` | `runtime/session_host_process._host_debug_log` | dict → jsonl |
| LLM stream debug (6 channels) | `TOAS_DEBUG_PROMPT_PROGRESS[_FILE]`, `TOAS_DEBUG_REASONING[_FILE]`, `TOAS_DEBUG_STREAM_RAW[_FILE]`, `TOAS_DEBUG_STREAM_REQUEST[_FILE]`, `TOAS_DEBUG_STREAM_EDGE[_FILE]`, `TOAS_DEBUG_STREAM_LIFECYCLE[_FILE]` | `llm.py` | mixed → optional per-channel files |
| Frontier debug | `TOAS_DEBUG_FRONTIER[_FILE]` | `runtime/step_runtime.py`, `step_context_runtime.py` | unknown shape |

## Implementation Path

1. Add `DiagnosticsPolicy` to `config.py`; wire into `OperatorConfig` and `apply_overrides`. Add `src/toas/runtime/logging_bootstrap.py` with `configure_logging(policy: DiagnosticsPolicy) -> None` (calls `logging.basicConfig`, no try/except). Call from daemon startup (`server_lifecycle.main`) and CLI entry (`cli.dispatch`). Tests: config round-trip, bootstrap sets level/handler correctly.

2. Migrate daemon RPC request channel: replace `daemon/facade_helpers.debug_log` (file-append via `TOAS_RPC_DEBUG_LOG`) and the injected `debug_log_fn` threading through `request_dispatch`, `request_dispatch_adapter`, `local_request_ops`, and `daemon/__init__.py` with module-level `logger = logging.getLogger(__name__)` in each module that currently receives the injected fn. Remove the injection parameter from the relevant call sites after verifying no other callers depend on it. Remove `TOAS_RPC_DEBUG_LOG` reading.

3. Migrate session host: replace `session_host_process._host_debug_log` / `_host_debug_log_path` / `_host_debug_enabled` with `logger.debug(...)` at the call sites. Structured dict fields become `logger.debug("%s", json.dumps({...}))`. Remove `TOAS_HOST_STREAM_DEBUG[_LOG]` reading.

4. Migrate async activity store: replace `async_activity_store_impl._debug_log` / `_debug_log_safe` / `_debug_enabled` with `logger.debug(...)`. The re-export of `_debug_log` from `async_activity_store_api` (imported by `async_step_runtime_worker`) is removed; worker uses its own `getLogger(__name__)`. Remove `TOAS_DAEMON_STREAM_DEBUG[_LOG]` reading.

5. Migrate `llm.py` six-channel debug: consolidate into `logger.debug(...)` at the relevant emission points. Remove the six `TOAS_DEBUG_*[_FILE]` env var reads. (This is the largest surface — may be its own commit.)

6. Migrate frontier debug in `step_runtime.py` / `step_context_runtime.py`. Remove `TOAS_DEBUG_FRONTIER[_FILE]` reading.

## Compatibility Requirements

- `diagnostics.log_level` and `diagnostics.log_file` are valid dotted-key config keys settable via `/config set`.
- Default behavior (no config, no env): no output, matching current default (all debug channels off).
- When `log_level = "DEBUG"` and `log_file` is set, debug output goes to that file. When `log_file` is absent, output goes to stderr.
- Existing per-module `TOAS_*_DEBUG` env vars silently stop working once their reading code is removed (deprecated, not replaced).

## Next Actions

- [x] Step 1: DiagnosticsPolicy + configure_logging bootstrap — `DiagnosticsPolicy(log_level="WARNING", log_file=None)` added to `config.py` and wired into `OperatorConfig`, `apply_overrides` classes dict, and `config_overrides.py`. `runtime/logging_bootstrap.py` adds `configure_logging(policy)` with no try/except. Called from `cli.main()` and `daemon/__init__.serve_forever` via lazy import. Tests: `test_config.py` (5 new) + `test_logging_bootstrap.py` (6 tests).
- [x] Step 2: Daemon RPC request channel — `debug_log` injection removed from `request_dispatch.safe_op_call`, `handle_request_dispatch`, `request_dispatch_adapter` wrappers, `local_request_ops.handle_default_op`, and both builders in `request_handler_assembly`. Module-level `logger = logging.getLogger(__name__)` added to `request_dispatch` and `local_request_ops`. `debug_log` fn deleted from `request_handler_assembly` and `daemon/facade_helpers`. `_debug_log` wrapper and import removed from `daemon/__init__`. `TOAS_RPC_DEBUG_LOG` reading gone. Tests updated to use `caplog` for log-assertion cases; `debug_log=` kwargs removed throughout.
- [x] Step 3: Session host — `_host_debug_log`/`_host_debug_enabled`/`_host_debug_log_path` replaced with `logger = logging.getLogger(__name__)` + `logger.debug("%s", json.dumps({...}))`. `TOAS_HOST_STREAM_DEBUG[_LOG]` reading removed. `stream_pacing_summary` updated to handle stdlib log-line prefix (JSON extracted via `text.find("{")`) and to count emit records without requiring a `ts` field (legacy raw-jsonl had it; stdlib format does not). Tests updated to `caplog` pattern.
- [x] Step 4: Async activity store — `_debug_enabled`/`_debug_log`/`_debug_log_safe`/`_DEBUG_LOG_GUARD` replaced with `logger = logging.getLogger(__name__)` in `async_activity_store_impl`. `_debug_log` re-export removed from `async_activity_store_api` and its `__all__`. `async_step_runtime_worker` gains its own `logger` + local `_debug_log` wrapper instead of importing from api. `TOAS_DAEMON_STREAM_DEBUG[_LOG]` reading removed. Reentrancy guard dropped (stdlib handles reentrancy). Snapshot-isolation test rewired to patch `_capture_watch_baseline` instead of `_debug_log`. Env-var tests replaced with `caplog` pattern.
- [x] Step 5: llm.py six-channel debug — six `_append_*` file-write functions and six `TOAS_DEBUG_*[_FILE]` env var reads removed. Six `debug_*` bool locals removed from `_stream_backend_response`. `debug_prompt_progress`/`debug_reasoning` params removed from `_handle_stream_progress` and `_process_stream_chunk`. All debug emission points converted to `logger.isEnabledFor(logging.DEBUG)` guards with `logger.debug(...)`. `_append_raw_stream_chunk_debug` consolidated into `_serialize_raw_stream_chunk` (pure function, no I/O). `pathlib.Path` import removed. Tests: env-var/file tests replaced with `caplog` tests; `except: pass` suppression tests deleted (no longer applicable); `_serialize_raw_stream_chunk` covers the three serialization branches.
- [x] Step 6: Frontier debug — `_frontier_debug_enabled`/`_append_frontier_debug` in `step_runtime.py` and `frontier_debug_enabled`/`append_frontier_debug` in `step_context_runtime.py` replaced with `logger = logging.getLogger(__name__)` + `logger.debug("%s", json.dumps(record))`. `_append_frontier_debug` alias removed from `step_context_runtime` bottom and dead `append_frontier_debug` import removed from `cli_session_commands`. `TOAS_DEBUG_FRONTIER[_FILE]` reading removed. Three behavioral-invariant tests in `test_cli.py` migrated from env-var + file-read pattern to `caplog.at_level(logging.DEBUG, logger="toas.runtime.step_runtime")` + JSON parsing from `r.message`.

## Related
- `525`
- `541`
- `542`
- `543` (closed)
- Backend lifecycle refactor (first `logging.getLogger(__name__)` adoption)
