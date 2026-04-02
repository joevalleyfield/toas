## Goal

Introduce `toasd` lifecycle and route `toas step` through RPC when daemon is available, with safe fallback to current local execution behavior.

## Scope

- add daemon process entrypoint and lifecycle controls (`start/stop/status`)
- implement RPC `step` operation in daemon
- make `toas step` act as RPC client when daemon is reachable
- preserve fallback path when daemon is unavailable

## Intended Inputs

- transport adapters from `221`/`222`
- existing `run_step` behavior and stdout contract
- existing event-log and tool-record semantics

## Intended Outputs

- working daemon mode for `step`
- CLI client path that prefers daemon and falls back safely
- tests proving behavior parity with current non-daemon `step`

## Constraints

- `toas step` user-facing output contract must not change
- daemon path must preserve existing append/record semantics
- fallback path must be explicit and reliable

## Non-Goals

- no Vim direct channel yet
- no full RPC parity for all commands yet

## Done When

- `toas step` works through daemon RPC and through local fallback
- stdout and history behavior match current contract
- lifecycle commands are documented and tested
