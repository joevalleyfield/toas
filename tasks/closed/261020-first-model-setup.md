# First-model setup without configuration scaffolding

Filed as: 261020-first-model-setup
FKA:
AKA: discover then select; initial model onboarding
Legacy index:
keywords: config, model, usability, closed, implementation

Related: `261020-endpoint-state-continuity`; `261020-endpoint-auth-discoverability`

Status: CLOSED 2026-10-20

Operator evidence: `.toas/session-261020-2200-testing-one.md` from line 178.
Discovering one model still requires understanding endpoint defaults, target
creation and active selection. A shortened displayed model ID is not the exact
API identifier. The named-target add form accepts an invalid endpoint reference
and reports success without a usable selected model.

Initial independent repairs:
- Validate named-target endpoint references before reporting success.
- Preserve created targets through transcript configuration reconstitution.
- Keep exact model IDs distinct from readable labels.

UX decision accepted by operator: discover, then select; selection handles
target creation. No manual endpoint default or target naming is required.

## Implementation

- Refresh and known-model views emit ready-to-run `/model select ENDPOINT MODEL`
  commands using unambiguous readable labels, with quoted exact IDs when labels
  collide. Selection resolves the full API ID, creates or reuses its target,
  handles target-name collisions internally, and records active selection.
- Invocation honors the newer selection even after an older target selection.
- Selected durable config updates preserve targets as well as endpoint catalogs.
- Named target creation validates the endpoint before reporting success.
- Endpoint-add output, help and README guide discovery then selection, with
  authentication conditional and endpoint defaults absent from the ordinary path.

Focused checks: 301 tests passed before the final invocation refinements;
latest setup/invocation/continuity module run passed 13; help/setup/continuity
run passed 34. Ruff and mypy pass. Actual isolated CLI artifact was inspected
against a local HTTP server, including streamed assistant output: add endpoint,
refresh, select by basename, send Whatup?, receive assistant response. Captured
POST /v1/chat/completions used the exact `/server/models/Qwen3.8-27B-Q8_0.gguf`
identifier, not its readable basename. Operator transcript/history untouched.

Final validation: full suite **3,586 passed**, eight skipped, 17 deselected,
195.92 seconds, **100.00% coverage**, 23,024 statements and zero missing
statements/files. The check entrypoint's full-suite stage passed; its acceptance
stage exposed stale assertions for the previous scaffolding-oriented help.
Updated those to verify discover/select guidance. Standalone acceptance rerun:
**17 passed** in 6.89 seconds; repository Ruff and mypy pass. Focused help tests
also pass after removing duplicate/advanced choices from the first-setup path.
