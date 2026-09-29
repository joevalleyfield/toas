Filed as: 260929-state-transcript-parsing-alignment
FKA:
AKA: native state turn parsing; transcript state alignment
Legacy index:

keywords: transcript, parser, runtime, state, alignment

Parent: `260926-state-step-requirements`
Depends on: `260927-state-step-alpha-loop`
Related: `260928-state-user-control-turn-lifecycle`; `260929-transcript-turn-decorations`

# Native State Turn Parsing In Transcript Engine

Bring `STATE` and `STATE-DIFF` turn parsing natively into `toas.transcript` so
that state turns are first-class transcript blocks instead of requiring
exceptional out-of-band string splitting and custom regex passes.

## Current Reality

`src/toas/transcript.py` strictly restricts role markers to
`SYSTEM | USER | ASSISTANT | CONTROL`. Encountering `## TOAS:STATE/1` or
`## TOAS:STATE-DIFF/1` raises a `ValueError` for an invalid marker.

Because of this, `cli_session_commands.py` intercepts any transcript containing
state markers and diverts to `parse_state_turn()` in
`src/toas/runtime/state_step.py`. `parse_state_turn()` does a backward search
for the last state marker and manually slices the transcript into prefix and
suffix. Surrounding user and control turns then have to be passed through
ad-hoc filtering (`_state_free_transcript()`) before they can be parsed by
`parse_transcript()`.

This exceptional handling breaks normal transcript reconciliation, prevents
unified LCP computation across transcripts containing state, and treats state
turns as an isolated parallel universe.

## Desired Reality

1. `toas.transcript.parse_transcript()` recognizes `STATE` and `STATE-DIFF`
   turns (including format/version decorations such as `/1`, `/2`) as valid
   transcript turns.
2. In the parsed turn list, the canonical semantic role is recorded (e.g. `role:
   "state"` or `role: "state-diff"`), with raw header marker preserved for
   lossless round-tripping.
3. `_eq` and `_lcp` compare semantic role and content, ensuring LCP matching
   works naturally across state turns.
4. `render_transcript()` and role escaping round-trip state turns cleanly.
5. `parse_state_turn()` can operate on standard parsed transcript turns rather
   than requiring custom string-slicing hacks.

## Acceptance Criteria

- `parse_transcript` parses transcripts containing `## TOAS:STATE/1`,
  `## TOAS:STATE-DIFF/1`, and arbitrary versions/decorations without error.
- State turns yield consistent `role` values and preserve content faithfully.
- `render_transcript` round-trips state turns with exact header markers.
- `_lcp` computes prefix matching across state turns based on role and content.
- `parse_state_turn` delegates to native transcript parsing rather than manual
  whole-buffer string slicing.
- Full test suite passes without regressions.

## Implementation Progress (2026-09-29)

- Updated `src/toas/transcript.py`:
  - `_TRANSCRIPT_ROLE_MARKER_RE` recognizes `STATE` and `STATE-DIFF` turn markers with optional version/progression or presentation decorations.
  - `_ROLE_MARKER_LINE_RE` and `_ESCAPED_ROLE_MARKER_RE` escape and unescape state markers losslessly without consuming newlines.
  - `render_transcript_marker` canonicalizes `"state"` to `## TOAS:STATE/1` and `"state-diff"` to `## TOAS:STATE-DIFF/1`, and supports versioned roles (`STATE/n`).
  - `render_transcript` uses explicit `marker` when present to preserve exact authored decorations, falling back to canonical markers.
  - `parse_transcript` emits canonical `role: "state"` / `role: "state-diff"`, storing `marker` only when non-canonical decorations are present.
- Updated `src/toas/runtime/state_step.py`:
  - Added `partition_state_transcript` to partition document turn sequences into prefix turns, the target state turn, and trailing suffix turns.
  - Refactored `parse_state_turn` to be strictly a turn-level schema decoder for state YAML/Markdown payloads (accepting a turn dict or state turn content), eliminating document-level metadata fields (`_transcript_prefix`, `_transcript_suffix`, `_input_turns`).
- Updated `src/toas/cli_session_commands.py`:
  - Removed `_state_free_transcript`.
  - Refactored `run_step` and `_run_state_step` to handle document-level turn partitioning and pass turn lists to `_resolve_state_input_turns`.
- Tests and verification:
  - 100% targeted test coverage on `toas.transcript`.
  - All 42 state-step tests in `test_state_step.py` and `test_cli_session_commands_state_step.py` updated to adhere to the clean flow and passing.
  - Full repo test suite (3,362 tests) passes cleanly.


