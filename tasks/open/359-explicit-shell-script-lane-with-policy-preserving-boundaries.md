## Goal

Restore expressive shell/script capability for agent workflows without weakening strict bounded `shell.argv` semantics.

## Why Now

Models currently attempt heredoc/redirection content inside `shell.arguments.argv`, which fails shape validation and slows execution loops.

## Scope

- add an explicit rich shell lane (working name: `shell_script` or equivalent)
- define argument schema for multiline/script payloads
- align authorization behavior with existing direct-user shell intent boundaries
- ensure projection/result rendering remains clear and auditable
- update prompt assets with lane-selection guidance

## Intended Behavior

- strict lane remains `shell` + `arguments.argv` for deterministic bounded calls
- rich lane supports multiline shell grammar intentionally and visibly
- models choose lane based on operation shape instead of forcing shell grammar into argv lists

## Done When

- rich lane is implemented and test-covered
- lane-selection examples exist in protocol/procedure assets
- agent can successfully emit heredoc/script operations without invalid-argv failures
