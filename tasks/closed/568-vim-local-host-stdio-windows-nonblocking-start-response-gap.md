# 568 - Vim local_host stdio Windows nonblocking start response gap

## Summary

On Windows first-drive runs of Vim `ToasStep` over `local_host` stdio can fail during nonblocking start with:

- `ToasLane: none`
- `ToasLastError: nonblocking step start failed: empty or partial local_host response`

Initial evidence indicates request/response intake can miss host output when callback-driven stdout delivery lags, even though the host is running.

## Scope

- harden Vim local-host request intake for `step_async*` startup path on Windows
- preserve existing protocol shape and lane semantics
- add/adjust targeted regression coverage where feasible

## Acceptance

- `ToasStep` nonblocking start no longer fails with `empty or partial local_host response` in the observed Windows stdio host lane scenario
- no regression for existing Vim local-host streaming/watch behavior
- task and roadmap stitched with implementation updates
