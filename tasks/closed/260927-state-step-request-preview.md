Filed as: 260927-state-step-request-preview
FKA:
AKA: state-step LLM request preview; step preview request
Legacy index:

keywords: runtime, projection, implementation, historical, observability

Parent: `260926-state-step-requirements`
Related: `260927-state-step-raw-response`

# Preview The State-Step Model Request

## Objective

Provide a no-generation invocation of `step` that constructs and prints the
request messages that state-step inference would hand to the model-generation
service.

## Completion

`toas step --preview` now shares the state-packet builder with ordinary
state-step inference and prints a JSON envelope containing `phase` and
`request_messages`. It makes no model call and does not advance the state-step
transition. If the next normal step would execute a pending tool batch or stop
at a completed terminal state, preview reports that phase instead of
constructing a fictitious inference request.

The implementation was exercised against the current session with
`PYTHONPATH=src .venv/bin/python -m toas step --preview`; it printed the
current inference request. Syntax compilation and `git diff --check` passed.
The test suite was not run for this focused change.

This is the TOAS request-message projection before provider-specific transport
shaping. The formula and invocation are documented in
[`docs/llm-notes.md`](../../docs/llm-notes.md).

Status: CLOSED — request preview implemented.
