## Goal

Stabilize Vim's local-host reasoning/progress stream contract so acknowledged stream policy does not flip during resubscribe windows and reasoning deltas render as explicit thinking blocks instead of bare answer-adjacent text.

## Why Now

Observed local-host runs can start with `thinking`/`prompt_progress` correctly reported as enabled, then later show them as off after a subscribe window rollover. In the same lane, reasoning text currently renders bare ahead of the answer, and provider-specific reasoning-style content can glue onto the final response instead of remaining visually distinct.

## Scope

- preserve per-run stream-policy state in Vim when subscribe/watch payloads omit policy fields
- render `llm_reasoning` deltas in Vim as `## TOAS:THINKING` blocks with deterministic close behavior
- close open thinking blocks on first answer/tool/projection text or on terminal completion when no visible answer follows
- add Vim regression coverage for policy persistence and reasoning-block rendering
- keep prompt/runtime notes in sync where the intended behavior is clarified

## Intended Behavior

- `stream: thinking=on prompt_progress=on` remains stable for a run once the async step ack establishes it
- reasoning deltas are visually separated from answer text in Vim using the same thinking markers already recognized by transcript parsing
- reasoning-only terminal runs do not leave an unterminated thinking block in the buffer

## Constraints

- do not infer reasoning from answer text heuristics; use semantic lane information when it is present
- do not regress existing projection/tool/result lane rendering behavior
- preserve local-host resubscribe dedup behavior

## Done When

- Vim local-host follow mode no longer overwrites stored stream policy with `{}`-shaped subscribe payloads
- `llm_reasoning` events render inside explicit thinking markers and close correctly
- focused regression tests cover both behaviors

## Progress

- 2026-06-01: Landed first cleanup pass for the Vim-facing contract.
- local-host follow mode now preserves acknowledged `stream_policy` when later subscribe/watch payloads omit that field
- `llm_reasoning` lane text now renders inside explicit `## TOAS:THINKING` blocks and closes on answer/terminal boundaries
- prompt-progress callback normalization now accepts object-shaped progress payloads so Vim receives semantic progress events
- progress-only updates now trigger run-region redraws instead of waiting for final status/text
- disabled prompt-progress mode now suppresses both worker-side text parsing and Vim-side text fallback rendering
- added focused Python/Vim regression coverage for reasoning rendering, stream-policy persistence, prompt-progress midrun visibility, and prompt-progress disabled behavior
