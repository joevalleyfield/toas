## Goal

Make `/help config` a valid help topic so operators can discover config key/value guidance directly from help.

## Why

Current behavior rejects `/help config` with `usage: /help`, which blocks obvious discoverability for config values/enums.

## Scope

- accept `/help config` in slash-help handler
- include topic in compact `/help` topic list
- render a config-focused help section that points to `/config show` and `/config values <key>`
- add regression tests for handler and step-level slash path

## Status

Completed.

## Outcome

- `/help config` now returns a dedicated config-help section.
- compact `/help` topic list now includes `/help config`.
- regression coverage added in handler and step tests.
