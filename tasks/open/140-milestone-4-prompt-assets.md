## Goal

Treat prompts as explicit, versioned assets rather than scattered inline strings.

## Scope

- Prompt storage and layout conventions
- Prompt selection by operator phase
- Prompt versioning
- Separation of generation, extraction, and repair prompts

## Non-Goals

- No premature prompt-tuning program without observability
- No single hidden mega-prompt

## Done When

- Prompt assets live in a deliberate library structure
- The runtime can select prompts by purpose and version
- Prompt changes become reviewable and testable as first-class artifacts
