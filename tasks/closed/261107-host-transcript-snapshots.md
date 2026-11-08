Filed as: 261107-host-transcript-snapshots
FKA:
AKA: Pyzo Step Here; async session_text; host snapshot capability
Legacy index:

keywords: runtime, host, protocol, editor, snapshots

# Async host transcript snapshots

## Status

Closed on 2026-11-07. Requested through Pyzo integration task 046. Full-suite
closure verified after resolving developer home config leakage in
`261107-test-suite-user-config-isolation`.

## Intent

Expose the existing operator API session_text input through async host stepping,
so an editor can execute a captured transcript prefix using the original session
path while retaining its complete saved file and editable suffix.

## Contract

- Async step payloads optionally accept session_text as a string, including an
  empty string. Omission preserves file-based input. Other supplied types fail
  validation before execution.
- Host status advertises step_async.session_text in capabilities. Clients check
  support before submitting snapshots because older hosts may ignore new fields.
- Forward the snapshot to the existing bounded operator in both async modes.
  Keep session_path for identity and ordinary runtime semantics.
- Preserve history, cancellation, streamed projections, and ordinary callers.

## Acceptance

Validate absent, empty, Unicode, multiline and invalid inputs. Exercise actual
host snapshot execution with a saved suffix containing a different action and
prove that only the selected prefix runs, the saved file remains intact, and
history retains the original transcript identity. Run the required checks and
inspect the actual returned projection. Record evidence before closure.

## Implementation and evidence

- Added optional session_text validation, preserving empty strings and rejecting
  supplied non-strings. Host status advertises step_async.session_text.
- The async start options retain the snapshot and forward it to the existing
  bounded operator together with the original session path. No new transcript
  execution or history engine is introduced.
- Focused host/worker validation passes, 91 tests. Real stdio host tests cover
  cold and cold_asyncio workers with a saved file containing an action that must
  not run. The returned canonical projection and durable history contain the
  snapshot action, the saved file stays unchanged, and the disk action is absent.
- Pyzo integration checks pass through the installed editable TOAS host. The
  native Cocoa probe reports Step Here success, preserved suffix and disk input,
  normal Save, successor continuation, and cancellation before Quit. A repaired
  prefix creates a new user event with a distinct id and the original parent,
  preserving the original history branch.
- Full TOAS units reach 100.00% coverage over 25,981 statements, with 3,880 passed,
  nine skipped and 17 deselected. The baseline failures previously observed were
  isolated to developer home config leakage (`~/.config/toas/config.toml`), resolved
  by `261107-test-suite-user-config-isolation`.
- Acceptance has 17 passed.
- Ruff passes and mypy passes across all 164 source files.

## Validation commands

Run through the local uvt runner when using the developer environment.

```sh
uv run pytest tests/test_daemon_request_contract.py tests/test_daemon_handlers.py tests/test_runtime_host_snapshots.py tests/test_daemon_async_runner.py --no-cov -q
./scripts/check.sh
uv run pytest tests/acceptance -m acceptance --no-cov -q
uv run ruff check src tests
uv run mypy
```
