# Explicit Syntax-Driven Reference Expansion and Terminal Report Projection

Filed as: 261009-explicit-reference-expansion-and-report-projection
FKA:
AKA: state reference expansion in report; syntax driven ref expansion; round trip by reference; eliminate manual transcription
Legacy index:

keywords: runtime, state, references, report, prompt, instructions

Parent: `260926-state-step-requirements`
Depends on: `261008-state-step-terminal-reporting-channel`; `261008-state-spill-ingestion-and-artifact-references`
Related: `261009-read-file-eof-truncation-and-soft-bounds`

Status: CLOSED

## Outcome

- Kept state schema fully user-defined and schema-agnostic by driving reference expansion strictly via explicit syntax:
  - Constrained `_STANDALONE_REF_PATTERN` to explicit reference syntax: `(ref: <target>)`, `ref: <target>`, and line-bounded slices `<target>:<start>-<end>`.
  - Disallowed bare `ib_...` and bare `.toas/scratch/...` strings from triggering automatic expansion as standalone tokens, preventing accidental inflation of metadata fields (e.g., `id: ib_...` or `path: .toas/scratch/...`).
  - Added support for structured dicts containing explicit `{"ref": "<target>"}`.
- Added terminal report reference expansion (`_expand_report_references`) so that explicit references inside the terminal `report` channel expand automatically into complete inert blocks upon projection.
- Updated `instructions_v1.txt` with clear operator instructions advising models against manual transcription and explaining that references round-trip in state and expand in final reports.
- Added comprehensive unit tests in `tests/test_state_step.py` and maintained 100.00% statement coverage across the repository.

## Context

In state-step session runs (`session-20261007-1946-state-seed.md`, Turns 6 & 8), the model engaged in painful manual transcriptions:
- In Turn 6, it transcribed 27 task filenames by hand into `notes.open_tasks_list_preview`.
- In Turn 8, it transcribed 44 task filenames by hand into the `report` field.

Furthermore, when the model stored structured metadata objects in `state.artifacts`:
```yaml
artifacts:
- id: ib_479396b18eb5ca83
  path: .toas/scratch/ib_479396b18eb5ca83.txt
  description: Full listing of files in tasks/open/
```
The packet preparation logic in `_expand_compound_observation` recursively matched bare `ib_...` and `.toas/scratch/...` strings anywhere in the dictionary, replacing both the `id` field and the `path` field with full, duplicate multi-line rendered inert blocks.

Hardcoding field names (like `state.artifacts`) into the runtime is risky because TOAS states are meant to be user-defined templates. Instead, reference expansion should be driven by explicit syntax (`(ref: ...)`, `{"ref": ...}`, or bounded slices `<target>:<start>-<end>`), remaining schema-agnostic while preventing accidental mutation of metadata fields.

Simultaneously, `report` projection should support expanding explicit references, and prompt instructions should explicitly inform models that results can be preserved and reported by reference without manual line-by-line transcription.

## Objectives

1. **Syntax-Driven Reference Expansion (Schema-Agnostic)**:
   - Scope standalone reference expansion strictly to explicit reference syntax:
     - `(ref: <target>)` or `ref: <target>`
     - `{"ref": "<target>"}`
     - Line-bounded slices `<target>:<start>-<end>`
   - Disallow bare `ib_...` and bare `scratch/...` without explicit `ref:` or line bounds from triggering standalone replacement, preventing accidental mutation of `id` or `path` metadata fields.
2. **Terminal Report Reference Expansion**:
   - Ensure the user-facing `report` channel expands explicit references when projected to the terminal and transcript, so models can provide synthesized answers or cite large results by reference.
3. **Model Instruction Updates**:
   - Update `instructions_v1.txt` to clearly state that models do not need to transcribe file listings, diffs, or raw outputs into `notes` or `report`. Storing references in `state` preserves them across turns, and references in `report` expand into complete user output upon completion.
4. **Validation and Coverage**:
   - Add unit tests for structured dicts in state and reference expansion in `report`.
   - Maintain 100.00% statement coverage.
