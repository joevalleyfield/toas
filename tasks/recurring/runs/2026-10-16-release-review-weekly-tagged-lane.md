# Release Review Weekly Tagged Lane: 2026-10-16

Template: `tasks/recurring/templates/release-review-weekly-tagged-lane.md`
Outcome: `cut`
Candidate version: `0.0.4.0`
Git tag: `0.0.4.0`
Release notes: `docs/releases/0.0.4.0.md`

## Trigger

Release review after the post-`0.0.3.0` slice—spanning state-shaped execution,
model endpoints and targets, topic guidance, and frontier resilience—reached a
coherent checkpoint.

## Inputs Reviewed

- `docs/release-process.md`
- `docs/checks.md`
- `docs/roadmap.md`
- `tasks/WORKBOARD.md`
- `tasks/open/260627-release-process-and-weekly-release-lane.md`
- Landed `feat` and behavior-changing `fix` commits since `0.0.3.0` (269 commits).

## Checklist

- [x] Candidate fits the v1 definition: git tag plus short release record, not
  packaging or publishing.
- [x] The release slice contains substantial `feat` and behavior-changing `fix`
  work across 269 landed commits, so it is release-eligible.
- [x] Task, roadmap, and workboard state were reviewed for obvious misleading
  planning state in the release slice.
- [x] Required verification completed for the candidate state.
- [x] Headline included changes, the state-shaped tech preview status, and deferred
  adjacent work are summarized in `docs/releases/0.0.4.0.md`.
- [x] Outcome decided: `cut`.

## Verification

Routine gate:

```text
scripts/check.sh
```

Result: passed outside the sandbox on the candidate commit.

- default pytest: `3511 passed, 17 deselected` with 100.00% statement coverage
  (22,781 statements covered, 0 missing files).
- replay-only acceptance: `17 passed`.
- `ruff check src tests`: passed cleanly.
- `mypy`: passed across 151 source files.
- Operator-perspective review: confirmed CLI help, prompt assets, and request preview
  formatting are clean, self-describing, and contract-aligned.

## Release Slice

Included headline work:

- State-shaped execution and frontier protocol technology preview (typed state transcripts,
  proposal scoping, reference handles, and terminal reporting).
- Canonical model endpoints and named target infrastructure and workflows.
- Modular runtime help topic facets, guidance asset loading, and config overview navigation.
- Lossless fence retry materialization, branch policy programs, and assistant source reference recovery.
- Batch tool try-all mode, read_file soft bounds/clean EOF truncation, and subprocess stdout isolation.

## Notes

`0.0.4.0` advances the SemVer-style `MINOR` component inside epoch `0` because
the release window adds substantial backward-compatible operator capabilities.

State-shaped execution is explicitly flagged as a **tech preview** in the release
notes: it has landed and is active for evaluation and experimentation, but is
not recommended yet as the primary work-surface.
