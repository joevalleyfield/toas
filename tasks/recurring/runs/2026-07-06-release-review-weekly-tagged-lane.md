# Release Review Weekly Tagged Lane: 2026-07-06

Template: `tasks/recurring/templates/release-review-weekly-tagged-lane.md`
Outcome: `cut`
Candidate version: `0.0.1.0`
Git tag: `0.0.1.0`
Release notes: `docs/releases/0.0.1.0.md`

## Trigger

Weekly release review for the first full release window after the initial
`0.0.0.0` tagged cut.

## Inputs Reviewed

- `docs/release-process.md`
- `docs/checks.md`
- `docs/roadmap.md`
- `tasks/WORKBOARD.md`
- `tasks/open/260627-release-process-and-weekly-release-lane.md`
- landed `feat` and behavior-changing `fix` commits since `0.0.0.0`

## Checklist

- [x] Candidate release fits the v1 definition: git tag plus short release
  record, not packaging or publishing.
- [x] Task, roadmap, and workboard state reviewed for obvious misleading
  planning state in the release slice.
- [x] Required verification completed for the candidate state.
- [x] Headline included changes and deferred adjacent work summarized in
  release notes.
- [x] Outcome decided: `cut`.

## Verification

Routine gate:

```text
scripts/check.sh
```

Result:

- sandbox attempt: failed because the execution sandbox denied local socket
  binds and Vim home-file writes
- unsandboxed rerun: passed
- default pytest: `2604 passed, 17 deselected`
- coverage: `100.00%`
- replay-only acceptance: `9 passed`
- `ruff check src tests`: passed
- `mypy`: passed

## Release Slice

This window covers landed changes since tag `0.0.0.0`.

Included headline work:

- segmented event-index stitching and logical-history graph projection
- hot-default history, heads, transcript, and llm-input behavior
- selected-source graph/projection anchors, diagnostics, and neighborhood
  controls
- root-divergence salvage tooling and sentinel-parent runtime handling
- routine gate tightening with lint and type checks
- planning/task refinements around history affordances and transcript-parallel
  capability seams

## Notes

`0.0.1.0` advances the SemVer-style `MINOR` component inside epoch `0`
because the release window contains multiple backward-compatible feature
additions, with fixes folded into the same coherent slice.

Packaging/publication, hosted CI, and release-helper automation remain out of
scope for this cut.
