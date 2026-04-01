## Goal

Make transcript rebuild and sync operations explicit and easy to use.

## Scope

- Add a command to rebuild `session.md` from durable history
- Support rebuild from selected or explicit heads
- Keep rebuild semantics clear relative to the user-authored working transcript

## Behavior

- Users can reconstruct a usable transcript view into `session.md`
- Rebuild can target the selected head or an explicit head
- The rebuild path is explicit rather than hidden behind `step`

## Rules

- Rebuild writes a projected transcript view, not authoritative recovery of every past edit
- Rebuild must not mutate durable history
- Rebuild commands should say what they targeted

## Non-Goals

- No automatic overwrite policy beyond the explicit command
- No merge of current transcript edits with rebuilt content

## Done When

- There is a CLI path to rewrite `session.md` from history
- The command works with selected and explicit heads
- Tests prove rebuild behavior and output targeting
