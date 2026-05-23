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
- 2026-05-22: after landing related async host/runtime/demo/vim commits, we intentionally rolled back to parent change `svzwzlos` (just after this experiment commit) to re-play core ideas in a cleaner TDD-supporting order.

## Continuation Plan
1. Re-play async failure-surfacing semantics first (`daemon/run_store`, `daemon/async_runner`) with focused assertions around non-empty terminal failure detail.
2. Re-play host stdio serve lifecycle seams (`runtime/session_host_process`, `cli_host_commands`) with durable diagnostics and explicit startup/exit assertions.
3. Re-play demo client behavior (`cli_demo_async_client`) as a consumer contract over the stabilized host/runtime surfaces.
4. Re-play Vim adapter changes (`vim/plugin/toas.vim`) last, only after core host/runtime behavior is reconfirmed.
5. Keep each slice independently committable and traceable to its assertion surface to avoid interleaved regressions.

## Closing Notes (2026-05-22)

- Status: closed as completed exploratory spike.
- Outcome:
  - experiment proved persistent multi-turn async stdio subprocess conversation shape.
  - core learnings were harvested into production-direction work (host stdio lifecycle seams, diagnostics, and subscribe-style push framing in demo/runtime compatibility path).
- Boundary for closeout:
  - this task intentionally remains a proof-of-concept artifact, not the canonical production contract.
  - remaining production hardening and Vim parity work continues under `543`/`542`/`541`.
