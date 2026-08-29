Filed as: 260828-remove-seed-transcript-envelope
FKA:
AKA: seed prompt envelope; pragmatic default marker; prompt transcript boundary
Legacy index:

Parent: `260803-seed-prompt-operator-stance`
Related: `260828-acceptance-seed-envelope-regression`

keywords: prompts, projection, active, correctness, defaults, transcript

# Remove Seed Transcript Envelope

The `pragmatic-default_v2` seed is prompt content, not a transcript fragment.
Its rendered content must not begin with `## TOAS:USER`; transcript projection
owns that structural marker when the seed becomes a durable user message.

## Acceptance Criteria

- [x] The v2 seed prompt no longer renders a transcript marker.
- [x] Prompt ordering and golden projection remain correct.
- [x] Bootstrap stores the plain seed content without adding a second
  transcript envelope.

## Implementation Evidence

- Removed the automatic `## TOAS:USER` prefix from v2 template rendering and
  updated its golden projection.
- Acceptance transcript setup adds the marker at the transcript boundary, while
  the seed content remains marker-free.
- Focused prompt, runtime, and acceptance tests pass.

## Closure

Closed after confirming the v2 seed is plain prompt content and transcript
projection owns its structural envelope, with no runtime compensation layer.
