# [id]-[slug]

## Objective
Define and run a long-horizon functional scenario that validates operator outcomes (raison d'etre), not just proximate feature mechanics.

## Why
State the durable operator problem this scenario proves we can handle.

## Scope
In scope:
- Scenario design using the embedded epic template
- One executable acceptance artifact (script/spec) plus assertions
- Evidence capture from transcript/history/event surfaces

Out of scope:
- Exhaustive functional/non-functional matrix coverage
- Unit-level behavior already covered elsewhere

## Inputs
- Target repo/workspace context
- Change request or operator goal
- Relevant roadmap/task references

## Deliverables
- `acceptance/<slug>.md` (filled epic scenario spec)
- `acceptance/<slug>.yaml` or equivalent replay/runner artifact
- Assertion report artifact(s)
- Task updates documenting pass/fail and follow-ons

## Exit Criteria
- Scenario is executable and reproducible
- Success criteria are externally observable and asserted
- At least one interruption/detour path is exercised
- Durable-history invariants are checked
- Follow-on tasks captured for uncovered adjacent risks

## Embedded Template: Functional Epic Scenario
Use this template to author the concrete scenario file.

```md
# Epic Scenario: <short title>

## Why
What operator outcome this proves (raison d'etre), not feature mechanics.

## Change Request
Concrete repo-level request to complete.

## Actor / Context
Who is operating, repo state assumptions, constraints.

## Success Criteria
Observable end state:
- code/docs changed as requested
- tests executed with expected result
- commit(s) produced
- task/roadmap stitched
- transcript/history remain coherent and reconstructable

## Long-Horizon Narrative
Turn-by-turn storyline:
1. Intake and clarify request
2. Plan and stage work
3. Implement iteratively
4. Handle interruption/failure/approval
5. Recover and continue
6. Validate and finalize
7. Commit and close loop

## Required Invariants
Durability/semantic guarantees that must hold throughout.

## Evidence to Collect
Commands/views and expected signals (`history`, `heads`, `rebuild`, transcript frontier, queue/intents, commit metadata).

## Failure/Detour Cases
At least 2:
- mid-task interruption
- intent extraction ambiguity / mixed command forms
- backend or tool failure requiring retry/recovery

## Out of Scope
What this scenario intentionally does not validate yet.
```

## First Instantiation Guidance
Start with the foundational epic:
- "Complete a change request on a repository"

Keep first pass thin:
- one realistic change request
- one interruption
- one recovery
- one final commit path

## Tracking
- Status: open | in-progress | blocked | done
- Last run: <date>
- Latest outcome: <pass/fail>
- Follow-ons opened: <task ids>
