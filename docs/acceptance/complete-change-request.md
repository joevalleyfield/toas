# Epic Scenario: Complete A Change Request On A Repository (Draft v1)

## Why
Prove TOAS supports end-to-end repository work as an operator system: intake, implementation, interruption handling, recovery, validation, and commit closure with durable/reconstructable history.

## Change Request
Apply one bounded repository change request that requires at least:
- one code/doc edit
- one verification run
- one commit

For draft v1, we will choose a scoped request that is realistic but unlikely to require broad refactors.

## Actor / Context
- Actor: single operator using TOAS transcript-first workflow
- Workspace: local git/jj repository with existing task/roadmap discipline
- System assumptions:
  - `toas step` resolves one frontier consequence at a time
  - durable history is append-only in `events.jsonl`
  - transcript is operator-controlled and may be edited between steps

## Success Criteria
- Requested change lands correctly in the repo
- Verification signal is captured (pass or explicitly documented expected fail)
- Commit is produced and traceable to scenario scope
- `toas history`, `toas heads`, and `toas rebuild` remain coherent with narrative
- Interruption/recovery path is exercised without losing intent or corrupting projection

## Long-Horizon Narrative (Operator Walkthrough Draft)
1. Intake and framing
- Open/confirm target request and boundaries
- Create or reference task entry for the request
- Record initial operator intent in transcript

2. Plan and initial frontier staging
- Stage a frontier turn describing the next bounded action
- Run `toas step`
- Inspect resulting projection and extracted intents

3. Implement pass 1
- Execute first bounded change via normal TOAS flow
- Validate immediate local effect (file diff / command output)

4. Inject interruption/detour
- Introduce a realistic interruption before closure (for example: approval gate, conflicting intent, or operator context switch)
- Resolve interruption explicitly using available control surfaces

5. Recover and continue
- Resume from durable state using `history`/`heads`/`transcript`/`rebuild` as needed
- Continue implementation with at least one additional bounded pass

6. Validate and finalize
- Run scenario verification command(s)
- Confirm no unresolved queue/intent residue blocks closure

7. Commit and close
- Produce final commit with scoped message
- Update related task tracking and scenario status

## Required Invariants
- No mutation of prior durable entries
- Non-tip continuation uses explicit lineage, not implicit undo
- Message/control/tool/model-call records remain semantically distinct
- Projected transcript content is derived from durable history, not hidden mutable state

## Evidence To Collect
- Before/after transcript frontier snapshots (short excerpts)
- `toas history` outputs around key boundaries
- `toas heads` output if branching occurs
- `toas rebuild` signal at least once during recovery path
- Verification run output summary
- Final commit id and touched files

## Failure / Detour Cases (Required In This Scenario)
- Case A: Mid-task interruption before completion
  - Expected behavior: operator can resume and complete without semantic drift
- Case B: Mixed-intent or command-shape ambiguity
  - Expected behavior: operator can disambiguate, proceed, and preserve intended execution order

## Out Of Scope (v1)
- Multi-repo routing
- Cross-session orchestration beyond one primary transcript
- Full policy matrix for intent arbitration modes
- Performance benchmarking

## Discovery Checkpoints (Expected Iteration)
- Decide concrete change request used for first executable run
- Decide how interruption is injected deterministically
- Decide minimal evidence artifact format (`.md` only vs `.md` + machine-readable capture)
- Decide whether replay artifact is authored manually first or generated from live run transcript

## Run Notes
- Status: draft
- Last revised: 2026-05-02
- First executable pass: pending
