# 683 Add workboard surfacing for captured parked/inbox threads

## Current Reality
When `capture_task_thread` runs, it creates files under `tasks/open/` or appends items to `tasks/open/inbox.md`. However, it does not update the workboard `tasks/WORKBOARD.md`, meaning the operator or other tools must manually sync or check those directories.

## Desired Reality
Any captured task thread (standalone, blocker, or inbox item) is automatically or programmatically surfaced on `tasks/WORKBOARD.md` under the correct column or list (e.g. under `## 1. Now` or a new section like `## Parked & Inbox`).

## Gap Analysis
We need to add workboard update capabilities to `LocalMarkdownAdapter` or implement automatic header parsing/insertion on `tasks/WORKBOARD.md` inside `route_and_capture`.

## Known Facts
- `tasks/WORKBOARD.md` uses structured comments like `<!-- WORKBOARD:NOW:START -->` and `<!-- WORKBOARD:NOW:END -->`.

## Assumptions
- Automating the workboard update will keep the project's overall status coherent.

## Unknowns
- How to determine the sorting order and keywords tags for newly captured items on the workboard.

## Investigations
- Check existing scripts in `tasks/scripts/` or `scripts/` to see if there is an existing workboard sync utility.

## Models
- Update method: Read `WORKBOARD.md`, find section, insert link `- **[T{id}]** [title] (kind: {kind})`, save.

## Forecasts
- This integration will make captured side-threads immediately visible on the developer's main workboard.

## Risks
- Concurrent updates or bad regex formatting could corrupt `WORKBOARD.md`.

## Transformations
- Extend `LocalMarkdownAdapter` to update `tasks/WORKBOARD.md` on macro/blocker capture.

## Evidence
- Tests confirming `WORKBOARD.md` has the new item added under the correct block marker.

## Decisions
- Update `WORKBOARD.md` using block-based patching within `LocalMarkdownAdapter`.

## Open Fronts
- Removing/syncing items when closed.

## Next Actions
- [ ] Add `## 2. Task Inbox` section with markers to `tasks/WORKBOARD.md` and shift other headers.
- [ ] Update `tasks/scripts/sync_workboard.py` to parse checklist items from `tasks/open/inbox.md` and regenerate the Inbox section.
- [ ] Add `_sync_workboard()` to `LocalMarkdownAdapter` in `src/toas/tasks.py` and call it at the end of `route_and_capture()`.
- [ ] Add tests in `tests/test_tasks_capture.py` asserting the workboard is kept in sync after capture.

