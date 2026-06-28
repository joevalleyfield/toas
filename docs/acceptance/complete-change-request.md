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
- `toas history`, `toas heads`, and `toas rebuild` remain coherent with
  narrative within their declared access mode
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

## Scenario Narrative Map (Draft)
This story is executed as bounded transition scenarios in the feature file.
Each scenario has:
- stable ID (`S#`)
- descriptive slug
- quoted scenario title

Draft chapter map:
- `S1` `intake_to_staged_frontier` "Intake to staged frontier"
- `S2` `staged_frontier_to_first_implementation` "Staged frontier to first implementation"
- `S3` `interruption_to_recovered_frontier` "Interruption to recovered frontier"
- `S4` `recovered_frontier_to_validated_change` "Recovered frontier to validated change"
- `S5` `validated_change_to_committed_closure` "Validated change to committed closure"

### S1 intake_to_staged_frontier
**Story intent**
- The operator receives a bounded request, anchors scope, and produces a clean runnable frontier turn.

**Before state**
- Repository workspace exists.
- Acceptance task is open.
- No implementation consequences have run for this request yet.

**Operator actions**
1. Record or confirm bounded request text.
2. Stage initial frontier intent in transcript.
3. Run one `toas step` consequence resolution cycle.

**After state**
- Frontier intent is represented in durable history.
- Resulting projection is coherent and readable.
- Next actionable state is clear (implementation pass can begin).

**Evidence focus**
- Transcript excerpt around staged frontier.
- `history` output showing the newly appended records.

### S2 staged_frontier_to_first_implementation
**Story intent**
- The operator advances from a staged frontier into the first concrete repository modification pass.

**Before state**
- Frontier is staged and runnable.
- Request scope is still bounded and unchanged.
- No closure/commit has occurred.

**Operator actions**
1. Trigger next consequence cycle (`toas step`).
2. Apply first bounded change through normal TOAS flow.
3. Inspect immediate output (diff/result shape) for coherence.

**After state**
- At least one requested repository change is present.
- Durable history captures the step consequence and resulting state progression.
- Workflow remains open for interruption/recovery and additional passes.

**Evidence focus**
- File-level diff excerpt or equivalent changed-file signal.
- `history` output around implementation consequence records.

### S3 interruption_to_recovered_frontier
**Story intent**
- The operator encounters interruption before closure and recovers deterministically using durable TOAS surfaces.

**Before state**
- First implementation pass completed.
- Workflow is not yet validated/committed.
- A realistic interruption point is introduced (approval gate, ambiguity, or context switch).

**Operator actions**
1. Record interruption condition and halt forward execution.
2. Inspect durable state via `history`/`heads` and, if useful, `rebuild`.
   Recovery should not assume silent traversal into sealed cold history unless
   the invoked affordance explicitly declares that access mode.
   `history` should read as the bounded root-to-head lineage view for the
   current default lineage, while `heads` remains the compact branch-tip view.
3. Re-establish a clear runnable frontier and resume.

**After state**
- Operator has regained a trustworthy frontier.
- No semantic drift appears between transcript projection and durable records.
- Workflow is ready for final implementation/validation passes.

**Evidence focus**
- `heads` output if branching was required.
- `rebuild` result (or explicit rationale if rebuild was not required).
- Pre/post frontier excerpts showing successful recovery.

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
