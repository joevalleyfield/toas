Filed as: 260905-config-show-filters
FKA:
AKA: filtered config inspection; config show query; config state filters
Legacy index:

Parent: `260905-help-assets-runtime-foundation`
Depends on: `260904-config-help-state-feedback`
Related: `260905-common-asset-library-migration`; `260901-help-system-design-survey`

keywords: config, surface, follow-on, usability, search, defaults, provenance

# Filtered Config State Inspection

## Objective

Extend `/config show` with compact, read-only filters so help can lead an
operator from a conceptual topic to the relevant live configuration state.

## Contract

`/config show` with no filter remains the complete effective-state inspection
surface. A positional filter selects matching configuration keys by exact key,
key prefix, or case-insensitive token match against the key name. Topic-name
resolution may be added later when the help catalog exists; this task should
keep the filter contract small and deterministic.

Examples:

```text
/config show
/config show llm
/config show llm.model
/config show timeout
/config show --sources llm
```

The existing `--sources` form remains composable with a filter. Inspection
reports state only; it must not mutate config or emit a config update.

## Scope

- Define and implement the positional filter grammar for `/config show`.
- Support exact-key, prefix, and case-insensitive token matching with stable
  deterministic ordering.
- Preserve complete unfiltered output and existing provenance output.
- Produce a clear compact no-match result that suggests `/help config` or
  `/config values <key>` where appropriate.
- Add focused runtime/step coverage for filtered, unfiltered, provenance,
  exact, prefix, token, and no-match paths.
- Document the filter contract in config help or the relevant design note.

## Non-goals

- Do not implement the help asset loader or curated topic catalog.
- Do not make `/config show` execute conceptual help or return prose topics.
- Do not add arbitrary boolean query syntax, fuzzy ranking, or topic aliases in
  this slice.
- Do not change config precedence, durability, mutation, or value lookup
  semantics.

## Acceptance criteria

- `/config show` remains backward-compatible as an unfiltered state view.
- `/config show <exact-key>` returns only the selected key.
- `/config show <prefix>` returns all matching keys in stable key order.
- `/config show <token>` finds matching key-name tokens case-insensitively.
- `/config show --sources <filter>` preserves source/provenance reporting.
- No-match output is read-only, compact, and actionable.
- Existing `/config --help` and `/help config` behavior remains intact except
  for an accurate filter hint.
- Targeted tests pass, and full required verification is recorded.

## Allowed write surfaces

- `src/toas/runtime/operator_command_config_help.py` and narrow config/runtime
  helpers;
- focused tests for config command handling and step behavior;
- config-help/design documentation;
- this task file and generated `tasks/WORKBOARD.md` sections.

## Required completion evidence

- exact grammar and matching precedence;
- examples of each supported filter form;
- targeted and full test results;
- confirmation that inspection remains read-only and provenance-safe.
