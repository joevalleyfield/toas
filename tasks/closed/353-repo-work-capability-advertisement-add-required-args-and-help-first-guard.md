## Goal

Reduce action-lane argument-shape confusion by making repo-work capability advertisement include required argument cues and a clear help-first fallback.

## Why Now

Observed transcript behavior showed the assistant issuing `operation: shell` with `arguments.command`, which fails because callable shell requires `arguments.argv`.

## Scope

- add compact required-argument hints to repo-work capability lines
- explicitly call out `shell` shape as `arguments.argv` and disallow `command` in callable lane
- add guidance to use `capability_help` before first callable action when argument shape is uncertain
- add regression test coverage for the strengthened repo-work output

## Outcome

Implemented in current pass:
- repo-work capability advertisement now includes per-tool argument cues
- shell guidance now explicitly requires `arguments.argv` and warns against `command`
- repo-work advertisement now includes a `capability_help` first-call fallback
- prompt tests cover shell shape and help-first guidance presence
