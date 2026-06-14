# 675 Architecture intent doc refresh and stale module guidance cleanup
keywords: docs, governance, active, architecture, intent, runtime, ownership, decomposition, guidance

## Goal

Refresh architecture-facing guidance so repo docs describe the current ownership model and decomposition intent instead of preserving oversimplified or stale module-boundary advice.

## Why

The current written guidance is uneven:

- `README.md` is relatively current about runtime surfaces and user-facing behavior.
- `AGENTS.md` still carries simplified implementation bias like “keep operator semantics in `step.py`” and “keep tool semantics in `tools.py`,” even though major runtime/tool decomposition work has already moved ownership into `src/toas/runtime/` and `src/toas/tools_cluster/`.
- some “important files” guidance and command-surface notes still point readers toward historical module centers rather than current ownership boundaries.

That mismatch makes architectural intent harder to read and encourages well-meaning changes to land in legacy compatibility hubs simply because the docs still imply that they should.

## Scope

- audit and update architecture-facing guidance in:
  - `AGENTS.md`
  - `README.md`
  - a dedicated architecture note/doc that encodes the destination module-ownership and boundary intent for `400`
  - any adjacent architecture/terminology note that should carry the canonical explanation instead of duplicating stale simplifications
- author the dedicated `400` destination-architecture doc
  - describe intended long-term ownership boundaries for `step.py`, `cli.py`, `daemon.py`, `tools.py`, and the runtime/tool subpackages
  - distinguish canonical ownership modules from compatibility façades and historical import surfaces
  - make clear where new shared runtime semantics should land while `400` remains in progress
- clarify current ownership posture, including distinctions such as:
  - operator-facing orchestration vs shared runtime semantics
  - runtime-owned modules vs compatibility façades
  - tool capability ownership vs historical `tools.py` import surface
- remove or rewrite references to modules/boundaries that no longer reflect current structure
- ensure guidance matches the decomposition direction captured in `400` and runtime-ownership work captured in `572`

## Non-Goals

- rewriting all project docs
- changing runtime behavior
- documenting every historical refactor in user-facing docs

## Intended Behavior

- contributors can tell where new logic should live from current docs without reverse-engineering recent refactors
- architecture notes describe intent, not just historical residue
- `AGENTS.md` stops steering changes into legacy module centers when current ownership lives elsewhere
- `400` has an explicit destination-architecture document that contributors can use as the boundary reference while decomposition remains incremental

## Done When

- `AGENTS.md` no longer presents stale module-boundary advice as current truth
- a dedicated doc exists that encodes the destination architecture intended by `400`
- current runtime/tool ownership is described in at least one clear architecture-facing source, with the new `400` destination doc serving as the canonical boundary reference or explicitly linked from it
- stale file/module references that materially distort contribution guidance are corrected or removed
- roadmap/task stitching records that the cleanup is about architectural intent clarity, not cosmetic doc churn

## Notes

- This task is partly documentation maintenance and partly architecture-governance hardening.
- Prefer one canonical destination-architecture doc for `400`, with shorter contributor-facing docs linking to it instead of re-explaining the same ownership model differently.
- Link the final wording back to `400`, `572`, and `674` as appropriate so decomposition intent and contribution guidance stay aligned.
