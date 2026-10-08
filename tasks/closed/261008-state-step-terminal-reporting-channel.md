# State-Step Terminal Reporting Channel and Completion Projection

Filed as: 261008-state-step-terminal-reporting-channel
FKA:
AKA: state step user response; state goal reporting channel; state completion projection; terminal outcome payload
Legacy index:

keywords: runtime, contract, active, usability, transcript, frontier, projection

Parent: `260926-state-step-requirements`
Depends on: `261008-scope-pending-state-transitions`
Related: `261007-state-protocol-tool-argument-definitions`; `260928-state-user-control-turn-lifecycle`

Status: CLOSED; defined and implemented user-facing reporting channel for state-step with completion projection in transcripts and CLI output.

## Context

In state-step transcripts (e.g. `session-20261007-1946-state-seed.md`), when a user issues a command such as `List open tasks.`, the model drives tool calls across turns until the investigation concludes. At Turn 7, the model planned:
```yaml
next_steps:
- Report the list of open tasks to the user.
- Mark the goal as complete.
```
However, the state protocol (`toas.state-step/1`) previously restricted the response schema to:
```yaml
schema:
  state_patch: object
  tool_calls:
  - tool_name: string
    args: object
  outcome:
  - continue
  - complete
```
There was no top-level `answer`, `report`, or `message` channel in the response contract, nor a dedicated reporting tool. As a result:
1. The model was forced to bury user-facing answers inside internal `state.notes` or `state.progress`.
2. When the model reached `outcome: complete`, there was no mechanism to project the final findings or summary to the operator.
3. The operator had to manually inspect the raw YAML state dump rather than receiving a clear, synthesized response.

## Objectives

1. **Define Protocol Response Channel**:
   - Update `toas.state-step/1` instructions and schema to include an explicit user-facing answer/report channel (optional `report: string` alongside `outcome: complete` / `state_patch`).
2. **Project Terminal Outcome in Transcripts**:
   - When `outcome: complete` is returned (or an intermediate report is emitted), project the report cleanly into the transcript or user-facing output so the operator receives the direct answer to their goal.
3. **Align Model Instructions**:
   - Instruct models how to conclude goals: provide the final synthesized findings in the report field rather than deferring to a non-existent reporting tool or next step.
4. **Validation and Testing**:
   - Add unit and transcript tests verifying report generation, validation, and projection upon goal completion.
   - Maintain 100.00% statement coverage and clean linting.

## Outcome

- Updated `toas.state-step/1` protocol schema and prompt instructions (`instructions_v1.txt`, `swe_v1.yaml`, `state_step.py`) to advertise `report: string` as an optional response field for user-facing synthesis and terminal reporting.
- Updated `render_state_turn` and `parse_state_turn` to handle `report` and `outcome`, preserving multi-line reports using YAML block scalar formatting (`|-`).
- Updated `StateHistoryPoint` and `state_transition` record persistence to capture `report` and `outcome` durably in `events.jsonl`.
- Updated `cli_session_commands._run_state_step` to project terminal completion messages (`[COMPLETED] state goal completed\n\n<report>`) into the transcript and stdout stream under `## TOAS:USER\n\n## RESULT`.
- Added comprehensive unit and CLI regression tests in `tests/test_state_step.py` and `tests/test_cli_session_commands_state_step.py`.
- Verified end-to-end artifact inspection (`toas prompt state/swe_v1`) and full check suite (`./scripts/check.sh`) with 100.00% statement coverage.
