# Assistance Provenance Trailers

Status: DRAFT
Task Link: `260806-assistance-provenance-trailers`

## Purpose

Record a lightweight convention for identifying the conversational system that
assisted a commit. This is deliberately separate from Git's human author and
committer fields: those fields should continue to describe the person making
the repository change.

## Locator Families

Codex and TOAS should not be forced into a fake common identity layer.

### Codex

Codex assistance has a task UUID, so a commit can name it directly:

```text
Assisted-by: codex:<codex-uuid>
```

### TOAS

TOAS provenance is a set of local durable references rather than a UUID. A
commit assisted through TOAS can use:

```text
Assisted-by: toas
TOAS-Transcript: <workspace-relative transcript path>
TOAS-Events: <source-qualified event occurrence>, ...
```

`TOAS-Transcript` is a familiar recovery affordance. It is not canonical
durable state, but retained transcript files are useful operator context.

Each `TOAS-Events` item must identify both the event source and node id. Node
ids are journal-local, so `n41` alone is ambiguous after rollover. A future
syntax might use a workspace-relative journal/segment path plus the node id,
for example:

```text
TOAS-Events: .toas/events.jsonl:n41, .toas/segments/000004-events.jsonl:n41
```

The exact syntax remains open; it must retain source identity even if a hot
journal is later sealed into an ordinal segment.

## Non-Goals

- Replacing Git authorship with model identity.
- Assigning synthetic UUIDs to TOAS histories merely for trailer symmetry.
- Assuming a transcript path is durable or that a bare node id is global.
- Introducing automatic trailer injection before the locator syntax and
  operator workflow are proven useful.

## Open Questions

- Should the committing tool append trailers automatically, offer an opt-in,
  or only validate trailers supplied by the operator?
- How should a hot-journal event locator remain resolvable after that journal
  is sealed and renamed during rollover?
- Are workspace-relative transcript paths acceptable in commits that may leave
  the original workspace or be published externally?
- What is the smallest useful record when one change draws on multiple Codex
  tasks or TOAS transcript/event sources?
