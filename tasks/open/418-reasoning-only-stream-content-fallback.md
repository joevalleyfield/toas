## Goal

Prevent stream-mode hard failure when backend emits reasoning/thinking deltas but no assistant content deltas.

## Why Now

Observed runs can stream meaningful thinking text and then terminate without content, currently ending as `empty chat completion content (stream mode)`.

## Scope

- allow stream finalization to use reasoning text as assistant content when content is empty
- emit warning on this fallback path
- add regression test coverage

## Intended Behavior

- runs with reasoning-only streamed output succeed instead of failing empty-content guard
- warning remains side-channel/stderr, not injected into transcript content

## Constraints

- only fallback when content is empty and reasoning is non-empty
- preserve existing failure for truly empty stream responses

## Done When

- fallback path is implemented in `src/toas/llm.py`
- tests cover reasoning-only stream success path

## Progress

- implemented reasoning-only stream fallback in `_finalize_accumulated_response`
- added regression test in `tests/test_llm.py`
