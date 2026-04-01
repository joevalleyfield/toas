## Goal

Define how TOAS should normalize or preserve model response details from the live endpoint.

## Scope

- Decide what to do with fields like `reasoning_content`
- Decide whether returned model ids should be canonicalized
- Decide what belongs in `llm_call` records versus transcript-visible consequences

## Behavior

- TOAS has an explicit policy for response-side extras
- Durable records remain useful without capturing accidental noise blindly
- Transcript-visible assistant output stays aligned with the intended user-facing surface

## Rules

- Normalization policy should be driven by observed endpoint behavior
- Do not silently discard fields without deciding why
- Keep durable records and transcript projections conceptually distinct

## Non-Goals

- No speculative support for every provider quirk
- No attempt to preserve every possible raw field by default

## Done When

- TOAS has a documented normalization policy for current endpoint responses
- The runtime reflects that policy where appropriate
- Tests cover the chosen treatment of important response fields
