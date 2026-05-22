# 546 Async Stdio IPC Todo Experiment

## Goal
Land an isolated async stdio IPC experiment showing a long-lived command server and client interaction over multiple request/response turns.

## Why
We want a minimal, stateful subprocess protocol that demonstrates host-REPL-style I/O behavior where `subprocess.communicate()` is not the right interaction model.

## Scope
In scope:
- async stdio server loop with small command surface (`add`, `list`, `done`, `shutdown`)
- async client session that keeps one subprocess alive and issues multiple framed requests
- focused test proving multi-turn stateful behavior across one subprocess session

Out of scope:
- integration into primary TOAS runtime/daemon surfaces
- policy/model/tool registry wiring

## Done When
- experiment module exists and is runnable in server/demo modes
- test proves multi-request roundtrip and state mutation over one subprocess
- roadmap reflects the open exploratory slice

## Progress
- 2026-05-21: added `src/toas/experiments/async_stdio_todo_ipc.py` with async NDJSON stdio server/client experiment.
- 2026-05-21: added `tests/test_async_stdio_todo_ipc_experiment.py` validating multi-turn stateful behavior over one persistent subprocess.
