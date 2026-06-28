# TOAS Release Process

Status: CURRENT
Normative Scope: release cadence, versioning policy, release gates, release artifacts
Task Link: `260627-release-process-and-weekly-release-lane`

## Purpose

This document defines how TOAS cuts stable tagged releases.

It is intentionally lightweight. It establishes a real release cadence and a
real release gate without assuming packaging, publication, or distribution
infrastructure.

## Release Definition

For the current TOAS process, a release is:

- a git tag whose name is exactly the release version
- release notes under `docs/releases/`
- a release-review run record under `tasks/recurring/runs/`

The release-review run record is the operational record of what happened during
the release window. The release notes are the product-facing summary of what
shipped.

Tag/version mapping:

- there is no separate tag alias or prefix by default
- the git tag is the canonical published release identifier
- the tag name must exactly match the release version string

Examples:

- release version `1.0.3.2` -> git tag `1.0.3.2`
- release version `1.0.3.2-r1` -> git tag `1.0.3.2-r1`

## Cadence

Default release cadence:

- weekly release review

Additional release reviews are allowed:

- after a milestone-worthy coherent slice lands before the next weekly review

Not every review must produce a release. Each review should record one of:

- `cut`
- `deferred`
- `skipped`

## Release Eligibility

A release window is eligible for a TOAS release when at least one landed change
in the window is release-worthy by current project standards.

For the current process, release-worthy means:

- at least one landed `feat`-class change, or
- at least one landed behavior-changing `fix`-class change

Pure docs, chores, internal refactors, or test-only changes do not require a
release by themselves unless the operator explicitly decides they represent a
stable checkpoint worth tagging.

## Meaning Of A Tag

A TOAS release tag identifies:

- the most recent repository state in that release window
- that satisfies the release gate
- and is considered the current stable checkpoint

This means a release tag is not merely a weekly snapshot. It is an explicit
claim that the tagged state is the last stable state that met the release
criteria without requiring unusual cleanup.

## Release Gate

The release gate is real, not ceremonial.

A release should not be cut unless all of the following are true:

- the routine check set in `docs/checks.md` is green for the tagged commit
- release notes have been generated and reviewed
- task, roadmap, and workboard state are not obviously misleading for the
  included release slice
- there is no known unresolved regression being knowingly stamped as stable

The release gate may be automated or delegated to an agent, but the existence
of automation does not relax the gate.

## Versioning

TOAS uses a four-component release version:

`EPOCH.MAJOR.MINOR.PATCH`

Interpret this as:

`epoch.{semver}`

Meaning:

- `EPOCH` is a deliberately managed stability/process era identifier
- `MAJOR.MINOR.PATCH` carries TOAS's SemVer-style meaning inside that epoch

Important clarification:

- `EPOCH` is not SemVer major
- only the trailing `MAJOR.MINOR.PATCH` components carry SemVer-style meaning

### SemVer Meaning Inside An Epoch

Within a given epoch:

- `MAJOR` changes for breaking user-facing changes
- `MINOR` changes for backward-compatible feature additions
- `PATCH` changes for backward-compatible fixes

This is a SemVer-style contract applied inside each epoch. TOAS does not claim
that the full four-component version is plain SemVer.

### Why TOAS Uses An Epoch

The leading epoch exists so process or audience expectations that latch onto
the leftmost version component do not distort the project’s semantic change
classification.

In short:

- `EPOCH` absorbs deliberate stability-era or process-visible transitions
- `MAJOR.MINOR.PATCH` continues to describe the actual product change shape

### Epoch Bump Rules

Change `EPOCH` only for deliberate policy or stability-posture transitions,
such as:

- declaring a new stability era
- resetting external compatibility expectations at a meta level
- changing the support/operational posture in a way that should be visible
  independently of normal SemVer interpretation

Do not change `EPOCH` for ordinary features or fixes.

### Release-Fix Suffix

When TOAS needs an additional cut of the same intended base release, it may use
an operational suffix:

`EPOCH.MAJOR.MINOR.PATCH-rN`

Examples:

- `1.0.3.2`
- `1.0.3.2-r1`
- `1.0.3.2-r2`

Rules:

- `-rN` is a release-fix suffix, not SemVer patch
- use it only for additional cuts of the same base release line
- reset it whenever the base `EPOCH.MAJOR.MINOR.PATCH` changes

## Release Notes

Release notes live under:

- `docs/releases/<full-version>.md`

Examples:

- `docs/releases/1.0.3.2.md`
- `docs/releases/1.0.3.2-r1.md`

Each release note should summarize:

- the released version
- the release date
- headline included changes
- notable fixes
- intentionally excluded or deferred adjacent work when useful for operator
  clarity

Release notes should not be duplicated inline inside the recurring release-run
record. The run record should reference the release note file instead.

## Recurring Release Review Records

Release-review runs belong under:

- `tasks/recurring/runs/`

Each run should record:

- the review date
- the candidate version or release line
- whether the outcome was `cut`, `deferred`, or `skipped`
- the exact git tag name when a release was cut
- the release-note path when a release was cut
- the reason when the release was deferred or skipped

## Non-Goals

This process does not yet define:

- package publication
- installer/distribution channels
- support windows
- artifact signing policy

If TOAS later needs those, they should extend this process through focused
follow-on work rather than by silently stretching the current definition.
