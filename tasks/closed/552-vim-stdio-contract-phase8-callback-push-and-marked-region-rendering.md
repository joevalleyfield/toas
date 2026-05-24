# 552 Vim Stdio Contract Phase Slice: Callback Push + Marked Region Rendering

## Goal
Replace poll-loop channel reads in the dedicated stdio contract plugin with callback-driven push intake, and render streamed output only within explicit marked regions.

## Why
This task captures a contributing experiment slice that informed the broader architecture shift from daemon/RPC/polling to session-host/stdio/subscribe-receive in Vim.
Pre-slice poll-loop behavior exhibited sporadic prefix-truncated parse errors and interaction-coupled rendering artifacts under burst + slow timing.

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
- serving as the umbrella narrative for the full Vim transport shift (tracked in `553`)

## Done When
- callback path replaces polling as primary intake in contract plugin
- parse-prefix truncation failures are not reproducible in burst+slow contract runs
- interaction remains responsive under sustained stream load
- phase-8 tests pass

## Related
- `551`
- `542`
- `553`
- `docs/protocols/vim-host-stdio.md`

## Progress
- 2026-05-23: task opened; phase-8 pivot approved.
- 2026-05-24: reclassified as contributing phase slice under broader architecture-shift cleanup (`553`).

## 2026-05-23 Follow-on

- added protocol contract doc at `docs/protocols/vim-host-stdio.md`
- advanced local-host watcher instrumentation/hardening in `vim/plugin/toas.vim`
- tightened local-host vim parity/nonblocking tests and stream-subscribe stubs
- captured stdio harness deps in `pyproject.toml`/`uv.lock` (`pynvim`, `pexpect`)

## Compression Carry-Forward (2026-05-23)

### What proved out
- Callback-driven channel intake (`out_cb` raw mode) is materially more stable than poll-loop `ch_readraw` for this stream shape.
- Strict greedy NDJSON framing is viable in Vim when byte ownership is single-path:
  - callback only appends to RX accumulator
  - timer decodes complete newline-terminated frames
  - incomplete tail remains in RX
- Marked-region rendering avoids `$` append coupling and user-cursor interference.
- Bounded per-tick decode/frame/render budgets are required to preserve interaction responsiveness under burst streams.

### Failure patterns observed pre-phase8
- Prefix-truncated parse errors (`request_id": ...`) under poll-loop path.
- Apparent missing chunk ranges from tail-write/render behavior and terminality starvation.
- Startup/command-synchronous waits or unbounded per-tick drains can feel "blocked" despite async labeling.

### Contract rules to preserve when porting into `vim/plugin/toas.vim`
1. No user command may synchronously wait for stream completion.
2. Stream byte intake must be callback-owned (single ingress path).
3. Timer tick must be bounded work only (decode/process/render budgets).
4. Completion frame must not starve behind content backlog.
5. Render only inside explicit run/result regions; never rely on tail edits.
6. Keep stdout protocol-pure; diagnostics side-channel only.

### Immediate next slices for `toas.vim` proper
- Introduce callback-owned local-host intake behind existing transport seam.
- Move current watch/subscribe progressive rendering to marked-region updates.
- Add parity tests asserting:
  - no parse errors under burst+slow synthetic host
  - completion observed without timeout starvation
  - editing outside marked regions remains independent during active stream
- Keep wire logging toggle during migration (`/tmp` log path), then trim once stable.

## Current Triage Position (2026-05-24)
- Classification: contributing (not umbrella).
- Primary value: durable capture of contract rules and failure patterns that fed production plugin hardening.
- Cleanup intent: retain this as implementation rationale history; avoid duplicating overarching migration status here.
