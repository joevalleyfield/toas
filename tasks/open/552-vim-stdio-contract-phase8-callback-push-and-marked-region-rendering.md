# 552 Vim Stdio Contract Phase 8: Callback Push + Marked Region Rendering

## Goal
Replace poll-loop channel reads in the dedicated stdio contract plugin with callback-driven push intake, and render streamed output only within explicit marked regions.

## Why
Phase-7 poll-loop path still exhibits sporadic prefix-truncated parse errors and interaction-coupled rendering artifacts under burst + slow timing. This violates strict greedy NDJSON framing and clean async interaction expectations.

## Contract
- channel intake is callback-driven (`out_cb`, raw mode)
- callback appends bytes into a single RX accumulator
- parser remains strict greedy NDJSON (`rx += chunk`; split only on `\n`; incomplete tail retained)
- no skipping/resync heuristics for partial frames
- timer owns bounded frame processing and bounded render work only
- render target is explicit marked region (not `$` append semantics)
- startup command returns immediately; no sync wait for completion

## Scope
In scope:
- `vim/plugin/toas_stdio_contract.vim` intake + render model shift
- synthetic host scenarios remain configurable (`fast`, `sim_slow`, `slow`)
- driver updates for phase-8 naming and behavior checks
- focused tests asserting:
  - no parse errors under canonical burst/slow runs
  - terminal completion observed
  - marked region integrity under user cursor movement

Out of scope:
- `toas.vim` production plugin migration (separate follow-on)

## Done When
- callback path replaces polling as primary intake in contract plugin
- parse-prefix truncation failures are not reproducible in burst+slow contract runs
- interaction remains responsive under sustained stream load
- phase-8 tests pass

## Related
- `551`
- `542`
- `docs/protocols/vim-host-stdio.md`

## Progress
- 2026-05-23: task opened; phase-8 pivot approved.
