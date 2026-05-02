## Goal

Add an explicit transcript control lane for operator commands that stays visible/durable for TOAS mechanics while remaining excluded from LLM message projection.

## Why

Operator workflow needs a near-user authoring surface for `/help`, `/config`, `/intent`, and `/queue` without polluting model context. Existing lanes can do this implicitly, but the semantics are not explicit or ergonomic.

## Scope

- define transcript marker semantics for `TOAS:CONTROL`
- execute control-lane operator commands with the same command semantics as current frontier operator commands
- exclude control-lane content from LLM input message assembly
- preserve ordering parity with adjacent transcript lanes for deterministic rebuild/append behavior
- preserve inert affordances inside control lane for help/example content

## Non-Goals

- no config sequencing redesign
- no external tracker sync or task-file mapping logic
- no replay/queue arbitration policy redesign
- no broad slash command syntax changes

## Done When

- `TOAS:CONTROL` sections are recognized and parsed deterministically
- frontier control commands execute and project results like existing operator commands
- control-lane text is never projected as user/assistant LLM input content
- historical control content imports as already-resolved durable history facts (no re-execution)
- inert regions continue to dud command extraction inside control lane
- tests cover parser behavior, ordering/rebuild invariants, and projection exclusion

## Initial Slices

1. parser + transcript semantics for `TOAS:CONTROL`
2. frontier execution and historical import behavior alignment
3. LLM projection exclusion and no-regression message assembly checks
4. inert-in-control compatibility coverage
5. docs/help updates describing control-lane intent and limits

## Loop Findings (2026-05-02)
- Loop 1 probe attempted canonical append-mode run with leading `## TOAS:CONTROL` section.
- Immediate parser failure:
  - `ValueError: invalid transcript marker at line 1: '## TOAS:CONTROL'`
- Artifact context captured in `docs/acceptance/spikes/471-465-loop1-scorecard.md`.
- Confirms slice ordering: parser/marker support must land before execution/projection experiments are meaningful.

## Progress
- Slice 1 complete: transcript parser/marker support now accepts `## TOAS:CONTROL` as a first-class lane marker.
- Slice 2 complete: control-lane frontier entries now execute operator slash-command semantics (for example `/help tools`) without invoking assistant generation.
- Slice 3 complete: `TOAS:CONTROL` lane content is excluded from LLM message projection while preserving adjacent user-turn concatenation semantics.
