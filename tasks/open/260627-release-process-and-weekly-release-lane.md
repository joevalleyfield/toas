Filed as: 260627-release-process-and-weekly-release-lane
FKA:
AKA: release cadence; weekly release review; tagged release process; release lane
Legacy index:

keywords: docs, governance, inception, release, schedule, cadence, process

# Release Process And Weekly Release Lane

## Current Reality

TOAS has strong task, roadmap, workboard, and recurring-maintenance discipline,
but it does not yet have an explicit release process or release schedule.

There is no repo-native definition of what counts as a release, what inputs
must be checked before one is cut, how skipped weeks should be recorded, or
where recurring release review should live.

## Desired Reality

TOAS should have a lightweight, explicit release lane that fits existing
project conventions.

For this first pass, a TOAS release should mean:

- a git tag
- a short release record or notes summary
- a bounded verification pass and planning-hygiene check before the tag is cut

The default operating rhythm should be a weekly release review, with optional
out-of-band milestone releases when a coherent slice lands before the next
weekly window.

## Gap Analysis

Without a release process, the project has a few coordination gaps:

- meaningful checkpoints can land without a shared rule for when to tag them
- release-worthy state can depend on memory rather than a checklist
- skipped or deferred release windows have no durable record
- release cadence can become ad hoc instead of using the same recurring lane
  conventions already used elsewhere in the repo

This task exists to close those process gaps without prematurely committing to
packaging, publication, or distribution work.

## Known Facts

- `tasks/README.md` defines the current open/closed task conventions and
  keyword vocabulary.
- `tasks/recurring/README.md` defines recurring templates and dated run
  records as the preferred shape for repeatable maintenance processes.
- Existing recurring templates use short sections such as `Purpose`,
  `Trigger`, `Inputs`, `Checklist`, and `Output`.
- `docs/roadmap.md` already tracks recurring maintenance lanes that were
  normalized out of umbrella-task form.
- `tasks/WORKBOARD.md` is the operational board and should surface this task
  through normal sync/update flow rather than through a parallel release board.

## Assumptions

- A v1 TOAS release is a git-tagged checkpoint, not a packaged or published
  distribution artifact.
- Weekly cadence is enough structure for now; tighter cadence would add process
  overhead without clear evidence of need.
- Extra milestone-triggered releases are allowed when a coherent slice lands.
- A scheduled release review may end in `cut`, `deferred`, or `skipped`
  outcome, and not every weekly review should force a tag.
- The recurring release-review mechanism should live under
  `tasks/recurring/templates/` and `tasks/recurring/runs/`.

## Unknowns

- What exact version/tag naming convention TOAS should standardize on.
- Whether release notes should live only in dated recurring run records or also
  in a separate changelog-like surface.
- What minimum verification command set should be required beyond the current
  full-suite norm when the first real release is cut.
- Whether future packaging/publishing work should extend this lane or spawn a
  separate follow-on task.

## Investigations

- Review the existing recurring templates and align the release-review lane to
  their structure and tone.
- Define the minimum release gate inputs that are already consistent with TOAS
  practice:
  - task hygiene
  - roadmap/workboard hygiene
  - verification run
  - concise release summary
- Decide how a no-release week is recorded so cadence remains durable without
  manufacturing releases.
- Confirm whether roadmap/workboard references are sufficient for visibility or
  whether later tooling follow-up is needed.

## Models

Working process model:

```text
weekly release review
  -> inspect task/roadmap/workboard state
  -> verify bounded release gate inputs
  -> decide cut / deferred / skipped
  -> if cut, create git tag and short release record
  -> if not cut, preserve a dated run record explaining why
```

This keeps release cadence explicit without turning release work into a large
standing umbrella.

## Forecasts

- A lightweight weekly review lane should make project checkpoints easier to
  communicate without adding much overhead.
- Clear skipped/deferred outcomes should reduce pressure to cut thin releases.
- If TOAS later grows packaging or distribution needs, this task should expose
  the right follow-on seam rather than requiring the release process to be
  reinvented.

## Risks

- Defining the lane too broadly and quietly turning this into packaging work.
- Requiring so much verification/process ceremony that weekly review becomes
  performative and stops running.
- Treating any notable merge as automatically release-worthy.
- Letting release records drift into a second roadmap rather than a concise
  operational log.

## Transformations

- Open a release-process coordination task that makes release semantics and
  cadence explicit.
- Add a recurring weekly release-review template under `tasks/recurring/`.
- Update `docs/roadmap.md` so release-process work is visible in normal
  planning surfaces.
- Keep implementation intentionally narrow: define the lane now, and leave
  packaging/publishing/distribution as future work only if justified.

## Evidence

This task will be complete when:

- an open task exists describing the release-process scope and boundaries
- a recurring release-review template exists under `tasks/recurring/templates/`
- roadmap language reflects release-process work as an open governance lane
- the task clearly distinguishes tagged releases from packaged distribution
  concerns
- the defined recurring lane can record `cut`, `deferred`, and `skipped`
  outcomes cleanly

## Decisions

- Define a v1 TOAS release as a git tag backed by a short release record.
- Use weekly release review as the baseline cadence.
- Allow out-of-band milestone releases when a coherent slice lands.
- Record scheduled review outcomes even when no tag is cut.
- Establish the recurring release-review lane immediately rather than leaving
  it as an implied future follow-on.

## Open Fronts

- Choose and document a tag/version naming convention when the first real
  release is prepared.
- Decide whether release records alone are enough or whether a separate
  changelog surface becomes worthwhile later.
- Determine whether future publishable artifacts should extend this lane or sit
  behind a separate task.

## Next Actions

- Create `tasks/recurring/templates/release-review-weekly-tagged-lane.md`.
- Add a concise roadmap note that this release-process lane is now open.
- Run the normal workboard sync path when task-surface regeneration is next
  performed so this task appears in the operational board.
- Use the first recurring run to prove the template can represent `cut`,
  `deferred`, or `skipped` without ambiguity.
