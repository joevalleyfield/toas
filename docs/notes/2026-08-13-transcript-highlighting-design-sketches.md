# Transcript Highlighting Design Sketches

Status: DRAFT  
Task Link: `260813-transcript-highlighting-design`

## Purpose

Capture the first design conversation for Vim transcript highlighting before
choosing Vim-classic syntax mechanics or visual styling.

The working transcript is still an ordinary Markdown document. TOAS adds
meaning through headings and fenced sub-documents; highlighting should reveal
that meaning without making the transcript a separate markup language.

## Repository Facts

The parser recognizes these exact role markers:

```markdown
## TOAS:SYSTEM
## TOAS:USER
## TOAS:ASSISTANT
## TOAS:CONTROL
```

`## RESULT` is a projection/semantic heading, not a role marker. The Vim
plugin currently knows about these markers for transcript insertion and region
handling, but does not define a transcript syntax-highlighting layer. Existing
fixtures show repeated user/result blocks and fenced `yaml` and `inert` content.

## Turn-Boundary Invariant

Every position in a valid TOAS transcript belongs to a role turn. A valid,
unescaped role marker is a total semantic reset:

```text
previous turn state  ──┤  ## TOAS:<ROLE>  ├── current turn state
```

No TOAS semantic state remains alive across a role marker. In particular,
fence ownership, projection-delta state, and role-derived context are all
turn-local. A syntax implementation may therefore synchronize backward to the
nearest role marker and never search earlier turns for TOAS state.

This is stronger than ordinary Markdown synchronization: Markdown may need to
recover generic document state, but TOAS semantics are never continued across
a role boundary. An unescaped role marker is structural even when nearby
content is fenced; transcript content that would otherwise look like a role
marker must be escaped by the transcript renderer/parser contract.

## Semantic Subregions

Semantic subregions are deliberately flat. Each `RESULT` or projection-level
`ASSISTANT` subregion is a direct child of exactly one enclosing
`TOAS:USER` turn; they do not nest below one another or become children of
other subregions. A sequence such as `RESULT` → `ASSISTANT` → `RESULT` closes
and replaces the current subregion at each heading.

This is a semantic relationship, not yet a styling decision. The renderer may
eventually add a visual indicator for the active subregion, but the first
contract only needs explicit ownership and reset behavior.

## Shared Semantic Vocabulary

The sketches below assume that highlighting can reason about several separate
dimensions without deciding yet how Vim renders them:

| Dimension | Values observed or proposed | Meaning |
| --- | --- | --- |
| role | `system`, `user`, `assistant`, `control` | Who owns the message lane |
| turn boundary | `user-like`, `assistant` | Every role heading resets all TOAS state |
| projection delta | `result`, `assistant-within-user`, none | A semantic subregion inside a turn |
| document mode | Markdown, fenced language, inert | Which language parser owns the body |
| potency | ordinary, inert, executable-looking | Whether content may be interpreted by another TOAS path |

This table is a design vocabulary, not a proposed syntax-group contract.

## Sketch A: Role Bands

Treat the nearest role heading as establishing a broad band until the next role
heading. `SYSTEM`, `USER`, and `CONTROL` share a user-like band; `ASSISTANT`
gets a separate band. `RESULT` and nested `ASSISTANT` headings add local labels
inside the current band.

```text
TOAS:USER       ┌──────────── user-like band ────────────┐
user content    │                                         │
RESULT          │  result delta                          │
result body     │                                         │
TOAS:ASSISTANT  └──────────── assistant band ────────────┘
assistant body
```

Strength: simple mental model and predictable turn resets.  
Risk: broad regions may obscure the distinction between `SYSTEM`, `USER`, and
`CONTROL`, and nested fences need a second mechanism.

## Sketch B: Orthogonal Overlays

Keep Markdown highlighting as the base. Add independent semantic overlays for
role, turn boundary, projection delta, and embedded-language ownership. A
`CONTROL` body can therefore have the same presentation as a `USER` body while
remaining separately tagged internally.

```text
Markdown base
  + role=user
  + turn=user-like
  + delta=result
  + document-mode=yaml
```

Strength: preserves distinctions without forcing every combination into a
single style name; likely the best fit if common primitives become useful later.
Risk: Vim's classic syntax engine may make overlapping contained regions and
priority rules difficult to express cleanly.

## Sketch C: Document Islands With Turn Context

Treat each fenced sub-document as an island owned by its declared language,
while carrying the surrounding role/turn context as metadata. Outside fences,
Markdown owns the body. Inside a fence, YAML or another language owns syntax,
but the transcript role remains available as an orthogonal fact.

```text
TOAS:USER [role=user, turn=user-like]
  Markdown body
  ```yaml [role=user, turn=user-like]
  operation: shell
  ```
  ## RESULT [delta=result]
  result body
```

Strength: respects the document's existing Markdown/language boundaries and
avoids teaching each embedded language about TOAS roles.
Risk: the same semantic distinction may be less visible inside an embedded
language unless the rendering layer has a non-textual or low-conflict channel.

## Sketch D: Heading-Centric Semantics

Make headings the primary highlighted affordance and leave bodies mostly to
ordinary Markdown and embedded-language syntax. Role headings carry distinct
internal identities; `RESULT` and nested `ASSISTANT` are marked as semantic
events but do not necessarily recolor their entire bodies.

Strength: minimal interference with Markdown and low risk of overwhelming long
transcripts.  
Risk: it may not provide enough orientation when scrolling through large turns.

## Current Leaning

Sketch B plus Sketch C appears to preserve the most information: orthogonal
semantic facts, with fenced islands retaining normal language ownership. This
is only a design hypothesis. It should not become an implementation decision
until a representative fixture exposes whether the distinctions are useful and
whether Vim-classic syntax can express them without fragile state coupling.

## Deliberately Deferred

- Colors, bolding, underlines, signs, concealment, and cursor-line behavior.
- Exact Vim syntax groups and `:syntax` state transitions.
- Whether internal tags are syntax groups, extmarks, buffer variables, or a
  shared intermediate representation.
- The complete fence-language registry.
- Execution or command interpretation; highlighting must not grant authority.

## Next Design Artifact

Build one annotated representative transcript fixture and mark the expected
boundaries and orthogonal facts without choosing colors. Use it to compare the
sketches on nested fences, repeated `RESULT` sections, `CONTROL`, and assistant
content appearing inside a user-like region. The fixture should also place
multiple role turns in one viewport: every visible turn slice must be
highlightable independently, rather than treating only the cursor's turn as
active.

## Annotated Fixture

The following is one hypothetical viewport. The `state` annotations are design
expectations, not transcript content. `sub=none` means that no semantic
subregion is active; `mode=markdown` means that ordinary Markdown owns the
body.

    ## TOAS:SYSTEM
    system setup
    state: role=system turn=user-like sub=none mode=markdown

    ## TOAS:USER
    inspect the configuration
    state: role=user turn=user-like sub=none mode=markdown

    ## RESULT
    operation: read_file
    state: role=user turn=user-like sub=result mode=markdown

    ```yaml
    path: toas.toml
    ```
    state: role=user turn=user-like sub=result mode=yaml

    ## ASSISTANT
    I found the relevant setting.
    state: role=user turn=user-like sub=assistant-within-user mode=markdown

    ## RESULT
    runtime.streaming_mode = enabled
    state: role=user turn=user-like sub=result mode=markdown

    ## TOAS:ASSISTANT
    The setting is enabled.
    state: role=assistant turn=assistant sub=none mode=markdown

    ```toml
    runtime.streaming_mode = "enabled"
    ```
    state: role=assistant turn=assistant sub=none mode=toml

    ## TOAS:CONTROL
    /history 5
    state: role=control turn=user-like sub=none mode=markdown

    ```inert
    operation: shell
    ```
    state: role=control turn=user-like sub=none mode=inert

The key transitions are:

| Boundary | New state | State discarded |
| --- | --- | --- |
| `TOAS:SYSTEM` | system, user-like, no subregion | everything before it |
| `TOAS:USER` | user, user-like, no subregion | system turn state |
| `RESULT` | user, result subregion | prior user subregion |
| `ASSISTANT` | user, assistant subregion | result subregion |
| `RESULT` | user, result subregion | assistant subregion |
| `TOAS:ASSISTANT` | assistant, no subregion | entire user turn state |
| `TOAS:CONTROL` | control, user-like, no subregion | entire assistant turn state |

This fixture deliberately places all four role turns in one possible viewport.
A syntax implementation must be able to resolve each visible slice separately;
the cursor's current turn is not the sole source of highlighting state.

## Recognition And Delegation

Fence handling should have an explicit recognition-to-delegation boundary. The
recognizer identifies the fence language and semantic tags; the sensible
default is to delegate recognized languages to Vim's included syntax rules.
Unknown languages should retain ordinary Markdown fence handling until a
language-specific delegate is registered.

## Open Questions

- Is a nested `## ASSISTANT` heading always a semantic delta inside a user turn,
  or can its meaning depend on the current projection context?
- Should `RESULT` own the following body until the next role/semantic heading,
  or only label the heading itself?
- What is the smallest useful representation of role identity that can survive
  a future non-Vim renderer?
- Which fence info strings are guaranteed by current TOAS contracts versus
  merely observed in fixtures?
