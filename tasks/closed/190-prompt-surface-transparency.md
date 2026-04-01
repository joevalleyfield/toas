## Goal

Make prompt authority visible and inspectable by removing hidden prompt behavior from ordinary generation and treating prompt assets as explicit library material.

## Scope

- remove implicit prompt injection from ordinary generation
- clarify the distinction between prompt content, backend flags, and backend policy
- keep prompt assets available without turning them into silent runtime layers

## Planned Tasks

- `191`: remove implicit generation prompt injection
- `192`: recast prompt assets as explicit library material
- `193`: improve model-input prompt transparency
- `194`: separate prompt content from backend policy

## Why

Backend-adaptive protocol work is useful, but it should not smuggle behavioral control back into hidden prompt layers. TOAS should keep prompt authority visible before it grows extraction or repair behavior.

## Done When

- ordinary generation has no hidden default prompt layer
- prompt assets are explicit and inspectable in their use
- backend flags/policy are not conflated with prompt content
