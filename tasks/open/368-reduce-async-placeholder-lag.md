# 368: Reduce initial lag for async placeholder rendering

- **Status**: Open

## Summary

The current non-blocking async execution flow (`rpc_async_nonblocking`) introduces a noticeable delay before the placeholder `TOAS:RUN` block appears in the buffer. This makes the interaction feel slower than the synchronous RPC path.

The delay is likely caused by the initial `timer_start` value in `s:toas_start_nonblocking_step` being too long.

## Action

- Investigate the `s:toas_watch_tick` timer in `vim/plugin/toas.vim`.
- The initial call in `s:toas_start_nonblocking_step` uses a delay of `120ms`. Experiment with reducing this initial delay to a much smaller value (for example `10ms` or `20ms`) to make the placeholder appear almost instantly.
- Ensure that subsequent polling in the repeat timer remains at a reasonable interval to avoid excessive CPU usage.
