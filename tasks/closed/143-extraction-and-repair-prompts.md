## Goal

Establish extraction and repair prompts as first-class assets even before their broader runtime use.

## Scope

- Add extraction prompt assets
- Add repair prompt assets
- Keep selection conventions shared with generation prompts

## Behavior

- The prompt library contains distinct assets for generation, extraction, and repair
- Runtime code can resolve those assets through one loading interface
- Prompt families are separated clearly enough to evolve independently

## Rules

- Extraction and repair prompts should not be hidden inside generation logic
- Prompt family boundaries should be obvious on disk
- Asset selection rules should stay uniform across prompt families

## Non-Goals

- No extraction or repair workflow overhaul yet
- No prompt chaining engine yet

## Done When

- Distinct extraction and repair prompt assets exist
- The runtime can load them through the shared prompt library
- The asset split is covered by tests and docs-level structure
