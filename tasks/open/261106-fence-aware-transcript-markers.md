Filed as: 261106-fence-aware-transcript-markers
FKA:
AKA: fenced transcript markers; code fence transcript parsing; contained marker safety
Legacy index:

keywords: transcript, parsing, markers, code fences, markdown, escaping, containment

Related: `261106-bounded-step-quiescence`; `260825-visible-transcript-turn-ids`

# Fence-Aware Transcript Marker Parsing

## Intent

Ensure transcript parsing distinguishes between bare, top-level role markers and contained content (inside Markdown code fences, blockquotes, or escapes), preventing inert tool results and specimens from tripping invalid marker errors or phantom turn splitting while preserving the operator typo guard for bare frontier lines.

## Context & Motivation

During multi-step dogfooding in `.toas/session-20261106-1823-visible-transcript-turn-ids.md`, Turn 1 executed `read_file` on `docs/notes/2026-10-04-transcript-reference-contract.md`. The note discussed heading grammar and contained the Markdown specimen:

````markdown
```markdown
## TOAS:<ROLE> [[handle]]
```
````

When Turn 2 started, `parse_transcript` scanned the transcript line-by-line without tracking code fences. It encountered `## TOAS:<ROLE> [[handle]]` at column 0 inside the 5-backtick inert result block. Because `<ROLE>` is not a valid role, `parse_transcript` raised:

```text
ValueError: invalid transcript marker at line 847: '## TOAS:<ROLE> [[handle]]'
```

This caused Turn 2 to abort immediately with `[run failed]`.

### The Boundary: Contained vs. Bare

1. **Bare, uncontained lines at column 0**:
   When an operator is editing at the frontier and accidentally types `## TOAS:USRE` or `## TOAS:BOT`, the hard fail protects them from silent turn desynchronization (where the input would otherwise be quietly absorbed into the preceding turn). This safety net must remain intact.
2. **Contained content**:
   Inside Markdown code fences (`` ` `` or `~` of length $\ge 3$), blockquotes (`>`), or escapes (`\## TOAS:`), lines are literal inert data. They must neither be parsed as active role delimiters nor trip marker syntax errors.

## Scope

- **`src/toas/transcript.py`**:
  - Update `parse_transcript(text)` to track CommonMark code fence state:
    - Open on `^[ \t]*(`{3,}|~{3,})` with character and length $N \ge 3$.
    - Close only on a matching line with at least $N$ identical fence characters.
    - While in a fence, lines are treated as raw content belonging to `current_lines`: they do not trigger role transitions and do not raise invalid marker errors.
  - Outside of fences, bare column-0 lines starting with `## TOAS:`:
    - If matching `_TRANSCRIPT_ROLE_MARKER_RE`, flush and transition role.
    - If not matching, raise `ValueError: invalid transcript marker at line <N>: ...` (preserving the typo guard).
- **Tests**:
  - Unit tests in `tests/test_transcript.py`:
    - Specimen with `## TOAS:<ROLE>` inside a code fence parses as content without error.
    - Specimen with `## TOAS:USER` inside a code fence remains part of the enclosing turn's content rather than splitting into a new turn.
    - Nested code fences (e.g. 5-backtick block enclosing 3-backtick block) preserve inner marker-like content.
    - Bare `## TOAS:BOT` outside fences still raises `ValueError: invalid transcript marker`.
  - Regression test with the full snippet from `session-20261106-1823-visible-transcript-turn-ids.md`.

## Acceptance Criteria

1. [ ] Lines starting with `## TOAS:...` inside Markdown code fences (both valid role names and unrecognized marker syntax) parse cleanly as inert turn content.
2. [ ] Nested code fences (e.g. 5 backticks enclosing 3 backticks) are respected according to CommonMark fence matching rules.
3. [ ] Bare, un-fenced lines starting with `## TOAS:` that fail `_TRANSCRIPT_ROLE_MARKER_RE` continue to raise `ValueError: invalid transcript marker at line <N>: ...`.
4. [ ] `./scripts/check.sh` passes with 100.00% statement coverage.
