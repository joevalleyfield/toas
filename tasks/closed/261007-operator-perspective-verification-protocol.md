# Operator Perspective Verification Protocol

Filed as: 261007-operator-perspective-verification-protocol
FKA:
AKA: operator POV verification; mandatory artifact inspection; beyond mechanical coverage
Legacy index:
Parent:
Depends on: `261007-harmonize-state-protocol-composition`
Related:

## Context

Strict mechanical verification (passing all unit/acceptance tests with 100.00% statement coverage via `./scripts/check.sh`) is essential for preventing regressions, but it can create a false sense of closure. Unit tests only assert what the test author thought to check, and can inadvertently canonize defective or amputated contracts (such as omitting tool argument definitions from rendered protocol blocks).

When changes impact user-facing surfaces, transcript formats, prompt templates, protocol representations, or CLI output, mechanical correctness must be paired with end-to-end artifact inspection and deliberate adoption of the operator's perspective.

## Objectives

1. Update `AGENTS.md` to define the verification protocol for user-facing, transcript, prompt, and protocol changes:
   - Mandatory end-to-end artifact inspection (running commands and inspecting concrete rendered outputs rather than relying solely on test mocks/assertions).
   - Operator perspective adoption (actively critiquing rendered artifacts from the operator's point of view for unfulfilled promises, self-describing clarity, and hallucination traps).
2. Ensure the guideline is clear that mechanical test/coverage gates are necessary but not sufficient.

## Outcome

- Updated `AGENTS.md` under `## Verification` with a dedicated section on `Mechanical vs. Operator-Perspective Verification`.
- Formalized mandatory end-to-end artifact inspection (running real commands and evaluating full rendered outputs rather than stopping at test assertions).
- Established the requirement for agents to step into the operator's shoes and critique output for unfulfilled promises, self-describing completeness, and hallucination traps before declaring work complete.

