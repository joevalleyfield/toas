## Goal

Reframe `/extract` around frontier assistant-command adoption: make the latest assistant turn's callable intent easy to inspect and run, without historical transcript scanning.

## Why Now

Current `/extract` behavior drifted into historical scan/replay semantics. The primary operator need is near-frontier command adoption from the latest assistant turn.

## Scope

- redefine `/extract` target model to the last assistant turn only
- keep dual modes:
  - `/extract --dry-run`: inspect what would run from the last assistant turn
  - `/extract --execute`: run that intent now
- preserve durable command/tool recording for executed path
- remove historical index scanning from `/extract`
- update help/errors to make scope explicit (frontier assistant only)

## Intended Inputs

- current `/extract` implementation from `234`, `271`, `272`
- callable detection logic for YAML plans and assistant loose-command blocks
- command/tool durable record write path in `cli.py`

## Intended Outputs

- `/extract` that behaves as a frontier ergonomics command
- deterministic dry-run/execute behavior against only the latest assistant turn
- tests proving historical turns are ignored by `/extract`

## Constraints

- no hidden fallback to historical scan in `/extract`
- no behavior change to durable record invariants
- explicit failure when the latest assistant turn has no callable intent

## Non-Goals

- no historical replay feature in this task
- no broader extraction/repair semantics over full transcript history

## Done When

- `/extract` operates only on the latest assistant message
- dry-run and execute paths are both test-covered
- task `276` remains as the explicit home for any historical replay behavior
