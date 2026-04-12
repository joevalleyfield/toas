## Goal

Remove stale JSON action-object entrainment from active prompt assets so callable guidance is unambiguous in the current fenced-YAML lane.

## Why Now

Operators observed real failures where assistant output proposed `operation: shell` with `command:` instead of required `arguments.argv`, indicating lingering protocol ambiguity in prompts and probes.

## Scope

- remove JSON action-object examples from active protocol entrainment prompts
- reinforce canonical shell callable shape (`operation: shell` + `arguments.argv`)
- align harness protocol-collision probes to YAML-only local action lane
- add regression coverage that `protocol/entrain_v1` no longer teaches JSON action objects

## Outcome

Implemented in current pass:
- `protocol/entrain_v1` now demonstrates YAML-only local action lane including shell `argv` shape
- stale `session-start/protocol-entrainment/json-action-object_v1` asset removed
- harness probe replaced with YAML shell `argv` probe
- prompt regression test added to prevent JSON-lane reintroduction
