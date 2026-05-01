# 468 Env modifier multiline stickiness fix

## Summary

`/env set|unset` modifiers were only recognized when the slash command appeared as the final parsed line of a user message block. This made env state appear non-sticky across turns when users included additional text after `/env ...`.

## Change

- Update env-modifier resolution to scan all user-message lines for `/env set` and `/env unset` commands.
- Preserve existing behavior for terminal-line usage while removing order fragility within a user block.
- Add regression tests for multiline and non-terminal `/env` command placement.

## Outcome

- Transcript-scoped env modifiers are sticky across following turns regardless of whether `/env ...` is the final line in the originating user block.
