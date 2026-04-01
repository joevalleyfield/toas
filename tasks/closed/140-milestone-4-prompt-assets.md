## Goal

Treat prompts as explicit, versioned assets rather than scattered inline strings.

## Scope

- Prompt storage and layout conventions
- Prompt selection by operator phase
- Prompt versioning
- Separation of generation, extraction, and repair prompts

## Why

The runtime now has real model calls and a real tool layer, but prompt behavior is still implicit. This milestone should make prompts reviewable assets with a small selection layer before prompting complexity grows further.

## Planned Tasks

- `141`: prompt asset library and loader
- `142`: generation prompt selection and wiring
- `143`: extraction and repair prompt assets

## Non-Goals

- No premature prompt-tuning program without observability
- No single hidden mega-prompt

## Done When

- Prompt assets live in a deliberate library structure
- The runtime can select prompts by purpose and version
- Prompt changes become reviewable and testable as first-class artifacts
