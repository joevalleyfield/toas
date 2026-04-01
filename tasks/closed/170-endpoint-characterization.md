## Goal

Characterize the live inference endpoint well enough to make agentic workflows build on observed behavior instead of guesswork.

## Scope

- Expand live probe coverage
- Record endpoint quirks that matter for runtime policy
- Define how TOAS should normalize or preserve model response details
- Test structured-output robustness directly

## Why

The runtime now talks to a real local endpoint. Before leaning harder on agentic prompting, TOAS should know what that endpoint reliably does, what it does surprisingly, and which behaviors need normalization.

## Planned Tasks

- `171`: expand harness scenarios and reporting
- `172`: document observed endpoint quirks
- `173`: runtime normalization policy for model responses
- `174`: structured-output robustness probes

## Non-Goals

- No broad multi-provider abstraction push yet
- No benchmark program pretending to be scientific performance work

## Done When

- The harness covers the main response-shape questions relevant to TOAS
- Observed quirks are documented and not trapped in conversation history
- TOAS has an explicit stance on what model response details it records, ignores, or strips
