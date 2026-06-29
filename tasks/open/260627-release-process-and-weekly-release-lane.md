Filed as: 260627-release-process-and-weekly-release-lane
FKA:
AKA: release cadence; weekly release review; tagged release process; release lane
Legacy index:

keywords: docs, governance, active, release, schedule, cadence, process

Related: `260628-project-checks-and-ci-posture`; `260627-release-helper-tooling`

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
- `docs/release-process.md` now records the current release cadence, gate, and
  versioning policy.
- `docs/releases/README.md` now defines the release-notes home and filename
  convention.
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

- What exact first public epoch value TOAS should start from when the first
  release is cut.
- Whether hosted CI alone should ever be sufficient release-gate evidence;
  current policy requires the local routine check set in `docs/checks.md`.
- Whether future packaging/publishing work should extend this lane or spawn a
  separate follow-on task.

## Investigations

- Review the existing recurring templates and align the release-review lane to
  their structure and tone.
- Define the minimum release gate inputs that are already consistent with TOAS
  practice:
  - task hygiene
  - roadmap/workboard hygiene
  - green routine check set
  - concise release summary
- Decide how a no-release week is recorded so cadence remains durable without
  manufacturing releases.
- Confirm whether roadmap/workboard references are sufficient for visibility or
  whether later tooling follow-up is needed.
- Document the versioning policy as `epoch.{semver}` with optional release-fix
  suffixes.

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
- Land contributor-facing release docs:
  - `docs/release-process.md`
  - `docs/releases/README.md`
- Update `README.md` and `docs/roadmap.md` so release-process work is visible
  in normal planning surfaces.
- Keep implementation intentionally narrow: define the lane now, and leave
  packaging/publishing/distribution as future work only if justified.

## Evidence

This task will be complete when:

- an open task exists describing the release-process scope and boundaries
- a recurring release-review template exists under `tasks/recurring/templates/`
- roadmap language reflects release-process work as an open governance lane
- contributor-facing docs describe release cadence, release gate, versioning,
  and release-note location
- the task clearly distinguishes tagged releases from packaged distribution
  concerns
- the defined recurring lane can record `cut`, `deferred`, and `skipped`
  outcomes cleanly

## Decisions

- Define a v1 TOAS release as a git tag backed by a short release record.
- Use weekly release review as the baseline cadence.
- Allow out-of-band milestone releases when a coherent slice lands.
- Treat windows with landed `feat` or behavior-changing `fix` work as release
  eligible by default.
- Record scheduled review outcomes even when no tag is cut.
- Establish the recurring release-review lane immediately rather than leaving
  it as an implied future follow-on.
- Treat a tag as the current stable checkpoint, not merely a periodic snapshot.
- Keep the release gate real: green routine check set, release notes, planning
  hygiene, and no known unresolved regression knowingly stamped as stable.
- Make the git tag exactly equal to the release version string; do not add a
  separate default tag prefix or alias.
- Document TOAS versioning as `epoch.{semver}`:
  - public shape: `EPOCH.MAJOR.MINOR.PATCH`
  - internal additional-cut suffix: `-rN`
- Keep release notes as separate artifacts under `docs/releases/`, referenced
  by recurring run records rather than duplicated there.

## Open Fronts

- The release gate's check evidence now resolves through
  `260628-project-checks-and-ci-posture` and `docs/checks.md`: green means the
  local routine check set passed. Hosted CI remains a possible future mirror,
  not the current source of truth.
- The first release review exercised the lane on 2026-06-28 with candidate
  version `0.0.0.0`, release notes at `docs/releases/0.0.0.0.md`, and run
  record `tasks/recurring/runs/2026-06-28-release-review-weekly-tagged-lane.md`.
- Decide whether future changelog aggregation is worthwhile beyond individual
  release note files.
- Determine whether future publishable artifacts should extend this lane or sit
  behind a separate task.

## Next Actions

- Use later weekly reviews to prove `deferred` and `skipped` outcomes without
  manufacturing release tags.
- Let `260627-release-helper-tooling` absorb any release-review mechanics that
  remain annoying after this manual cut.
