## Goal

Make anchors practical maintenance records rather than manually written curiosities.

## Scope

- Emit anchors at useful transcript boundaries during normal operator actions
- Avoid redundant anchors when an equivalent anchor already exists
- Keep anchor generation tied to actual projection/rebuild work

## Behavior

- Normal operator commands can leave behind useful anchors
- Anchor maintenance stays lightweight and deterministic
- Later alignment can benefit from anchors created by real usage

## Rules

- Anchors remain non-causal helpers
- Anchor emission should follow observable operator actions, not speculative background work
- Redundant anchor spam should be avoided

## Non-Goals

- No full indexing subsystem yet
- No performance engineering beyond practical shortcuts

## Done When

- At least one regular operator command emits useful anchors automatically
- Duplicate-equivalent anchors are avoided
- Tests cover both emission and suppression behavior
