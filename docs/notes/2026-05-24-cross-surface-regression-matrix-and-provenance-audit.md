# Cross-Surface Regression Matrix And Provenance Audit (Task 561)

## Scope

This note captures concrete multi-surface regression checks and provenance-audit expectations for the currently landed `561` behavior.

## Matrix

1. Explicit surface targeting ignores selected-surface metadata.
- Setup: bind `docs` and `roadmap`, select `roadmap`.
- Action: `toas step --surface docs`.
- Expectation: step reads/writes `docs` transcript only; selected `roadmap` does not override explicit target.

2. Selected/bound surface wins over config transcript path.
- Setup: config override points to path A; selected surface bound to path B.
- Action: default `toas step`.
- Expectation: path B is used.

3. Cross-surface non-interference for step.
- Setup: two bound transcript files with distinct markers.
- Action: step one surface.
- Expectation: untouched surface transcript remains byte-identical.

4. Rebind provenance durability.
- Setup: `toas surface rebind docs --from-head n1 --to-head n9 --reason ...`.
- Expectation: append-only records include `surface_rebind` and corresponding `surface_guardrail` override payload.

## Provenance Audit Expectations

1. Surface mapping state is auditable from append-only records (`surface_bind`, `surface_select`).
2. Continuity-retarget intent is auditable from explicit provenance records (`surface_rebind`, `surface_guardrail` override).
3. Rewrite/parentage authority remains transcript/LCP/lineage walk; provenance records are non-authoritative annotations.
