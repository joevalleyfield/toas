## Goal

Require slash commands to execute only when a line begins with `/command` at column 1.

## Why Now

Result/help content and command examples can include indented slash lines. Current extraction trims leading whitespace and can execute those lines unintentionally.

## Scope

- update user-frontier operator-command extraction to require literal line-start `/`
- align CLI tail extraction helper to the same rule
- add regressions for indented slash lines and in-text slash mentions

## Constraints

- keep last-line-only slash extraction behavior unchanged
- preserve existing parsing/dispatch behavior for valid slash lines

## Done When

- indented last-line slash text does not execute
- mid-line slash text does not execute
- column-1 slash command still executes
- tests cover runtime extractor + CLI helper

## Completion

- tightened runtime `extract_operator_command` to require slash at column 1 (no leading whitespace trim)
- aligned CLI tail extractor `_extract_operator_command_tail` to the same column-1 rule
- added regressions in `tests/test_step_frontier.py` and `tests/test_cli.py` for indented and mid-line slash text
- full test suite passes with coverage gate (`uv run pytest`)
