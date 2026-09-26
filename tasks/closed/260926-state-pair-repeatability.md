Filed as: 260926-state-pair-repeatability
FKA:
AKA: Qwen repeat run; jj prompt reference
Legacy index:

keywords: exploration, investigation, historical, tooling, usability, evaluation
Parent: `260926-state-step-requirements`
Related: `260926-state-experiment-harness`; `260926-state-experiment-plan-tools`

# Repeat the live state execution comparison

## Objective

Repeat the paired live comparison with the current experiment harness and add a
short jj command reference to model-visible fixture instructions. Compare the
new actions and outcomes with the previous pair to observe run-to-run
variability.

## Acceptance

- The model-visible procedure and generated `AGENTS.md` include a concise jj
  usage reference covering status, full diff, history, focused commit behavior,
  empty working-copy semantics, and previous-commit verification.
- Run state-only and history-plus-state against the local endpoint using the
  same budgets, tools, reviewer policy, and independent evaluator.
- Record matching initial fixture/input fingerprints, configured alias,
  endpoint-returned model identity, per-arm calls/actions, script reviews, and
  evaluator outcomes in the experiment runbook.
- State clearly that another pair is a repeatability observation, not a
  statistical estimate.

## Completion

- Added the jj command reference to the model procedure, repository customs,
  and generated fixture `AGENTS.md`.
- Paired live run:
  `/private/tmp/toas-state-live-repeat-20260926T/pair.json`. Initial fixture
  and model-input hashes matched within the pair; configured alias was
  `qwen3.5-35b-a3b`, and both arms returned
  `Qwen3.8-27B-Q8_0.gguf`. Both arms passed the current evaluator.
- State-only finished in 5 model calls / 8 tool calls; history-plus-state in 4
  model calls / 5 tool calls. Neither needed a reviewed script.
- Comparison with the prior pair shows substantial trajectory variation, but
  the prompt changed to include the jj reference, so this is exploratory and
  not a controlled repeatability estimate.
- Python syntax compilation passed. Tests were not run.
