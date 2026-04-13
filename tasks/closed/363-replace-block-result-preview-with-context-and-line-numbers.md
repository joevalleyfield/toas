## Goal

Improve `replace_block` result projection to show immediate edit-shape feedback (especially indentation outcomes) without dumping full file content.

## Why Now

The generic success-content projection now exposed full edited content, which was useful for catching unintended indentation but too noisy. A bounded context preview is a better default.

## Scope

- add line-numbered preview data to `replace_block` tool results
- render `replace_block` success as summary + bounded preview (context around changed lines)
- keep full content in tool result payload for programmatic use
- add tests for preview rendering and preview metadata presence

## Outcome

Implemented in current pass:
- `replace_block` results now include `changed_line_start`, `changed_line_end`, and `preview`
- result rendering for `replace_block` shows concise line-numbered preview by default
- tests cover both rendered preview output and returned preview metadata
