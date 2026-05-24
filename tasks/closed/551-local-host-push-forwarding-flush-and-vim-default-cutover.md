# 551 Local-Host Push Forwarding Flush And Vim Default Cutover

## Goal
Make local-host subscribe streaming truly incremental end-to-end and cut Vim transport default to local-host.

## Why
Vim progressive rendering depends on immediate forwarding of stream progress (`push_event`) rather than post-hoc burst delivery.

## Scope
- host stdio subscribe handling flushes frames as produced
- preserve existing immediate-reject subscribe contract
- flip Vim default `g:toas_transport_mode` to `local_host`
- keep explicit RPC opt-back support

## Done When
- subscribe no longer buffers full frame list before writing to stdout
- Vim default transport resolves to local-host without user override
- targeted runtime host tests pass

## Validation
- `uv run pytest tests/test_runtime_session_host_process.py -q --no-cov`

## Notes
- This closes the practical post-completion burst regression observed in live Vim usage where stream progress/tokens appeared only after run completion.
