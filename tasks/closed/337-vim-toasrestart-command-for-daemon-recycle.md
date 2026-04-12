# 337: Add `:ToasRestart` command in Vim

## Summary
Add a Vim command to restart the TOAS daemon from the editor so dev code changes can be picked up without leaving Vim.

## Motivation
The current Vim plugin supports step/watch/cancel but not daemon lifecycle control. During development, restarting the daemon is a frequent operation.

## Proposed Behavior
- New command: `:ToasRestart`
- Sequence:
  - clear cached RPC channel state in plugin
  - run `toas daemon stop` (best effort)
  - run `toas daemon start`
  - optionally probe/show status notice
- No default keybinding yet.

## Acceptance Criteria
- Running `:ToasRestart` from Vim restarts daemon in normal dev workflows.
- If daemon is not running, command still leaves daemon running (start-like behavior).
- Vim plugin channel state is refreshed so subsequent TOAS commands work without manual reset.
- UX does not block on extra prompt noise beyond normal command output.

## Outcome

Implemented in current pass:
- added `:ToasRestart` command in `vim/plugin/toas.vim`
- restart flow:
  - clear plugin RPC/watch state and close cached channel
  - run `toas daemon stop` as best-effort
  - run `toas daemon start`
  - run `toas daemon status` and surface notice text
- stop failure is tolerated; start failure raises explicit error
