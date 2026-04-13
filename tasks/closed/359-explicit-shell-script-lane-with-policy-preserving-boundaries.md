## Goal

Restore expressive shell/script capability for agent workflows without weakening strict bounded `shell.argv` semantics.

## Why Now

Models were attempting heredoc/redirection content inside `shell.arguments.argv`, failing shape validation and slowing execution loops.

## Scope

- add explicit rich shell lane (`shell_script`)
- define argument schema for multiline/script payloads
- align authorization behavior with existing bounded assistant policy
- ensure projection/result rendering remains clear and auditable
- update capability prompts with lane-selection guidance

## Outcome

Implemented in current pass:
- added model-addressable `shell_script` tool with required `arguments.script`
- `shell_script` runs via `sh -lc` but remains workspace-bounded, timeout-bounded, and allowlist-gated on leading command
- result projection uses shell-style rendering (`stdout`/`stderr`) for `shell_script`
- capability help/prompts now advertise both `shell` (`argv`) and `shell_script` (`script`) lanes
- tests added for successful `shell_script` execution and disallowed-command rejection
