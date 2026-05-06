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

## Decision (2026-05-06)

- Chosen near-term policy: de-emphasize `search` in default weak-model-facing guidance and prefer first-pass `$ rg ...` via user-shell shorthand.
- Keep `search` available for structured needs (`query` + optional `path`/`limit`/`regex`) rather than removing capability.

## Implementation Notes

- Updated shared tools guidance (`/help tools` source) to mark `search` as structured-use and explicitly prefer `$ rg ...` for first-pass discovery.
- Updated dynamic repo-work capability prompt to:
  - frame `search` as structured/secondary usage, and
  - recommend `$ rg ...` first-pass discovery through user-shell shorthand.
- Added tests locking both guidance surfaces.

## Verification

- `uv run pytest` -> `1244 passed` on 2026-05-06.

## Status

Closed.
