## Goal

Support choosing and resuming a specific message lineage in graph-native history.

## Scope

- Define how a working head is selected
- Support continuing from a non-tip accepted message event
- Make rewind a head-selection operation rather than log truncation
- Ensure `step` appends new descendants instead of rewriting history
- Define send-time projection rules for adjacent user-message concatenation

## Behavior

- Rewind selects an earlier accepted message event as the next parent
- Continuing after rewind creates a branch
- Existing descendants remain in history
- Transcript projection can target the selected lineage
- Adjacent user message events are concatenated when projecting input to the LLM
- Concatenation is a send-time projection rule, not a storage rule

## Non-Goals

- No full branch UI yet
- No merge semantics yet

## Done When

- The operator can continue from an earlier message event without deleting later history
- Rewind and branch continuation are expressible in graph terms
- History preserves multiple futures from the same parent
- The LLM input layer no longer emits back-to-back `user` turns when they are adjacent in history
