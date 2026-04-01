## Goal

Create a deliberate prompt asset library with stable loading conventions.

## Scope

- Define on-disk layout for prompt assets
- Load prompts by phase and version
- Keep prompt loading explicit and testable

## Behavior

- Prompt files live in a predictable library structure
- Runtime code can ask for a prompt by purpose and version
- Missing prompts fail explicitly

## Rules

- Prompt assets are data, not scattered inline constants
- Loading should stay narrow and easy to replace later
- Version selection should default cleanly without hiding what was chosen

## Non-Goals

- No prompt registry service
- No dynamic prompt editing UI

## Done When

- Prompt files exist in a deliberate structure
- Runtime code can load prompts by phase and version
- Prompt loading behavior is covered by tests
