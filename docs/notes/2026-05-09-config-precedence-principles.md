# Config Precedence Principles (Aspirational)

Status: guidance note for least-surprise alignment. Not a runtime-wide contract yet.

## Intent

TOAS should converge toward a precedence model where the most immediate, intentional operator action wins over broader defaults.

## Precedence Ladder (target)

Highest to lowest:

1. Explicit command/turn-local overrides
   - CLI flags
   - one-shot command args
   - transcript-scoped direct modifiers for the current step (for example `/env set ...` in-session)
2. Environment variables
3. Config files (with deterministic merge order)
4. In-code defaults

Rule of thumb: specific overrides trump general defaults.

## TOAS-Specific Nuance

TOAS has durable operator state in events (`config_override` records from `/config set`).

Operationally, durable session overrides should remain a first-class intentional layer. Where they map to policy fields, they are expected to outrank file config. Placement relative to process environment should be explicit per subsystem and documented.

## Runtime Mutation Cases

- Transient runtime mutations (in-memory) are immediate for the running step/process.
- Persistent runtime mutations (written to durable records or files) participate in normal precedence on subsequent steps.

## Current State / Known Exceptions

Not all subsystems follow one shared resolver today.

Examples:
- Some LLM/prompt transport settings currently use env-top patterns.
- Some shell-stream behavior has been aligned with scoped precedence work under task `485`.

These are not blanketly wrong; they are exceptions to be documented and revisited deliberately rather than changed ad hoc.

## Engineering Guidance

When adding or modifying config behavior:

1. Define precedence explicitly for that subsystem.
2. Keep it consistent with this ladder unless there is a strong reason not to.
3. Document exceptions inline and in user-facing docs.
4. Add tests that lock precedence expectations.

## Related

- `466` config sequencing/precedence contract and diagnostics clarity
- `485` shell-lane purpose unification and shared stream-policy handling
