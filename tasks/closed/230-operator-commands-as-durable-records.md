## Goal

Introduce an explicit operator-command arc where non-`step` workflows are durable, replayable, and lineage-safe.

## Scope

- define command requests/results as non-message durable records
- add an explicit command-entry surface (`/commands` and/or equivalent CLI entrypoints)
- keep command records linked to message-space targets without entering message parentage
- project outcomes in result-style form so users can adopt them explicitly

## Planned Tasks

- `231`: operator command record model and linkage semantics
- `232`: command entry surface and execution path
- `233`: projection and adoption semantics for command outcomes
- `234`: first command set (`extract`, `outline`, `compact`) with mechanical-first posture

## Why

Operator pressure now includes non-frontier workflows (compaction, non-tail extraction, topic outlining). Those actions need durable provenance without blurring conversation lineage.

## Done When

- command operations are first-class durable operator facts
- replay/audit can explain command request -> outcome causally
- message-event lineage remains conversation-only
- at least one mechanical command is production-ready with test coverage
