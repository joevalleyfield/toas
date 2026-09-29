Filed as: 260929-transcript-turn-decorations
FKA:
AKA: turn header metadata; transcript decorations; non-semantic turn headers
Legacy index:

keywords: transcript, parser, metadata, decorations, ergonomics

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
