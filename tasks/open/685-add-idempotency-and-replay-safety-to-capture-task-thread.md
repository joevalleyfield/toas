# 685 Add idempotency and replay safety to capture_task_thread

## Current Reality
When `toas step` replay runs, or if an assistant repeats tool calls, calling `capture_task_thread` multiple times with identical inputs results in duplicate files being written to `tasks/open/`, duplicate bullet points appended to the parent task sections, and duplicate events written to `tasks/events.jsonl`.

## Desired Reality
`capture_task_thread` is completely idempotent. If a task thread with the same signature (same parent task, same kind, and same title or matching `capture_id` if provided) has already been logged, the tool resolves to the existing record. It does not re-create standalone task files, does not duplicate checklist items, does not append duplicate ledger events, and returns the original outcome/directives.

## Gap Analysis
Currently, `route_and_capture` generates a new UUID `capture_id` and performs the file edits on every call without checking the ledger or the file system for prior duplicates. We need to scan `tasks/events.jsonl` for a matching event (by checking title/kind/active_task_id or an explicit incoming idempotency key/hash of title+kind) and skip filesystem changes if a match is found.

## Known Facts
- UUID is generated using `uuid.uuid4().hex[:12]` inside the tool right now.
- Replays process existing history events linearly.

## Assumptions
- A hash of `(active_task_id, kind, title)` can serve as a robust signature for deduplication if an explicit `capture_id` or idempotency key is not passed.

## Unknowns
- How to handle cases where the operator updates/changes the content of a previously captured task on a subsequent retry (do we overwrite, skip, or version?).

## Investigations
- Investigate how TOAS identifies duplicate tool results downstream in `step.py` and `graph.py`.

## Models
- Define a signature/hash calculator for event comparison: `hash(active_task_id + title + kind)`.

## Forecasts
- Idempotency will make the tool safe for execution loops, reducing directory bloat and git diff noise.

## Risks
- False positives in deduplication could suppress separate task captures if their titles are identical.

## Transformations
- Modify `route_and_capture` to first query the ledger/adapter for an existing match before executing routing.

## Evidence
- Integration tests demonstrating that calling the tool twice sequentially with the same arguments creates only one file and one ledger entry.

## Decisions
- Deduplicate based on `(active_task_id, kind, title)` signature matching within the ledger.

## Open Fronts
- Hand-off/recovery of manual updates made to task files before a replay.

## Next Actions
- [ ] Add `find_existing_event(self, title: str, kind: str, active_task_id: Optional[str], capture_id: Optional[str] = None) -> Optional[TaskCaptureEvent]` to `TaskTrackerAdapter` and `LocalMarkdownAdapter`.
- [ ] Add `verify_physical_outcome(self, outcome: TaskCaptureOutcome) -> bool` to `LocalMarkdownAdapter` to check physical presence of files/items.
- [ ] Update `route_and_capture` deduplication flow: check for existing ledger event, if found check physical outcome, if missing recreate them without duplicate ledger log.
- [ ] Add `capture_id` option to the tool definition in `src/toas/tools.py`.
- [ ] Add idempotency and physical recovery tests in `tests/test_tasks_capture.py`.

