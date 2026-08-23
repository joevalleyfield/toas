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

Claimed for implementation on 2026-08-16: unstyled Vim syntax probe and
headless syntax-identity coverage against the annotated multi-turn fixture.

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
- Every position in a valid transcript belongs to a role turn. Any valid,
  unescaped role marker is a total semantic reset: no TOAS fence ownership,
  projection-delta state, or role-derived context survives across it.
- `RESULT` and a nested `ASSISTANT` heading may supply semantic deltas inside a
  user-like turn without automatically becoming new transcript roles.
- Semantic subregions are flat children of exactly one enclosing `TOAS:USER`
  turn. `RESULT` → `ASSISTANT` → `RESULT` resets the current subregion at each
  heading; subregions do not nest.
- A viewport may contain multiple turns. Highlighting must cover every visible
  turn slice, not only the turn containing the cursor.
- Fence recognition and language delegation are separate concerns; recognized
  languages should delegate to included Vim syntax rules by default.
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
role identity, fence behavior, and minimum test evidence are explicit. The
design note now contains the first annotated multi-turn fixture; the next
decision is the recognition/delegation contract and whether that fixture should
become a parser-level or Vim-level regression artifact.

## Implementation Evidence: 2026-08-16

- Added `vim/syntax/toas_transcript.vim` as an unstyled semantic probe.
- Role and semantic headings receive distinct syntax identities without any
  highlight links or visual styling.
- `yaml` and `toml` fences delegate to Vim's bundled syntax files through
  `syntax include`; unknown fences receive no TOAS delegate.
- Added `tests/vim/transcript_syntax_probe.vader` with three focused cases and
  13 passing syntax-identity assertions across multiple visible turns.
- The probe intentionally stops before body-wide subregion ownership and
  automatic filetype/plugin wiring. Those need a follow-on after the syntax
  cache behavior is reviewed.

## Visual Styling Evidence: 2026-08-16

- Added a first restrained visual layer using standard theme-owned Vim groups.
- User-like role markers share `Title`; assistant role markers use `Statement`.
- `RESULT`, nested assistant, and fence delimiters use `PreProc`, `Special`,
  and `Delimiter` respectively.
- Visual links are covered by the focused Vader probe; no hard-coded colors
  were introduced.

## Syntax Cache Evidence: 2026-08-16

- A fenced delegated syntax can otherwise leave a later role heading in the
  stale fence state until `:syntax sync fromstart`.
- Each recognized TOAS fence now treats an exact role heading as a zero-width
  end condition, while the separate role sync anchor lets Vim recover from a
  nearby viewport without scanning back across earlier turns.
- The regression covers a YAML fence that has no closing fence before
  `## TOAS:USER`; the heading is no longer `mkdCode` and resolves to
  `toasRoleUser`.
- Focused probe result: 5/5 cases, 22/22 assertions.

Claimed for implementation on 2026-08-23: add a TOAS Markdown overlay for
escaped less-than text so `\\<` remains ordinary prose to Vim's inherited HTML
syntax.

## Escaped Less-Than Evidence: 2026-08-23

- Added `toasEscapedLessThan` for the Markdown-native `\\<` spelling.
- The focused probe covers escaped tag-like text, protocol-marker text, and
  escaped autolink-shaped text; it inspects both the escape position and the
  following characters for inherited HTML/autolink state.
- Verified with both the local vim-markdown runtime and Vim's bundled Markdown
  syntax: 6/6 cases, 28/28 assertions.
