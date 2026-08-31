# Release Review Weekly Tagged Lane: 2026-08-30

Template: `tasks/recurring/templates/release-review-weekly-tagged-lane.md`
Outcome: `cut`
Candidate version: `0.0.3.0`
Git tag: `0.0.3.0`
Release notes: `docs/releases/0.0.3.0.md`

## Trigger

Weekly release review after the post-`0.0.2.0` action-intent, executable-fence,
and transparent-compaction slice reached a coherent checkpoint.

## Inputs Reviewed

- `docs/release-process.md`
- `docs/checks.md`
- `docs/roadmap.md`
- `tasks/WORKBOARD.md`
- `tasks/open/260627-release-process-and-weekly-release-lane.md`
- landed `feat` and behavior-changing `fix` commits since `0.0.2.0`

## Checklist

- [x] Candidate fits the v1 definition: git tag plus short release record, not
  packaging or publishing.
- [x] The release slice contains substantial `feat` and behavior-changing
  `fix` work across 96 landed commits, so it is release-eligible.
- [x] Task, roadmap, and workboard state were reviewed for obvious misleading
  planning state in the release slice.
- [x] Required verification completed for the candidate state.
- [x] Headline included changes and deferred adjacent work are summarized in
  `docs/releases/0.0.3.0.md`.
- [x] Outcome decided: `cut`.

## Verification

Routine gate:

```text
scripts/check.sh
```

Result: passed outside the sandbox on the candidate commit.

- default pytest: `3051 passed, 9 deselected`
- replay-only acceptance: passed
- `ruff check src tests`: passed
- `mypy`: passed

## Release Slice

Included headline work:

- durable concept-graph compaction artifacts and successor reuse
- canonical ordered action-plan ingress and compound request history
- executable Bash, Python, PowerShell, JSON-callable, and generic interpreter
  fence lanes
- evaluator-backed shell/executable grants and live frontier configuration
- partial-search preservation plus Windows runtime path hardening

## Notes

`0.0.3.0` advances the SemVer-style `MINOR` component inside epoch `0` because
the release window adds multiple backward-compatible operator capabilities.
Fixes are folded into the same coherent slice.

The documented manual lane remains sufficient for this cut. The existing
`260627-release-helper-tooling` follow-on remains the appropriate home for
optional release scaffolding and consistency helpers.
