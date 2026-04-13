## Goal

Ensure `capability_help` outputs useful detail in transcript result blocks, not just summary metadata.

## Why Now

In transcript-driven loops, `capability_help` returned only `[OK] ... summary` text, which hid the actionable argument-shape and policy detail needed by weaker models.

## Scope

- update generic success result shaping to include `content` when present and non-duplicate
- preserve existing specialized renderers (`shell`, `read_file`, `search`)
- add regression test confirming `capability_help` content appears in rendered result text

## Outcome

Implemented in current pass:
- default success renderer now appends non-duplicate `content` under summary
- `capability_help` result blocks include full detail text by default
- test coverage added for `shape_result_content` with `capability_help`
