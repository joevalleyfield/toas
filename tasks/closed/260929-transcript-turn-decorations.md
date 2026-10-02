Filed as: 260929-transcript-turn-decorations
FKA:
AKA: turn header metadata; transcript decorations; non-semantic turn headers
Legacy index:

keywords: transcript, parser, metadata, decorations, ergonomics, historical

Parent: `260926-state-step-requirements`
Related: `260929-state-transcript-parsing-alignment`

# General Transcript Turn Header Decorations And Metadata

Allow transcript role marker lines (`## TOAS:ROLE ...`) to carry trailing
decorations, identifiers, progression counters, timestamps, or non-semantic
metadata without affecting LCP equality or leaking into model-facing prompts.

## Context

In early transcripts, turn headers were strictly `## TOAS:(SYSTEM|USER|ASSISTANT|CONTROL)`.
With the introduction of typed state turns (`## TOAS:STATE/1`), version and
progression numbers were appended to the header line.

Beyond state turns, operators and tooling frequently benefit from navigational
and diagnostic decorations on turn headers—such as turn sequence numbers
(`## TOAS:STATE/3`), timestamps, or node IDs (`## TOAS:ASSISTANT [m_abc123]`)—to
enable easier buffer navigation and inspection.

## Principles

1. **Semantic Role vs. Presentation Marker**: The semantic role in graph/event
   space must remain clean (e.g. `role: "assistant"`, `role: "state"`).
2. **LCP Invariance**: Trailing decorations must not distort longest common
   prefix (LCP) matching between transcripts or between a transcript and durable
   history.
3. **Model Projection Filtering**: Model-facing prompt preparation must project
   only the required content and semantic role, omitting internal presentation
   decorations.
4. **Round-Trip Preservation**: Working transcript serializers should preserve
   the operator's authored decorations when reconstructing the buffer.

## Implementation & Evidence (2026-10-02)

- Landed in commit `d89614f2554f` (`feat(transcript): support native state turns and header decorations`).
- `_TRANSCRIPT_ROLE_MARKER_RE` in `src/toas/transcript.py` matches arbitrary trailing presentation decorations/versions: `r"^## TOAS:(SYSTEM|USER|ASSISTANT|CONTROL|STATE|STATE-DIFF)(?:/([^ \t]+))?(?:[ \t]+(.*))?$"`.
- `parse_transcript` assigns clean semantic roles while capturing raw headers in `message["marker"]`.
- `render_transcript` round-trips authored marker strings.
- `_eq` and `_lcp` match purely on semantic role and content, ensuring decorations do not distort prefix matches.
- Verified by `tests/test_transcript.py::test_parse_transcript_preserves_non_canonical_marker_decorations` and `tests/test_transcript.py::test_lcp_and_eq_with_state_turns`.

Status: Complete.
