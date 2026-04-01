## Goal

Make the operator usable for longer-lived sessions, larger histories, and regular debugging.

## Scope

- Branch and head inspection UX
- Transcript rebuild ergonomics
- Anchor and index optimization
- Better history inspection and debugging tools

## Why

The core runtime is now coherent, but operator ergonomics still lean on reading raw JSONL and manually inferring state. This milestone should make everyday inspection and rebuild tasks available as explicit CLI surfaces before any heavier UI is considered.

## Planned Tasks

- `151`: history and branch inspection commands
- `152`: transcript rebuild and sync commands
- `153`: practical anchor maintenance

## Non-Goals

- No heavy UI layer unless the CLI/editor workflow proves insufficient
- No speculative scale machinery before there is real pressure

## Done When

- Users can inspect and navigate history without reading raw JSONL by hand
- Larger histories remain practical to work with
- Debugging projection, branching, and execution state is materially easier
