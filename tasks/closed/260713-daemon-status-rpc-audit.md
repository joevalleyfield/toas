# Daemon status failure and RPC daemon audit

Filed as: 260713-daemon-status-rpc-audit
FKA:
AKA: toas daemon status TypeError; RPC daemon lifecycle audit; daemon facade wiring
Legacy index:

keywords: runtime, hardening, historical, correctness, transport, ipc

## Context

A cloud-container smoke test found that `uv run toas daemon status` raises a
`TypeError` instead of reporting daemon state. The traceback shows the CLI
runtime daemon command reaching `toas.daemon.server_lifecycle.status()` directly,
which requires injected lifecycle ports, rather than the public daemon facade
that supplies those ports.

The same surface is part of the documented CLI and routine development posture,
so the immediate failure should be fixed before deeper daemon/RPC confidence is
claimed.

## Scope

- Restore `toas daemon status` so the CLI calls a port-wired daemon lifecycle
  facade and returns the documented running/stopped status line.
- Add a focused regression test that exercises the real CLI wiring enough to
  catch the facade-vs-implementation mismatch.
- Audit nearby daemon/RPC CLI entry points for the same class of accidental
  low-level implementation wiring.
- Split follow-ons if the audit finds broader transport or lifecycle contract
  work beyond the status failure.

## Acceptance

- `uv run toas daemon status` exits cleanly in a container with no daemon running
  and prints a stopped/running status line.
- A targeted test fails on the current broken wiring and passes after the fix.
- The task records whether the RPC daemon audit found no further issues or names
  follow-on tasks for any larger seams.

## Progress

- 2026-07-13: Fixed the immediate `toas daemon status` failure by routing the
  CLI daemon command through the public `toas.daemon` facade instead of the
  injected-port `server_lifecycle` implementation module.
- 2026-07-13: Focused audit checked remaining `server_lifecycle` references;
  production CLI wiring now uses the facade, while direct `server_lifecycle`
  imports are confined to lifecycle implementation/facade assembly and dedicated
  lifecycle tests.

## Follow-up disposition

No broader RPC daemon follow-on was opened in this slice. The next audit should
start from daemon start/stop/status parity under RPC mode if future smoke tests
find transport-specific behavior rather than facade wiring drift.

## Closure evidence

- 2026-07-14: Re-audited production references. `src/toas/cli.py` routes daemon
  commands through the public `toas.daemon` facade; remaining
  `server_lifecycle` references are limited to facade assembly and lifecycle
  implementation/tests.
- 2026-07-14: Verified the lifecycle command seam with 23 focused tests covering
  CLI start/stop/status, runtime command handling, and daemon facade delegation.
- 2026-07-14: Verified `TOAS_RPC_MODE=off toas daemon status` and
  `TOAS_RPC_MODE=on toas daemon status`; both exit cleanly and report the daemon
  as stopped when no daemon is running.
- 2026-07-14: `ruff check` and `mypy` pass for the audited CLI/runtime/daemon
  surface.

## Status

Closed. The documented daemon status failure is fixed, the facade-vs-
implementation wiring regression is covered, and this audit found no further
RPC daemon lifecycle issue in scope.
