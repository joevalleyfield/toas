# Portable Synchronous Host Pipe Reads

Filed as: 261015-sync-host-pipe-portability
FKA:
AKA: Windows HostClient select failure; bounded host response timeout
Legacy index:

keywords: transport, hardening, historical, compatibility, windows, ipc

Parent: `261015-windows-compatibility-restoration`

Status: CLOSED 2026-10-15; synchronous host requests work over native Windows pipes

## Failure and Repair

`cli_demo_async_client.HostClient` used `select()` on subprocess stdout, raising
WinError 10038 on Windows. Its process-exit shortcut could also discard final
stdout that had not yet been read. On timeout, an unconditional stderr read from
a live child could block and defeat the configured response deadline.

Add a runtime-owned `PipeReader`: one daemon reader thread per stdout pipe,
deadline-aware queue reads, explicit EOF and error delivery. Use it for the
synchronous client on both Windows and POSIX; drain queued bytes through EOF
instead of treating process exit as proof the pipe has already been consumed.
Use a monotonic deadline and collect blocking stderr diagnostics only after
process exit. The owning subprocess retains pipe/shutdown ownership; the reader
exits when the pipe reaches EOF or reports an OS read error.

The request/response protocol, delimiters, correlation IDs, and async client
behavior remain unchanged.

## Verification

- The four baseline real-process `HostClient` request tests now pass on Windows.
- Added real-process regressions for a silent live child's bounded request
  timeout and draining final stdout after process exit.
- Reader tests cover byte ordering, persistent EOF, an idle deadline, and read
  error propagation; existing frame/diagnostic tests use an injected reader.
- **106 passed** across `tests/test_runtime_pipe_reader.py` and
  `tests/test_cli_demo_async_client.py`.
- Targeted coverage for `toas.runtime.pipe_reader` and
  `toas.cli_demo_async_client`: **100%**, 466 statements, zero missing files.
- Ruff passes for all changed Python files.
- Actual `_start_host` running `python -m toas host serve --stdio-json` in a
  temporary directory: `HostClient.request('status', ...)` returned `ok: true`,
  the requested correlation ID, and a valid status envelope; process and pipes
  were cleaned up afterward.

The remaining LLM stand-in integration failures use `AsyncHostClient`, so they
are not claimed resolved here. Full-suite and POSIX-host verification remain
master-task gates.

Follow-up 2026-10-15: full mypy inspection during shell runtime selection found
that Popen exposes `IO[bytes]`, wider than the reader's original `BinaryIO`
annotation. Corrected the annotation without changing behavior. Pipe/client and
explicit-runtime matrix recheck: 110 passed; mypy returned to the six baseline
journal-lock errors.
