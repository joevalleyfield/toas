# 450: Draft@Origin Import Checklist (9401df55 + 8fc11687)

## Purpose
Capture every reviewed change from the `draft@origin`-only commits as explicit checklist items so import work can be staged without losing details.

## Source Commits
- `9401df55`: `feature(procedure): add parameterization, defaults, and result visibility`
- `8fc11687`: `hot-fix windows-compatibility`

## Relationship
- Execution task: `449` (implementation slices)
- This task: exhaustive intake checklist and import ledger

## Checklist

### A) Procedure runtime and callable surface (`9401df55`)
- [ ] `load_procedure(...)` accepts optional `params` map
- [ ] procedure YAML may declare `defaults` map
- [ ] merge precedence is `defaults` then caller-supplied `arguments`
- [ ] support placeholder interpolation for both `{{ key }}` and `{{key}}`
- [ ] fail fast on unresolved placeholders with explicit missing key names
- [ ] preserve/verify invalid/missing asset error behavior after interpolation pass
- [ ] `procedure` tool validates `arguments` is a dictionary when provided
- [ ] `procedure` tool forwards `arguments` into `load_procedure(...)`
- [ ] dry-run output includes readable step preview (not just count)
- [ ] execution output includes per-step rendered content for triage visibility

### B) Procedure assets (`9401df55`)
- [ ] add `src/toas/procedures/search_scope_v1.yaml`
- [ ] `search_scope_v1` includes required `query` placeholder
- [ ] `search_scope_v1` includes `path` default (`"."`)
- [ ] `repo_discovery_triage_v1` op shape is corrected (no invalid op token)
- [ ] discovery procedure still aligns with current intended task-scout behavior

### C) Windows shell compatibility (`8fc11687`)
- [ ] add Windows env alias normalization helper for shell subprocess calls
- [ ] normalize common case-sensitive aliases used by MSYS/bash contexts (`OneDrive`, `UserProfile`, `ProgramFiles`, `AppData`)
- [ ] ensure `run_subprocess(...)` always uses normalized effective env on Windows
- [ ] verify Windows shell launcher argv is valid for `bash` path (no malformed option token)
- [ ] verify Windows user-shell path that converts argv -> command-line -> launcher remains correct
- [ ] verify assistant-shell and user-shell paths remain behaviorally aligned after changes

### D) Validation and stitching
- [ ] add targeted tests for procedure defaults + interpolation + missing-required-parameter errors
- [ ] add targeted tests for procedure `arguments` validation and rendering visibility
- [ ] add Windows-focused tests (or platform-gated mocks) for env normalization + launcher argv correctness
- [ ] run full suite (`uv run pytest`)
- [ ] update `449` progress notes as slices land
- [ ] close this checklist task when all items are either landed or explicitly deferred with rationale

