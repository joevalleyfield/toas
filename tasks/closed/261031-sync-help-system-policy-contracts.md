Filed as: 261031-sync-help-system-policy-contracts
FKA:
AKA: help system policy sync; precedence and shell help; help progressive disclosure
Legacy index:

keywords: runtime, help, assets, config, policy, shell, models, usability, discoverability

Parent: `260901-help-system-design-survey`
Related: `261030-namespaced-config-policy-coalescence`; `260920-effective-policy-provenance-inspection`

# Sync Help System with Namespaced Config and Scoped Policy Contracts

Sync the packaged help catalog, session help, command usage, and progressive
disclosure handlers with recent namespaced configuration and scoped policy
architecture.

## Current Reality

Recent architecture milestones established:
1. Namespaced configuration and policy coalescence across scopes (`transient > session > workspace > user > global > defaults`).
2. Reified first-class keys `llm.target` and `shell.allowed`.
3. Winning source provenance reporting in `/config show [topic] [--sources]`.
4. Endpoint discovery and named target selection workflows (`/config endpoint`, `/models refresh`, `/model select`).

However, the help system exhibits several drift points:
- `precedence` in `src/toas/assets/help/config.yaml` has only a `config` facet; running `/help precedence` or `/help sources` fails with `usage: /help`.
- The `precedence` topic summary does not describe the 5-tier scope hierarchy or explain the winning provenance formats (`[source=session (n...)]`, `[source=file (...)]`, etc.).
- `execution` lacks aliases `shell` and `grants`, causing `/help shell` to fail and `/help config shell` to fall back to key substring search. `shell.allowed` is missing from `execution`'s `related_keys`.
- `SHELL_USAGE` in `src/toas/step.py` advertises the deprecated `head` scope alias alongside `session`.
- `render_session_help_full()` "Common goals" lists legacy direct `/config set llm.base_url ...` and `llm.model ...` rather than endpoint addition, model discovery, and `/model select`.
- `/help <topic>` command dispatch only checks single-word arguments, failing multi-word queries like `/help endpoint set`.

## Desired Reality

1. Progressive disclosure flows seamlessly:
   - `/help`: compact overview and topic index.
   - `/help <topic>` (or `/help <query...>`): plain behavioral overview with next actions and cross-pointer to configuration.
   - `/help config <topic>`: configuration knobs, related keys, schema, and pointer to `/config show [topic] [--sources]`.
   - `/config show [topic] [--sources]`: live effective state with source provenance tags.
2. `precedence` (aliases: `sources`, `provenance`) provides both `plain` and `config` facets explaining the 5-tier scope stack and provenance formatting.
3. `execution` includes `shell` and `grants` aliases, reified `shell.allowed`, and scoped grant actions.
4. `SHELL_USAGE` advertises canonical scopes (`global|user|workspace|session|transient`).
5. Session help full examples reflect modern named model targets and discovery.
6. Full test coverage (100.00%) maintained across all test suites.

## Acceptance Criteria

- `/help precedence`, `/help sources`, `/help provenance` render the plain behavioral concept and point to `/help config precedence`.
- `/help config precedence` explains the 5-tier scope hierarchy and points to `/config show <topic> --sources`.
- `/help shell` and `/help grants` resolve to the `execution` plain facet.
- `/help config shell` resolves to the `execution` config facet with `shell.allowed` in `related_keys`.
- Multi-word queries like `/help endpoint set` or `/help prompt progress` resolve to their respective topics.
- `SHELL_USAGE` omits `head` from the advertised help list.
- `render_session_help_full()` common goals reference modern endpoint addition, `/models refresh`, `/model select`, and `llm.target`.
- End-to-end artifact inspection verifies the rendered help outputs match expectations.
- `./scripts/check.sh` passes at 100.00% statement coverage.

## Progress

- Opened task and established acceptance criteria.
- Added plain and config facets to `precedence` explaining the 5-tier scope hierarchy and provenance formatting.
- Added `shell` and `grants` aliases to `execution`, adding `shell.allowed` and scoped grant next actions.
- Cleaned up `SHELL_USAGE` to advertise canonical scopes (`global|user|workspace|session|transient`).
- Modernized `render_session_help_full()` "Common goals" with model target addition, discovery, and selection.
- Supported multi-word topic queries in `/help <query>`.
- Verified 100.00% statement coverage across all 155 source files (3,653 unit tests + 17 acceptance tests).
- Inspected concrete rendered artifacts end-to-end.

## Completion Evidence

- Direct end-to-end execution of `/help`, `/help full`, `/help precedence`, `/help config precedence`, `/help shell`, `/help config shell`, and `/help endpoint set`.
- `./scripts/check.sh` passes at 100.00% statement coverage.

Status: Closed.
