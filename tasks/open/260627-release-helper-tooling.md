Filed as: 260627-release-helper-tooling
FKA:
AKA: release scripts; release helper scripts; release automation helpers; release note scaffolding
Legacy index:

keywords: tooling, governance, inception, release, automation, cadence, docs

Related: `260627-release-process-and-weekly-release-lane`

# Release Helper Tooling

## Current Reality

TOAS now has a documented release process, release-review cadence, versioning
policy, and release-notes home.

That policy is durable enough to run manually, but the repetitive mechanics are
still easy to do inconsistently:

- scaffolding release notes
- scaffolding recurring release-review run records
- collecting the likely release slice since the last release tag
- validating that the release version, git tag, and note filename all match

## Desired Reality

TOAS should have a small set of helper scripts that make the release process
easy to execute consistently without hiding the release policy behind opaque
automation.

The goal is operator-assisting tooling, not a one-command black box release
pipeline.

## Scope

- identify the highest-value release helper scripts
- define where they should live and how they should be invoked
- prefer scaffolding/validation/reporting helpers over publish-time complexity
- keep helper outputs aligned with `docs/release-process.md`,
  `docs/releases/`, and `tasks/recurring/runs/`

## Non-Goals

- package publication or distribution automation
- CI workflow design
- artifact signing or release hosting
- replacing the recurring release-review record with generated hidden state

## Known Facts

- `docs/release-process.md` defines the current release policy
- `docs/releases/README.md` defines the release-notes filename convention
- recurring maintenance records live under `tasks/recurring/runs/`
- the current policy makes the git tag exactly equal to the release version
  string

## Candidate Helpers

- release-note scaffold helper
- recurring release-review run scaffold helper
- release-candidate summary helper
- release tag/version/notes consistency checker

## Risks

- building too much automation before the manual release lane is proven once
- coupling helper behavior too tightly to details that may still evolve
- hiding important release judgments behind generated defaults

## Exit Evidence

- one focused helper-tooling task exists as the home for release ergonomics
- the task preserves the boundary between release policy and helper mechanics
- the task is ready to split into implementation slices once the first manual
  release-review run exposes the sharp edges
