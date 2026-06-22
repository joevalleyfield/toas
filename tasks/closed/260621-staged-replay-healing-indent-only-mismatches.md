Filed as: 260621-staged-replay-healing-indent-only-mismatches
FKA:
AKA: staged replay healing; indent-only mismatch recovery; search_indent replay suggestion
Legacy index:

keywords: tooling, exploration, inception, usability, search, patch, replay, whitespace

Related: `566`; `260621-search-block-first-line-indent-diff-fidelity`

# Staged Replay Healing For Indent-Only Mismatches

## Current Reality

When `replace_block` misses because indentation is the only meaningful delta,
TOAS can diagnose the mismatch but does not yet stage a one-more-step replay
healing path. The user still has to infer the needed `search_indent` adjustment
manually.

## Desired Reality

If near-match diagnostics strongly suggest that indentation is the only delta,
TOAS should be able to stage a replay-ready follow-up with the necessary
argument modification so the user can execute the repair in one more step.

## Gap Analysis

- We do not currently have a staged replay healing concept for tool argument
  repair.
- We need a confidence model that distinguishes indent-only deltas from broader
  textual drift.
- We need to decide where proposed healed arguments live: diagnostics only,
  projected structured metadata, or an explicit repair surface.

## Known Facts

- `replace_block` already supports `search_indent` and `replacement_indent`
  arguments.
- Near-match diagnostics can already identify high-similarity candidate windows.
- Indent-only mismatch healing is larger than the current bounded-diagnostics
  task because it introduces a new staged replay behavior.

## Unknowns

- What confidence threshold is safe enough to propose a healed replay without
  encouraging silent mispatches.
- Whether the staged replay artifact should remain advisory or become a
  first-class executable repair affordance.
- How this should interact with future generalized tool-result or replay-healing
  infrastructure.

## Investigations

- Characterize the exact signature of indent-only mismatches across strict,
  default, and lax matching modes.
- Prototype a detector that proposes `search_indent` only when non-whitespace
  content aligns exactly.
- Survey where TOAS could surface a staged replay suggestion with minimal new
  semantics.

## Evidence

Ready to leave inception when:

- we have examples proving indent-only mismatch detection is separable from
  broader near matches
- the owner surface for staged replay healing is identified
- proposal safety constraints are explicit enough to implement without broad
  guesswork

## Risks

- Over-eager healing could turn a diagnostic hint into an unsafe patch
  suggestion.
- A too-local implementation could paint us into a corner before broader staged
  replay semantics exist.

## Next Actions

- Gather concrete mismatch examples where `search_indent` replay healing would
  have resolved the failure safely.
- Decide whether this belongs in `replace_block` diagnostics, replay metadata,
  or a broader healing surface.
- Open a focused implementation task only after the staged replay contract is
  explicit.
