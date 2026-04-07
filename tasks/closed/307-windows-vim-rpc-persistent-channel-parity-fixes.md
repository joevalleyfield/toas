## Goal

Restore real persistent daemon-RPC stepping in Vim on Windows (including Git Bash/MSYS Vim) so `:ToasStep` uses the daemon path by default and matches CLI `toas step` behavior.

## Scope

- fix Vim transport selection and channel-open compatibility for Windows Vim variants
- add a Windows Vim-friendly daemon transport endpoint for persistent channels
- enforce RPC/CLI parity by making request workdir explicit and normalized
- add practical transport diagnostics to identify fallback vs RPC delivery and payload shape

## Intended Inputs

- existing daemon named-pipe transport for CLI RPC
- existing Vim persistent-channel plugin
- observed Windows runtime behavior: false fallback, empty RPC output, path-format mismatches

## Intended Outputs

- working Windows-default Vim persistent RPC channel
- consistent `step` behavior between CLI path and daemon RPC path for the same workspace
- operator-facing Vim diagnostics for quick transport troubleshooting

## Constraints

- no protocol fork between CLI RPC and Vim RPC payload semantics
- keep daemon operation handlers transport-agnostic
- preserve CLI fallback behavior when channel transport is unavailable

## Non-Goals

- no removal of named-pipe transport for CLI
- no expansion of RPC op surface
- no major Vim UX redesign beyond transport correctness and diagnostics

## Done When

- `:ToasStep` uses RPC (not fallback) on Windows when daemon is running
- `/prompt` and other step consequences match CLI parity for same workdir/session state
- Vim diagnostics clearly distinguish: channel open failure, RPC error response, empty consequence

## Notes

Key fixes landed:

- daemon:
  - added Windows localhost TCP RPC server for Vim persistent channel
  - wrote port file `.toas.vim-port` and cleaned it on stop/shutdown
  - normalized MSYS-style workdir paths (`/c/...`) to Windows form for request execution
  - added optional debug log hook (`TOAS_RPC_DEBUG_LOG`) for in/out request tracing
- CLI/daemon parity:
  - RPC requests now include explicit `workdir`
  - daemon executes ops in request `workdir`, restoring afterward
  - Windows PID liveness check uses Win32 process APIs (not `os.kill(pid, 0)`)
- Vim plugin:
  - switched to raw framed JSON channel semantics (newline-delimited)
  - fixed Windows detection to include `win32unix`
  - removed unsupported `ch_open(..., waittime=...)` usage
  - fixed request-id float formatting bug
  - fixed false-success behavior when channel is not open
  - kept and extended diagnostics:
    - `:ToasTransport`
    - `:ToasLastError`
    - `:ToasRpcLens`
    - `:ToasProbe`
    - `:ToasDebug`
