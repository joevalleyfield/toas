## Goal

Establish a full-featured prompt probing framework with documented expectations, failure taxonomy, and remediation playbooks so prompt iteration is evidence-driven.

## Why Now

Live backend work and prompt-variant experimentation now outpace ad-hoc spot checks. TOAS needs a coherent narrative and operational probe workflow tying together harness outputs, prompt assets, and policy decisions.

## Scope

- formalize a scenario taxonomy and failure-mode IDs for prompt probing
- define machine-readable expectations per scenario (shape, collision markers, role-contract checks)
- extend probe workflows to report:
  - pass/fail per expectation
  - failure mode IDs
  - recommended remediation actions
- add scenario packs for:
  - command-lane role clarity
  - provider-collision vocabulary tests
  - strict-shape compliance
  - transport/policy interaction checks

## Intended Inputs

- `src/toas/llm_harness.py`
- prompt assets in `src/toas/prompts/protocol/...`
- narrative notes in `docs/llm-notes.md` and `docs/protocol-notes.md`
- taxonomy narrative in `docs/prompt-probing-taxonomy.md`

## Intended Outputs

- repeatable prompt-probing workflow with explicit expectations
- human-readable narrative docs and machine-readable result artifacts
- “what to try next” guidance when probes fail

## Constraints

- keep probe behavior explicit and reproducible
- avoid backend-specific hardcoding where generic checks suffice
- preserve current harness capability while extending output structure

## Non-Goals

- no automatic prompt rewriting by TOAS
- no claim of universal backend behavior from one model run

## Done When

- scenario taxonomy is documented and referenced by probe outputs
- each scenario reports expectation-level pass/fail and failure-mode IDs
- remediation guidance is included in summarized results
- tests cover expectation evaluation and report shaping logic
