# 469 Functional Acceptance Epic: Complete A Change Request On A Repository

## Objective
Define and execute a long-horizon functional acceptance scenario proving TOAS can take an operator from request intake to validated, committed repository change with durable, reconstructable history.

## Why
This is the foundational raison d'etre scenario: TOAS must reliably help an operator complete real repository work end-to-end, not just expose isolated features.

## Scope
In scope:
- Author one concrete epic scenario spec for this operator outcome
- Implement one executable acceptance artifact (replay/spec runner input)
- Assert externally visible outcomes and durable-history invariants
- Exercise at least one interruption/detour plus recovery path

Out of scope:
- Broad acceptance matrix across all feature families
- Exhaustive non-functional characterization

## Inputs
- Active repo workspace and current roadmap/task context
- One bounded but realistic change request
- Existing replay/history/heads/rebuild observability surfaces

## Deliverables
- `acceptance/complete-change-request.md` (instantiated epic spec)
- `acceptance/complete-change-request.yaml` (or equivalent executable artifact)
- Run artifact(s) proving pass/fail outcomes
- Task/roadmap follow-ons for discovered gaps

## Exit Criteria
- Scenario is reproducible via one documented invocation path
- Scenario demonstrates full cycle: intake -> implement -> validate -> commit
- Interruption/recovery branch is exercised and validated
- Durable-history invariants are checked from external operator surfaces
- Findings are documented and stitched into follow-on tasks as needed

## Embedded Epic Scenario Template (Instantiated)

### Why
Prove TOAS supports durable, interruption-tolerant completion of a real repository change request from transcript-driven operation.

### Change Request
Complete one concrete, bounded repository change request and land it as a commit with validation evidence.

### Actor / Context
Operator working in a local repository through transcript + step semantics, with possible mixed intents and at least one interruption.

### Success Criteria
- Requested repository change lands correctly
- Verification commands/tests succeed (or expected failures are explicitly handled)
- Commit is produced with coherent message and scope
- Transcript and event history remain coherent and rebuild-safe
- `history`/`heads`/`rebuild` signals remain consistent with operator narrative

### Long-Horizon Narrative
1. Intake and clarify request
2. Plan and stage approach
3. Implement in bounded passes
4. Encounter interruption/detour and handle it
5. Recover state and continue
6. Validate outcomes
7. Commit and close loop

### Required Invariants
- Append-only durable history
- Branch-not-undo semantics for non-tip continuation
- Message/control/tool/model records remain distinct
- Projection does not mutate durable facts

### Evidence To Collect
- Transcript frontier before/after key steps
- `toas history`, `toas heads`, `toas rebuild` outputs/signals
- Validation command results
- Commit metadata and changed-file scope

### Failure/Detour Cases
- Mid-task interruption before completion
- Mixed intent/command staging ambiguity requiring explicit recovery action

### Out Of Scope
- Multi-repo routing and cross-session orchestration breadth
- Full arbitration policy matrix

## Tracking
- Status: in-progress
- Last run: 2026-05-02 (`uv run pytest tests/acceptance/steps/test_complete_change_request_steps.py -q --no-cov`)
- Latest outcome: thin executable pytest-bdd path passing (1 passed)
- Follow-ons opened: none yet

## Progress Notes
- Draft scenario spec authored in `docs/acceptance/complete-change-request.md`
- Gherkin scenario scaffold authored in `tests/acceptance/features/complete_change_request.feature`
- First executable step binding landed in `tests/acceptance/steps/test_complete_change_request_steps.py` using `pytest-bdd`
- Added acceptance harness mode controls for backend sourcing (`replay_only|live_only|hybrid`) with cutover selectors (`live_from_step`, `live_from_label`) and replay fixture strictness
- Acceptance staging now supports heavy-mode git snapshot materialization (`TOAS_ACCEPTANCE_WORKSPACE_MODE=git_snapshot` with `TOAS_ACCEPTANCE_SOURCE_REPO` + `TOAS_ACCEPTANCE_SOURCE_REF`) while retaining scratch-mode defaults
- Scenario sequence now exercises TOAS-native operator controls during setup (`/config set generation.thinking_mode disabled`) before implementation passes, reducing operator-prose shaping and increasing affordance realism
