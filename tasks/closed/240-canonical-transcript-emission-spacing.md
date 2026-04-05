## Goal

Standardize transcript emission/replay formatting to a canonical readable form with explicit blank-line spacing around TOAS role headings.

## Scope

- canonicalize rendered/projected transcript style to use:
  - blank line separation between blocks
  - `## TOAS:<ROLE>` on its own line
  - consistent blank line after each role heading before content
- apply the same style across transcript rendering and CLI replay/projection output paths
- update tests to assert canonical spacing where appropriate

## Intended Inputs

- current transcript renderer behavior
- current CLI block-printing behavior
- existing transcript/rebuild tests

## Intended Outputs

- stable pretty emission style (`\n\n## TOAS:...\n\n` boundaries)
- fewer cosmetic discontinuities in user-edited transcript loops
- test coverage for canonical formatting output

## Constraints

- no change to transcript parsing split semantics
- no role-marker syntax expansion
- no hidden content mutation beyond spacing normalization in emitted output

## Non-Goals

- no parser heuristics or fuzzy marker detection changes
- no change to lineage/binding logic

## Done When

- emitted/rebuilt transcripts use one canonical spacing style
- parser behavior remains unchanged
- formatting-only diffs are materially reduced in normal operation
