## Goal

Add a first-class `/config` subcommand to enumerate allowed categorical values for a config key.

## Why Now

`/config show` and `/config set` are usable, but there is no direct way to ask TOAS for valid values when a key is categorical.

## Scope

- add `/config values <key>` command handling
- expose allowed categorical values for enum-like keys
- include bool-shape value hints where relevant
- update `/config` usage/help strings
- add direct tests for categorical and non-categorical key behavior

## Constraints

- preserve existing `/config set|unset|restore|load|save|secret|backend` behavior
- keep parsing authority in config parsing layer (single source for allowed values)

## Done When

- `/config values <key>` returns allowed values for categorical keys
- unknown keys still fail with current key-validation diagnostics
- non-categorical keys return a clear "not categorical" message
- tests cover success + no-enum branches

## Completion

- added `/config values <key>` to runtime operator command handling and usage text
- added config-layer `config_value_choices` API (enum + bool choice support)
- surfaced key-specific choice output with current value and set-command examples
- covered behavior in `tests/test_config.py` and `tests/test_runtime_operator_command_handlers.py`
