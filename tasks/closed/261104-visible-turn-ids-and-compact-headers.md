Filed as: 261104-visible-turn-ids-and-compact-headers
FKA:
AKA: visible turn ids; compact header stamps; keyless telemetry decorations; turn handle resolution
Legacy index:

keywords: transcript, turn-id, handle, telemetry, compact-stamp, projection, resolution, selector

Parent: `260825-visible-transcript-turn-ids`
Related: `261104-transcript-turn-telemetry-decorations`; `docs/notes/2026-10-04-transcript-reference-contract.md`; `docs/notes/2026-10-04-transcript-decorators.md`

# Visible Turn IDs And Compact Header Stamps

## Intent

Implement visible turn handles and compact, keyless telemetry stamps for
transcript headings, unifying turn identity with execution telemetry while
retaining double-bracket (`[[handle]]`) syntax for in-prose citations and
enabling stateless turn selection.

## Motivation

Visible turn handles allow operators to identify and reference specific turns
in `session.md` without tracking raw event hashes or relying on ambient editor
cursor state. Combining turn handles with execution telemetry into a clean,
keyless header stamp (`## TOAS:ASSISTANT [bravo claude-3-7-sonnet 11:42:00 1.2s]`)
eliminates visual noise while making each turn identifiable and citeable.

In-prose citations (`[[bravo]]`) reference those visible handles directly,
and stateless command selectors can address turns by visible handle as well
as canonical event hash.

## Proposed Presentation Surfaces

### 1. Keyless Compact Header Stamp
Single brackets hold turn identity and execution telemetry with keys elided
where token shapes are structurally distinct:
- Turn ID leads: `bravo`, `@bravo`, or `**bravo**`
- Status: `OK`, `ERROR`, `FAIL`
- Duration: `42ms`, `1.2s`, `3m10s`
- Timestamp: `11:42:00`
- Target: model or tool identifier (`claude-3-7-sonnet`, `read_file`)

```markdown
## TOAS:USER [alpha]
Please check the database configuration.

## TOAS:ASSISTANT [bravo claude-3-7-sonnet 11:42:00 1.2s]
I will inspect the local SQLite settings.

## RESULT [charlie OK 42ms read_file]
[OK] read_file: config.json
```

### 2. In-Prose Citations
Within user prompts, assistant prose, or state documentation, earlier turns
are referenced using standard double brackets:

```markdown
As noted in [[alpha]], we need persistent storage. Based on [[charlie]], please patch the path.
```

### 3. Stateless Turn Selector
Commands and APIs (such as `toas transcript <selector>` or handoff targeting)
can resolve a turn by either its visible handle (`bravo`) or its canonical
event hash (`evt_01j7b2`).

## Acceptance Criteria

- Implement deterministic turn handle allocation (e.g. NATO phonetic `alpha`,
  `bravo`, etc., or preserving user-authored handles) during transcript projection.
- Extend `turn_telemetry.py` to format and parse keyless compact stamps
  (`[bravo claude-3-7-sonnet 11:42:00 1.2s]`) alongside key-value and comment styles.
- Parse `turn_id` from turn markers and sub-heading comments into message dictionaries.
- Ensure LCP invariance and model-input sanitization preserve existing invariants.
- Implement stateless turn selector resolution supporting visible handles.
- Add Vim syntax highlighting for in-prose `[[handle]]` citations.
- Achieve 100.00% statement coverage across all modified and new files.

## Resolution

- Implemented deterministic NATO phonetic turn handle allocation (`allocate_turn_handle`) in `src/toas/runtime/turn_telemetry.py` (`alpha`, `bravo`, ..., `zulu`, `alpha-2`, etc.).
- Implemented `parse_turn_stamp` in `src/toas/runtime/turn_telemetry.py` supporting both keyless compact stamps (`[bravo claude-3-7-sonnet 11:42:00 1.2s]`, `[charlie OK 42ms read_file]`), bold/sigil handles (`**bravo**`, `@bravo`, `[[bravo]]`), and verbose key-value pairs (`[id=bravo target=...]`).
- Extended `format_turn_telemetry` with `"compact"` style (keyless stamp where token shapes are structurally distinct) and added `"compact"` choice to `session.telemetry_decorations` in `src/toas/config_parsing.py`.
- Updated `src/toas/transcript.py` (`parse_transcript`) to extract `turn_id` into message dictionaries while maintaining 100% LCP invariance in `_eq` / `_lcp` and prompt-packet sanitization in `project_llm_input_from_messages`.
- Updated `src/toas/runtime/step_generation_runtime.py` to auto-allocate turn handles and project compact or verbose stamps for assistant turns.
- Implemented stateless turn selector resolution (`resolve_turn_selector` and `_lineage` in `src/toas/graph.py`), enabling selector lookup by visible turn handle, metadata marker, or ID prefix in addition to canonical event hash.
- Added in-prose reference extraction (`extract_in_prose_references`) for `[[handle]]` and `[[handle|alias]]`.
- Updated Vim syntax definitions in `vim/syntax/toas_transcript.vim` linking `toasProseReference` to `Underlined`, verified with Vader test suite in `tests/vim/transcript_syntax_probe.vader`.
- Verified 100.00% statement coverage across all 161 files in `./scripts/check.sh`.

