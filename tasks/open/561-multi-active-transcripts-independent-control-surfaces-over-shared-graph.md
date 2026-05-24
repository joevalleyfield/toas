# 561: Multi-Active Transcripts as Independent Control Surfaces Over Shared Graph

## Why

TOAS currently centers a single primary transcript surface (`session.md`) per working context.
As operator workflows diversify (e.g. docs-keeper, roadmap keeper, focused maintenance lanes), we need multiple simultaneously active transcript surfaces that can each act as an authored working/control artifact over the same underlying causal graph.

Without an explicit multi-surface model, independent continuities can accidentally inherit lineage from unrelated transcript work, weakening provenance and increasing the chance of subtle continuity corruption.

## Sequencing Note

This task should not be implementation-started until `550` (root sentinel taxonomy unification) is landed.
Creating this task now is intended to capture scope and design direction so implementation can begin immediately after `550`.

## Goal

Support multiple concurrently active transcript files (for example `session-docs-keeper.md`, `session-roadmap.md`) as independent authored surfaces over a shared graph while preserving transcript-first semantics and preventing accidental lineage inheritance across unrelated continuities.

## Scope

- Define transcript identity/continuity semantics for multiple active transcript surfaces without requiring explicit branch metadata in authored transcript files.
- Preserve LCP-based reconciliation as the continuity inference mechanism per transcript surface.
- Ensure surface-local divergence, reproject, and rebind operations preserve provenance in durable history.
- Introduce guards that prevent cross-surface accidental lineage carryover when continuity is unrelated.
- Specify CLI/runtime behavior for selecting and stepping distinct active transcript surfaces.

## Non-Goals

- Replacing transcript-first semantics with graph-authored branch metadata.
- Introducing hidden loop semantics.
- Retrofitting every historical workflow in one migration pass.

## Proposed Direction

1. Transcript surfaces are first-class authored artifacts with stable surface identity in runtime/durable records.
2. Continuity for each surface is inferred from transcript evolution via LCP reconciliation, not explicit branch pointers in the transcript text.
3. Shared graph extraction remains downstream of transcript evolution: graph follows transcript updates, not vice versa.
4. Rebind/reproject operations must carry explicit provenance records to show when a surface intentionally changes continuation target.
5. Runtime safeguards detect probable unrelated continuity inheritance and require explicit operator intent before attaching lineage.

## Invariants (Target)

1. Multiple transcript surfaces may be active concurrently against shared graph state without implicit coupling.
2. Continuity inference remains transcript-driven and LCP-based per surface.
3. Unrelated transcript continuities do not inherit lineage implicitly.
4. Durable history retains auditable provenance for surface-local continuation and rebind transitions.
5. Existing single-surface behavior remains compatible as a degenerate case of the multi-surface model.

## Landed So Far

1. [x] Design contract captured in `docs/notes/2026-05-24-multi-active-transcript-surfaces-design.md`.
2. [x] On-the-fly transcript targeting for all step entry paths:
   - `toas step --session <transcript_path>`
   - `toas step --stdin --session <transcript_path>`
   - `toas step --control <slash_command> --session <transcript_path>`
   - `toas step --async --session <transcript_path>`
3. [x] Host transport session targeting:
   - `toas host serve --session <transcript_path>` host default
   - request payload `session` / `session_path` accepted for async step lifecycle
   - precedence contract documented and implemented: `request > host default > durable selection > config`
4. [x] Bootstrap compatibility remains intact when `events.jsonl` is absent (first step on targeted transcript path can initialize history).

## Remaining Work

1. [ ] Durable surface mapping records in history (`surface_bind`, `surface_select`) and query helpers.
2. [ ] First-class CLI surface family (`toas surface list|bind|select`) over durable records.
3. [ ] `toas step --surface <surface_id>` resolution via durable mapping (ergonomic layer over raw path).
4. [ ] Guardrail enforcement (`surface_guardrail`) to block probable unrelated lineage inheritance unless explicit rebind intent.
5. [ ] Explicit rebind provenance (`surface_rebind`) and corresponding runtime path/tests.
6. [ ] Cross-surface non-interference regression matrix and transcript/graph provenance audits.

## Progress

- 2026-05-24: Opened post-`550` implementation design contract in `docs/notes/2026-05-24-multi-active-transcript-surfaces-design.md`.
- 2026-05-24: Defined proposed durable control records (`surface_bind`, `surface_select`, `surface_rebind`, `surface_guardrail`) and surface-local continuity/guardrail invariants.
- 2026-05-24: Captured CLI/runtime proposal (`toas surface *`, `toas step --surface`) and migration compatibility contract for single-surface degenerate mode.
- 2026-05-24: Landed first on-the-fly step surface override seam: `toas step [--stdin] [--control ...] --session <transcript_path>` and `toas step --async --session <transcript_path>` now propagate transcript override through dispatch, local step runtime, operator API, and async RPC payloads with parity tests.
- 2026-05-24: Extended host-mode session targeting contract: `toas host serve --session <transcript_path>` now sets host default surface via env, and async step payload validation now accepts request-level `session`/`session_path` override fields for host transport precedence (`request > host default > durable selection > config`).

## Acceptance Criteria

1. A committed design/implementation plan exists that keeps transcript-first semantics primary.
2. Multi-surface continuity and provenance contracts are specified with deterministic invariants.
3. Guardrails for accidental cross-continuity lineage inheritance are explicitly defined and testable.
4. Sequencing/dependency on `550` is reflected in implementation plan and task tracking.

## Exit Criteria For Closing 561

1. Durable surface-id mapping and selection are append-only history records (not daemon-only state).
2. Surface-id workflow is usable without raw path juggling (`surface select/list/bind` + `step --surface`).
3. Guardrails prevent accidental cross-continuity lineage inheritance by default.
4. Explicit rebind path is available and auditable in durable records.
5. Single-surface behavior remains backward compatible as degenerate `default` surface.

## Validation

```bash
uv run pytest
```

## Related

- `550` Root sentinel taxonomy unification (`n0`) (dependency)
- `549` LCP root-class relinearization hardening
- `463` Session identity orchestration and buffer mapping
- `488` Multi-operator orchestration exploration
