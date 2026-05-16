# 516 Doc Truth Model and Task-Coupling Guardrails

## Objective
Make it mechanically obvious which docs describe current implemented behavior versus directional or draft architecture, and require task linkage for planned content.

## Why
During rearchitecture, doc/code sequencing can blur fact vs plan. We need explicit status markers and task coupling to reduce ambiguity and drift.

## Scope
- define a lightweight doc-truth model note
- apply status headers to core architecture/protocol/capability docs
- require open-task linkage for planned/draft sections
- require closure linkage (task/commit) when draft material becomes implemented

## Done When
- doc-truth model is documented under `docs/notes`
- `docs/capabilities.md` explicitly marked current/normative
- `docs/runtime-direction.md` explicitly marked directional/non-normative with driving task links
- `docs/protocol-notes.md` explicitly marked draft/proposal with linked tasks

## Related
- `515` protocol envelope v0 and event durability map
- `466` config sequencing contract clarity

