# Release Review Weekly Tagged Lane: 2026-06-28

Template: `tasks/recurring/templates/release-review-weekly-tagged-lane.md`
Outcome: `cut`
Candidate version: `0.0.0.0`
Git tag: `0.0.0.0`
Release notes: `docs/releases/0.0.0.0.md`

## Trigger

Manual first exercise of the lightweight release process after the release lane
and routine check posture were documented.

## Inputs Reviewed

- `docs/release-process.md`
- `docs/checks.md`
- `docs/roadmap.md`
- `tasks/WORKBOARD.md`
- `tasks/open/260627-release-process-and-weekly-release-lane.md`
- recent landed `feat` and behavior-changing `fix` commits in the current
  no-prior-tag release window

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

- sandbox attempt: failed because the execution wrapper denied local socket
  binds and Vim home-file writes
- unsandboxed rerun: passed
- default pytest: `2458 passed, 17 deselected`
- coverage: `100.00%`
- replay-only acceptance: `9 passed`

## Release Slice

This first release has no prior release tag, so the slice is the current stable
checkpoint rather than a delta from an earlier tagged baseline.

Included headline work:

- LLM backend driver protocol and Gemini REST support
- Gemini request compatibility fixes
- host startup import warmup for LLM paths
- replay-only acceptance revival in the routine check gate
- explicit local check posture documentation
- transcript writeback surface unification and `rebuild` removal
- packet-inclusive `toas llm-input --envelope`
- task/workboard/roadmap governance refinements

## Notes

`0.0.0.0` is used as the first release-process version because there were no
existing TOAS release tags and the documented process maps cleanly to
`EPOCH.MAJOR.MINOR.PATCH`: epoch `0` plus SemVer `0.0.0`.

Package publication, hosted CI, and helper automation were intentionally not
included in this cut.
