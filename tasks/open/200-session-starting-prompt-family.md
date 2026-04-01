## Goal

Create the first real prompt-library expansion: a moderately rich family of session-starting prompt assets that lower human activation energy while seeding protocol-oriented prompt experimentation.

## Scope

- add only session-starting prompt assets in this pass
- organize assets by user intent at session start
- require uniform per-asset metadata
- provide basic browsing/listing support for discovery

## Categories

Top-level categories for the first pass:

- `start-here`
- `role-framing`
- `protocol-entrainment`
- `backend-deconfliction`

## Intended Shape

- target roughly 3–6 assets per category
- keep the set moderately rich but curated
- allow some assets to be multi-turn exemplars
- do not require assets to be tied to a specific transcript role

## Metadata Requirements

Every asset must carry indexable metadata with at least:

- `name`
- `description`
- `category`

Descriptions should be short one-liners suitable for browsing.

## Success Criteria

Primary success criterion:
- lower activation energy for humans starting a session

Secondary success criterion:
- include some hypothesis-driven prompts for protocol entrainment and backend deconfliction, even if they are provisional and may later be replaced

## Non-Goals

- no hidden runtime prompt injection
- no assumption that prompt assets are always active
- no requirement that protocol-oriented prompts be validated as successful in this first pass

## Done When

- the prompt library includes the first session-starting family
- assets are organized by the defined categories
- each asset has indexable metadata
- users can browse/list the family without opening files blindly
