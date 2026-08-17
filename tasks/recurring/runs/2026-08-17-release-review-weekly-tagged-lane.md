# Release Review Weekly Tagged Lane: 2026-08-17

Template: `tasks/recurring/templates/release-review-weekly-tagged-lane.md`
Outcome: `cut`
Candidate version: `0.0.2.0`
Git tag: `0.0.2.0`
Release notes: `docs/releases/0.0.2.0.md`

## Trigger

Out-of-band release review after the accumulated post-`0.0.1.0` feature and
fix slice reached a coherent stable checkpoint.

## Inputs Reviewed

- `docs/release-process.md`
- `docs/checks.md`
- `docs/roadmap.md`
- `tasks/WORKBOARD.md`
- `tasks/open/260627-release-process-and-weekly-release-lane.md`
- landed `feat` and behavior-changing `fix` commits since `0.0.1.0`

## Checklist

- [x] Candidate fits the v1 definition: git tag plus short release record, not
  packaging or publishing.
- [x] The release slice contains 32 `feat` commits and 24 `fix` commits across
  126 landed commits, so it is release-eligible.
- [x] Task, roadmap, and workboard state were reviewed for obvious misleading
  planning state in the release slice.
- [x] Required verification completed for the candidate state.
- [x] Headline included changes and deferred adjacent work are summarized in
  `docs/releases/0.0.2.0.md`.
- [x] Outcome decided: `cut`.

## Verification

Routine gate:

```text
scripts/check.sh
```

Result: passed outside the sandbox on the candidate commit.

- default pytest: `2877 passed, 9 deselected`
- replay-only acceptance: passed
- `ruff check src tests`: passed
- `mypy`: passed

## Release Slice

Included headline work:

- LLM compaction projections, durable procedure state, and append-only
  successor-session rotation
- automatic hot-journal rollover and recovery behavior
- activity-health policy, summaries, observer metrics, and Vim reporting
- hardened local-host/Vim cancellation, subscription, terminal projection, and
  transcript rendering behavior
- YAML plan salvage/coalescing and safer tool-write behavior

## Notes

`0.0.2.0` advances the SemVer-style `MINOR` component inside epoch `0` because
this release window contains substantial backward-compatible feature additions,
with fixes folded into the same coherent slice.

The manual process was sufficient to cut this release. The existing
`260627-release-helper-tooling` follow-on remains the home for optional
scaffolding and consistency helpers; no opaque one-command release automation
was introduced here.
