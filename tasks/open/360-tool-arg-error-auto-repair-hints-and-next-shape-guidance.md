## Goal

Convert common tool-shape failures into immediate corrective guidance so models can self-repair in one additional step.

## Why Now

Even with better prompts, weak models still emit invalid argument shapes; terse errors alone waste turns and reduce momentum.

## Scope

- extend tool error/result projection with corrective "next valid shape" hints where safe
- prioritize high-friction tools (`shell`, `capability_help`, edit tools)
- keep hints compact and deterministic (no speculative policy drift)
- add regression tests for projected repair hints

## Intended Behavior

- invalid payloads produce actionable correction snippets in `## RESULT`
- model can copy/adjust to valid shape in next turn without extra discovery steps

## Done When

- targeted tools emit repair hints for top failure modes
- replay probes show reduced repeated-shape failures
