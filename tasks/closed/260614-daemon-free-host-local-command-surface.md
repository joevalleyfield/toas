Filed as: 260614-daemon-free-host-local-command-surface
FKA:
AKA:
Legacy index:

keywords: runtime, decomp, historical, cli, host, local-command-surface, daemon-free, 470, 400, 525

# Daemon-Free Host Local Command Surface

## Current Reality

`525` has moved primary host request handling out of daemon package identity, but the stdio host still builds its local request runtime using `toas.cli` as a broad compatibility object. `toas.cli` remains a large CLI facade with daemon compatibility exports, presentation wrappers, and dispatch behavior that are not all relevant to the host-local request path.

## Desired Reality

The stdio host request handler should build against a daemon-free local command surface that exposes only the local command functions and step dependencies needed by runtime request handling.

## Gap Analysis

`runtime.local_request_ops` expects a `cli_module`-shaped object for local `step`, `heads`, `history`, `transcript`, `llm_input`, `prompt`, `prompts`, `rebuild`, and `intents`. The current host path satisfies that by importing `toas.cli`, which keeps 525 balanced on a broad compatibility facade instead of a narrow runtime/CLI seam.

## Known Facts

- `470` is closed as the original operator API seam migration.
- `400` remains the active decomposition umbrella for CLI facade thinning.
- `525` was the active runtime ownership umbrella that benefited from this seam and is now closed.
- `cli_session_commands.run_step_local` accepts an explicit `cli_mod` dependency object.

## Next Actions

- [x] Add a daemon-free local command module for request-handler assembly.
- [x] Switch `cli_host_commands._host_request_handler` to build its runtime from that module instead of `toas.cli`.
- [x] Add/adjust tests that assert the host request handler does not import `toas.daemon` or `toas.cli`.

## Progress

- 2026-06-14: Closed after adding `cli_local_commands.py` as the daemon-free local command dependency surface, switching stdio host request assembly away from `toas.cli`, and validating the host handler no longer imports `toas.cli` or `toas.daemon`.
