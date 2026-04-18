## Goal

Harden streaming generation against backend reasoning-parse failures that surface as `<|channel>` / parse-position errors.

## Why Now

Some backend/model combinations fail before first token when reasoning-format streaming is requested, causing full run failure even when normal streamed completion would work.

## Scope

- detect known reasoning parse failure signatures in streaming path
- retry once without reasoning-format request when failure occurs before any emitted content
- preserve existing behavior for non-matching failures
- add regression test coverage

## Intended Behavior

- TOAS recovers automatically from this backend failure mode in-stream
- user sees successful completion instead of immediate run failure when fallback path is viable

## Constraints

- do not mask unrelated backend errors
- do not retry if content has already streamed (avoid duplicate output risk)

## Done When

- fallback is implemented in `src/toas/llm.py`
- tests cover fallback call-shape transition and successful completion

## Progress

- added parse-failure signature detection helper in streaming path
- added one-shot retry without reasoning request when failure occurs pre-output
- added regression test in `tests/test_llm.py`
- added partial-stream salvage path: if content deltas already emitted before stream error, return accumulated content with warning instead of failing run
- added parse-error payload salvage path: when backend parse failure includes recoverable `<channel|>` content, return salvaged content with warning
