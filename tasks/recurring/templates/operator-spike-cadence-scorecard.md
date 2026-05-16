# Recurring: Operator Spike Cadence and Scorecard

## Purpose
Run an operator-driven spike on a meaningful task implementation path and capture protocol/runtime/tooling signals in a consistent scorecard.

## Trigger
- Weekly while active runtime/protocol work is landing
- Or after major changes to runtime lanes, prompt scaffolding, or tool-call affordances

## Inputs
- Current runbook (`docs/acceptance/spikes/*`)
- One historical or bounded work-unit target
- Current `AGENTS.md` and prompt template selection

## Scorecard
- Date:
- Spike target:
- Runtime lane/path used:
- What succeeded:
- First failure boundary:
- Recovery attempts and outcomes:
- Operator load/friction notes:
- Drift mode observed (if any):
- Actionable follow-ons (task links):

## Output
- Dated run artifact in `tasks/recurring/runs/`
- Linked follow-on tasks for product/runtime fixes only when warranted

## Guardrails
- Keep acceptance proof scope separate from probing scope
- Prefer actionable findings over broad narrative
- Do not reopen closed acceptance tasks without concrete regression evidence
