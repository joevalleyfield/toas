Filed as: 260904-config-help-state-feedback
FKA:
AKA: config UX; config help alias; compact config mutation output
Legacy index:

Parent: `260901-help-system-design-survey`

keywords: config, implementation, active, usability, surface

# Config Help, State Inspection, and Mutation Feedback

## Objective

Make config discovery and feedback follow the operator priority vote:
`/help config` and `/config --help` explain usage, bare `/config` inspects
current state, and `/config set` reports compact effective changes.

## Status and evidence

Ready for implementation. The parent's remaining synthesis is not a blocker.
Claimed for implementation on 2026-09-04. The bounded change covers the
config help alias and effective-state feedback at the existing operator
command seam.
Source inspection on 2026-09-04 found that `_handle_config_command` already
routes bare `/config` to show, but has no `--help` branch. `_config_set_result`
prints all flattened values. The current config collection is in
`docs/notes/help-corpus/2026-09-01-slash-help-config/`; the design note's steering
review and workboard priority vote supply the intended disclosure split.

## Acceptance criteria

- `/config --help` and `/help config` reach equivalent focused guidance with
  exact forms for inspection, categorical lookup, and setting a value. Explain
  session durability and point to persistent defaults without a full state dump.
- Bare `/config` retains `/config show` inspection behavior; `--sources` still
  exposes provenance. Guidance points to these state views rather than mixing
  their complete output into help.
- Successful `/config set <key> <value>` reports changed effective keys with
  before/after values and session scope, without unrelated settings. Include
  any real normalized/coupled effective changes. Setting an already-effective
  value reports no effective change without claiming no override was recorded.
- Preserve validation failures, durable override semantics, same-turn config
  application, secret redaction, and inert projected examples. A help request
  must not produce a config mutation or model call.
- Record a starter path from `/help` through config guidance, inspection,
  categorical lookup, and one mutation. A reader can identify the current
  value, available choices, resulting change, and its persistence boundary.

## Ownership and scope

Primary seam: `src/toas/runtime/operator_command_config_help.py` for dispatch
and command feedback. Help prose currently lives in `src/toas/step.py`; limit
changes there to its existing rendering surface. Use existing config resolution
for effective values. Do not redesign precedence, transport, durable records,
or a global help registry. Other mutation commands can receive separate
follow-ons once their effective-state reporting seam is checked.

## Verification

Add targeted handler tests in `tests/test_runtime_operator_command_handlers.py`
for help alias, read-only inspection, changed/unchanged set feedback, and
validation errors. Use step-level coverage in `tests/test_step.py` for durable
override application and inert projection, reusing existing fixtures. Check
local/RPC output parity through existing routed command coverage if affected.
Run the relevant tests and repository-required suite; record results and the
starter-path outcome here when implementing.

## Completion evidence

- 2026-09-04: Added equivalent `/config --help` routing alongside `/help
  config`, with a starter path covering effective inspection, provenance,
  categorical lookup, and session-scoped mutation. Help remains read-only and
  does not emit a config update or model call.
- 2026-09-04: Changed `/config set` feedback from a full flattened dump to a
  compact effective diff with before/after values. Unchanged values explicitly
  report that the session override was recorded; the existing update payload,
  validation, redaction, and same-turn durability paths are unchanged.
- 2026-09-04: Targeted handler and step suite passes: 370 tests; Ruff passes.
  Full suite reaches 100% coverage and passes 3098 tests, with 3 unrelated
  Vim/plugin subprocess timeouts observed in `test_vim_plugin_local_host_prompt_progress`,
  `test_vim_plugin_local_host_reasoning`, and `test_vim_plugin_real_host_smoke`.
