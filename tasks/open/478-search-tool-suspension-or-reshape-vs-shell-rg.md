## Goal

Decide whether TOAS `search` should be temporarily suspended from default weak-model-facing guidance or reshaped so it clearly outperforms/compliments raw `shell rg` in practice.

## Why Now

Recent operator spikes show recurring argument-shape mismatch (`pattern`/`directory` vs required `query`) and recovery loops that add friction relative to direct `shell` `rg` calls.

## Scope

- analyze observed spike failures/successes for `search` tool usage
- compare model success rate and operator friction: `search` vs `shell` `rg`
- choose one near-term policy:
  - suspend/de-emphasize `search` in default guidance, or
  - reshape `search` interface/aliases to match model priors (`pattern`, `directory`, etc.)
- define acceptance criteria for chosen policy

## Constraints

- avoid capability loss that blocks legitimate non-shell search workflows unless explicitly accepted
- keep safety/approval boundaries intact for shell usage
- keep guidance consistent across prompts/help surfaces

## Done When

- decision recorded and implemented (or explicitly deferred with rationale)
- prompt/help guidance reflects the decision
- tests cover chosen behavior shape and common weak-model call patterns

## Status

Open.
