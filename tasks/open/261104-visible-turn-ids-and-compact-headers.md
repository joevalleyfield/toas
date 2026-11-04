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
