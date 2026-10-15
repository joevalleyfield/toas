# Host Stream Renewal and Cancellation Terminality

Filed as: 261015-host-stream-cancellation
FKA:
AKA: Windows async stand-in timeouts; cancelled worker reported failed
Legacy index:

keywords: runtime, hardening, historical, compatibility, windows, cancel, stream

Parent: `261015-windows-compatibility-restoration`

Status: CLOSED 2026-10-15; repair bounded-subscription test observation and typed worker cancellation

## Evidence and Causes

The first cancellation test timed out waiting for an answer delta. Durable history
contained a complete model answer. Host wire diagnostics showed a normal
`push_complete` with `complete=false`, `reason=idle_timeout`, after the production
750 ms cap, before model-client startup completed on Windows. The test kept
waiting on that closed subscription. Raising the cap experimentally confirmed
the cause; no production deadline was changed in the repair.

The stand-in tests now renew normal idle/request-deadline completions using the
observer's last sequence. A regression checks the resumed cursor, unique request
ID, delivery of final completion, and preservation of upstream error frames.
Use `os.pathsep` when constructing the subprocess PYTHONPATH.

The timing-based cancellation scenario previously accepted any subscription
completion as terminal cancellation. Renewing subscriptions exposed that the
first cancel intentionally records observation intent while tokens continue.
The test now explicitly escalates and requires a true cancelled completion,
retaining its relative stream-duration bound and no-success assertions.

That stricter test exposed a production bug: `_run_in_process_worker` classified
`_RunCancelledBrokenPipe` as a generic failure. Add a typed cancellation handler
consistent with the subprocess wait path: status cancelled, return code 130,
terminal finalization, no error event. A unit regression reproduced the failed
classification before the fix. The generic exception path still reports failure.

## Verification

- Four baseline LLM stand-in failures addressed: answer cancellation, timed
  cancellation, reasoning-only EOF, and reasoning cancellation.
- **101 passed, 3 deselected** across daemon runner, activity store API, host
  stream bridge, and real-host stand-in modules using `-o addopts= -q --tb=short`.
- Explicitly deselected existing failures: POSIX reader-stall simulation,
  explicit-shell provisional projection, and user-lane tool pacing. These remain
  master-task work; no permanent skips were added.
- Worker targeted coverage: **100%**, 460 statements, 61 passed / 1 deselected
  (the known POSIX simulation failure), zero missing files.
- Changed-file Ruff passes.
- Inspected actual temporary real-host durable history: final run record is
  `cancelled`, with detail `cancel escalated by operator; close sent immediately`,
  rather than a failed traceback. Real host tests also assert stream truncation,
  cancelled completion, and terminal event statuses.

No production async-client protocol or deadline changes were needed. Complete
Windows suite and POSIX-host execution remain master-task closure gates.
