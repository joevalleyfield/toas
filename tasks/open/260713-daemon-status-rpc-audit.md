# Daemon status failure and RPC daemon audit

Filed as: 260713-daemon-status-rpc-audit
FKA:
AKA: toas daemon status TypeError; RPC daemon lifecycle audit; daemon facade wiring
Legacy index:

keywords: runtime, hardening, active, correctness, transport, ipc

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
