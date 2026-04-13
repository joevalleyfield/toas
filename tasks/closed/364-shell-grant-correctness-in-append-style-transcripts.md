## Goal

Fix shell-grant resolution correctness so `/shell allow|deny|reset` behaves predictably in append-style transcripts.

## Why Now

Effective grant computation could drop prior grants by inspecting only the last line of each user message, causing confusing regressions in append-style sessions.

## Scope

- process all shell-modifier command lines in user transcript content
- ensure sequential `/shell allow ...` commands within one user block accumulate correctly
- preserve explicit `reset` semantics
- include `shell_script` in user-context execution routing parity with `shell`
- add regression tests for append-style grant behavior and user-frontier `shell_script`

## Outcome

Implemented in current pass:
- `resolve_effective_shell_allowed` now scans all `/shell ...` lines across user content, not only trailing lines
- user-frontier plan routing now treats both `shell` and `shell_script` as user-context shell execution
- user-context `shell_script` calls are bridged to user shell execution via `sh -lc <script>`
- tests added for multi-line grant accumulation and user-context `shell_script` execution
