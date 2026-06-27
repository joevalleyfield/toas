# Recurring: Release Review Weekly Tagged Lane

## Purpose
Run a lightweight release review on a weekly cadence so TOAS can cut
git-tagged releases intentionally, or record why a release was deferred or
skipped.

## Trigger
- Weekly
- Or after a milestone-worthy coherent slice lands before the next weekly
  review window

## Inputs
- `tasks/WORKBOARD.md`
- `docs/roadmap.md`
- open/closed tasks included in the candidate release slice
- verification results for the candidate release state

## Checklist
- Confirm the candidate release still fits the current v1 release definition:
  git tag plus short release record, not packaging/publishing
- Review task, roadmap, and workboard hygiene for the intended release slice
- Confirm the required verification run was completed for the candidate state
- Summarize headline included changes and any intentionally excluded work
- Decide one outcome: `cut`, `deferred`, or `skipped`
- If `cut`, record the tag/version and release summary
- If `deferred` or `skipped`, record the blocking reason or why the window did
  not warrant a tag

## Output
- Dated run artifact in `tasks/recurring/runs/`
- If cut, a git-tagged release backed by a short release record
- Focused follow-on tasks only when the review exposes process or release-gate
  gaps
