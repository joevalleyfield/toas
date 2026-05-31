# 668 Vim-Lane LLM Response Duplication Regression

## Goal
Identify and fix a regression where LLM answer content appears duplicated in Vim-rendered output, likely in local-host streaming/projection paths.

## Symptom
- User-observed duplicate assistant response text during/after streaming.
- Initial suspicion: duplication is Vim-lane specific (or more visible there) rather than core model generation duplication.

## Scope
In scope:
- reproduce duplication in Vim/local-host path with logs
- verify whether duplication is lane-specific (`llm_answer` vs `tool`) or projection-specific
- isolate whether duplication is introduced by:
  - host subscribe compatibility projection (`chunk` projection vs semantic events)
  - Vim watch pump frame adaptation/merge path
  - fallback watch/read paths rendering both semantic and compatibility text
- implement fix preserving streaming continuity and terminal semantics
- add regression tests that fail on duplicated rendered LLM answer content

Out of scope:
- unrelated throughput tuning not required to fix duplication
- model/backend-side true repeated token generation bugs without transport/projection involvement

## Repro Inputs
Capture for each repro:
- transport mode (`local_host`/rpc compatibility)
- run_id
- relevant tails from:
  - `.toas/host-stdio-vim.log`
  - `.toas/host-stdio-wire.log`
  - `.toas/host-stream-debug.jsonl` (if enabled)
- evidence of rendered duplication in transcript buffer and/or `.toas/foo.md`

## Done When
- deterministic repro exists in automated test coverage
- root cause is identified and fixed
- Vim/output no longer duplicates LLM answer text under repro conditions
- roadmap/task notes updated with closure details

## Related
- `665` shell-intent streaming backslide and pacing follow-through
- `663` transport contract guardrails and producer/projection boundary notes
