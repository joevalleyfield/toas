Filed as: 260813-transcript-highlighting-design
FKA:
AKA: Vim transcript highlighting; Markdown transcript syntax; role-aware transcript rendering; transcript semantic highlighting
Legacy index:

keywords: surface, explore, inception, usability, markdown, vim, transcript, syntax

Related: `260803-language-exec-fenced-block-lane`; `260614-architecture-follow-through-coordination`

# Transcript Highlighting Design Exploration

Explore a role-aware syntax-highlighting model for TOAS transcripts in Vim.
The transcript remains an ordinary Markdown document, but its role headings,
semantic result headings, and fenced sub-documents provide enough structure for
a richer operator view.

This is a design task, not an implementation commitment. The first output is a
small set of competing design sketches and a vocabulary for discussing them.
Vim-classic syntax state mechanics and initial colors/styles follow later.

## Confirmed Repository Contract

- `src/toas/transcript.py` recognizes exactly `SYSTEM`, `USER`, `ASSISTANT`, and
  `CONTROL` role markers in the form `## TOAS:<ROLE>`.
- `## RESULT` is used by projection/rendering code but is not a transcript
  role marker.
- Existing transcript fixtures contain repeated `TOAS:USER` / `RESULT` blocks.
- Existing projected content includes ordinary Markdown fences, notably `yaml`
  and `inert`.
- The Vim plugin currently parses and inserts transcript regions but has no
  dedicated transcript syntax-highlighting layer.

## Design Intent

- `USER` and `ASSISTANT` are turn-breaking boundaries.
- `SYSTEM` and `CONTROL` are user-like for presentation, while retaining
  distinct role identity for any internal tagging or future behavior.
- `RESULT` and a nested `ASSISTANT` heading may supply semantic deltas inside a
  user-like turn without automatically becoming new transcript roles.
- No initial visual style or color assignment is prescribed.
- Fenced sub-documents should remain eligible for their normal Markdown/Vim
  language highlighting.

## Exploration Questions

- What is the smallest useful semantic vocabulary beyond Markdown's own syntax?
- Which regions need explicit start/end ownership, and which can be derived
  from the nearest heading?
- How should nested fenced languages interact with turn and semantic context?
- Should role identity be represented as syntax groups, concealed markers,
  buffer-local metadata, or only as an internal conceptual layer?
- Which distinctions should be orthogonal (role, turn, result/projection,
  embedded language, execution potency) rather than collapsed into one style?
- What must remain stable if the transcript is edited, branched, or rendered by
  a future non-Vim surface?

## Exit From Inception

Promote a bounded implementation follow-on after one design sketch is chosen
for a representative transcript fixture and its expected region boundaries,
role identity, fence behavior, and minimum test evidence are explicit.
