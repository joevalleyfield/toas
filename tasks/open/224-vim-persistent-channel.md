## Goal

Enable Vim/Neovim to talk directly to `toasd` over a persistent channel so stepping does not spawn a `toas` process per invocation.

## Scope

- add a minimal Vim-side integration for persistent daemon connection
- expose a Vim command for step requests over the persistent channel
- append returned blocks into buffer in a way compatible with current workflow
- include reconnect behavior when daemon/channel is unavailable

## Intended Inputs

- daemon RPC operation from `223`
- chosen transport endpoint contract
- current Vim interaction pattern (`:r !toas step`) as baseline

## Intended Outputs

- working Vim command (or plugin script) for direct channel `step`
- documentation for setup and usage
- tests or scripted validation for round-trip behavior

## Constraints

- no per-step `toas` process spawn in the direct-channel path
- keep transcript/stdout insertion semantics predictable
- keep CLI path available as fallback

## Non-Goals

- no broad Vim UI feature set beyond step channel integration
- no replacement of CLI workflows outside Vim

## Done When

- Vim can execute `step` via persistent daemon channel
- channel path is measurably free of per-step CLI spawn
- fallback path remains available and documented
