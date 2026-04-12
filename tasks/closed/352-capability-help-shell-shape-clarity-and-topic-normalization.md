## Goal

Make `capability_help` reliably useful during active runs by clarifying shell callable shape and reducing brittle topic lookup failures.

## Why Now

Recent transcript flow showed two operator failures:
- assistant proposed `operation: shell` with `command:` instead of required `arguments.argv`
- `capability_help` lookup failed hard on a close typo (`capaility_help`) instead of guiding recovery

## Scope

- explicitly document shell callable shape inside `capability_help` output
- clarify that `command`/`cmd` are not the action-lane shape for `operation: shell`
- add topic normalization for common aliases and close typos
- add tests covering both shell-shape guidance and typo-normalized topic lookup

## Outcome

Implemented in current pass:
- shell tool detail now states canonical action-lane shape: `arguments.argv` list[str]
- shell detail now explicitly warns against `command`/`cmd` for `operation: shell`
- `capability_help` topic resolution now normalizes aliases and close typo matches
- tests added for shell guidance text and typo normalization behavior
