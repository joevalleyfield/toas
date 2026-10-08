# State Spill Ingestion Guidance and Scratch Artifact References

Filed as: 261008-state-spill-ingestion-and-artifact-references
FKA:
AKA: state spill ingestion; ephemerality retention; scratch path artifact expansion; tail sipping amnesia
Legacy index:

keywords: runtime, usability, active, correctness, projection, frontier

Parent: `260926-state-step-requirements`
Depends on: `261008-state-step-terminal-reporting-channel`
Related: `261004-state-observation-reference-addressing`; `260926-state-step-requirements`

Status: CLOSED; enabled scratch file paths and bare block IDs as first-class expandable artifact references and enhanced spill trailers and instructions to eliminate tail-sipping ephemerality amnesia.

## Context

In dogfood (`session-20261007-1946-state-seed.md`), `shell` returned 47 lines, spilling to `.toas/scratch/ib_479396b18eb5ca83.txt`.
- The spill footer previously advised: `[17 lines remaining. Inspect with read_file, grep, or script via path=".toas/scratch/ib_479396b18eb5ca83.txt"]`.
- The model followed this hint literally by issuing `read_file` with `start_line: 30`, `end_line: 47`.
- Because observations are strictly single-turn ephemeral, once Turn 6 executed, the preview containing lines 1..30 vanished from context. In Turn 7, the model saw only lines 30..47 and concluded there were only 18 open tasks in the repository instead of 46.
- In Turn 6, the model attempted to preserve context by adding `.toas/scratch/ib_479396b18eb5ca83.txt` to `state.artifacts`, but the packet preparer only expanded `(ref: ib_...)` block references, ignoring raw scratch file paths.

## Objectives

1. **Scratch Path Artifact Resolution**:
   - Enable `state.artifacts` to accept and expand `.toas/scratch/<block_id>.txt` paths (or bounded slices `path:start-end`) just like `ib_<block_id>` references.
2. **Tune Spill Ingestion Guidance**:
   - Clarify the spill footer and protocol instructions so models understand that intentional reads permit up to 500 lines without spilling, and that sipping only the tail without persisting the head drops earlier items under single-turn ephemerality.
   - Advise models to read the full spilled output via `read_file` (without line bounds or up to 500 lines) when ingesting lists or files that fit within bounded limits.
3. **Validation and Testing**:
   - Test artifact expansion for scratch file paths.
   - Verify prompt instructions and spill notifications in end-to-end tests.
   - Maintain 100.00% statement coverage.

## Outcome

- Updated `_STANDALONE_REF_PATTERN` and `_resolve_reference_target` in `src/toas/runtime/state_step.py` to recognize bare scratch file paths (`.toas/scratch/<block_id>.txt`), bare block IDs (`ib_<block_id>`), and sliced scratch paths (`.toas/scratch/<block_id>.txt:start-end`), expanding them into full or sliced inert result blocks during state-step packet preparation.
- Ensured `build_multi_state_sequence_packet` computes `workspace_root` from `events_path` so scratch and workspace artifact references expand consistently across multi-turn sequences.
- Updated `spill_inert_block` in `src/toas/tools_cluster/rendering.py` to clarify that intentional reads permit up to 500 lines without spilling, and explicitly warned models that under single-turn ephemerality, sipping only the tail drops the previewed head unless persisted into state.
- Updated `instructions_v1.txt` to explicitly guide models on persisting spilled lists into `state.artifacts` or reading complete spilled files.
- Added comprehensive unit tests in `tests/test_state_step.py` verifying scratch path, slice, and block ID expansion in both single-step and multi-turn sequence packet generation.
- Verified `./scripts/check.sh` passes with 100.00% statement coverage across all 22,678 statements.
