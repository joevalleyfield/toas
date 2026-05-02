# 471/465 Loop 1 Scorecard

## 471 Loop 1: shape contract guardrail
Artifact: `docs/acceptance/spikes/471-loop1-shape-contract-session.md`

- shape_ok: partial
- payload_executable: partial
- repo_grounded: low
- operator_load: medium
- recovery_cost: medium

Notes:
- explicit response-shape contract reduced freeform drift.
- model still tends toward weakly grounded discovery/planning operations rather than direct targeted file edits.
- improvement over prose-only drift, but still below "close-enough real change" threshold.

## 465 Loop 1: control-lane parser probe
Artifact: `docs/acceptance/spikes/465-loop1-control-lane-probe-session.md` (run aborted at parse)

- shape_ok: n/a (parser rejection)
- payload_executable: n/a
- repo_grounded: n/a
- operator_load: low (fast feedback)
- recovery_cost: low

Observed failure:
- `ValueError: invalid transcript marker at line 1: '## TOAS:CONTROL'`

Signal:
- confirms `465` starts at transcript parser + marker semantics (slice 1) before any execution/projection behavior can be evaluated.
