## Goal

Codify how TOAS chooses prompts, flags, and fallback behavior for awkward or antagonistic backends.

## Scope

- define when no-thinking and similar request flags should be used
- define fallback from preferred action syntax to safer alternatives
- keep adaptive policy separate from transcript-visible consequences

## Behavior

- TOAS has an explicit backend-adaptive generation policy
- runtime choices are based on observed backend behavior rather than single-path assumptions

## Done When

- prompt/flag selection has documented rules
- future extraction/repair work can rely on that policy instead of inventing its own
