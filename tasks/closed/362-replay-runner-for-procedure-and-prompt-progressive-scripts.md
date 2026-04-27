## Goal

Provide a first-class replay runner for progressive prompt/procedure scripts so behavior tuning is reproducible without ad-hoc shell harnesses.

## Why Now

Reliable evaluation of weaker-model steering requires repeating the same multi-turn shape under current assets; manual transcript editing is noisy and easy to mis-run.

## Scope

- define replay script input format
- support append-first execution semantics (`step >> session.md` equivalent)
- capture run artifacts (step outputs, history snapshot, session tail)
- integrate with procedure invocation once `361` lands

## Progress

- added first-class CLI replay runner command: `toas replay-script <script_path> [--output <path>] [--dry-run]`
- added replay script parser with append-first semantics and deterministic step records (`append`, `step`, `source`)
- added integrated prompt/procedure step sources (`source: prompt|procedure`) with artifact capture (`steps`, `events_tail`, `session_tail`)
- added parser/append shaping tests and dispatch coverage for replay runner command flags

## Intended Behavior

- one command replays a progressive session-shaping script
- replay consumes current prompt/procedure assets and exposes behavior drift quickly

## Done When

- replay runner is implemented and tested
- at least one fixture covers repo-local discovery/task-pick flow
- docs include standard replay workflow for agentic steering validation
