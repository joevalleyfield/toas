## Goal

Provide a first-class replay runner for progressive prompt/procedure scripts so behavior tuning is reproducible without ad-hoc shell harnesses.

## Why Now

Reliable evaluation of weaker-model steering requires repeating the same multi-turn shape under current assets; manual transcript editing is noisy and easy to mis-run.

## Scope

- define replay script input format
- support append-first execution semantics (`step >> session.md` equivalent)
- capture run artifacts (step outputs, history snapshot, session tail)
- integrate with procedure invocation once `361` lands

## Intended Behavior

- one command replays a progressive session-shaping script
- replay consumes current prompt/procedure assets and exposes behavior drift quickly

## Done When

- replay runner is implemented and tested
- at least one fixture covers repo-local discovery/task-pick flow
- docs include standard replay workflow for agentic steering validation
