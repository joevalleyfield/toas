# 467 Vim plugin daemon port-path alignment

## Summary

The Vim plugin currently defaults to legacy daemon discovery paths (`.toas.vim-port` and `.toas.sock`), while the daemon writes and serves from `.toas/toas.vim-port` and `.toas/toas.sock`. This causes channel-open failures even when a daemon is running.

## Scope

- Update Vim plugin default discovery paths to match daemon defaults.
- Keep existing override variables (`g:toas_vim_port_path`, `g:toas_socket_path`) intact.
- Preserve fallback reads for legacy locations to avoid breaking older environments.

## Acceptance

- Vim plugin can connect to a running daemon without manual `g:toas_vim_port_path` override in default repo layout.
- Plugin still supports legacy port-file location as a fallback.
