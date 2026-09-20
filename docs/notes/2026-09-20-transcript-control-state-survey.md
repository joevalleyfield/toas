# Transcript Control State Survey And Resolution Order

Status: survey complete; implementation follow-ons are intentionally separate.

This note records the observed control surfaces before introducing a generalized
transcript settings-delta or checkpoint model. It distinguishes the documented
configuration contract from the current resolver paths, which are not yet
uniform.

The normative navigation companion is [Transcript Control State And Resolution
Contract](2026-09-20-transcript-control-state-contract.md). This survey remains
the evidence inventory; the companion note states the cross-domain contract and
the current-versus-target lineage distinction.

## Executive findings

1. The documented configuration ladder is clear for the ordinary config lane:
   runtime secrets > durable session overrides > project files > global files >
   environment compatibility inputs > code defaults. See
   [`docs/notes/2026-05-09-config-precedence-principles.md`](2026-05-09-config-precedence-principles.md).
2. The implementation does not apply that ladder to one universal settings
   object. Model invocation, stream behavior, child-process environment,
   grants, workspace scope, surface selection, and host transport each have
   separate resolvers.
3. `config_override`, `shell_scope_grant`, `command_context`,
   `workspace_scope`, `target_selection`, and surface records are appended as
   non-message journal records without message parentage. Their `active_*`
   reducers scan the supplied event list in journal order. The normal step path
   supplies the whole journal, so these controls are currently history-forward,
   not branch-forward.
4. Message-authored controls such as `/env`, `/model <legacy-id>`, and
   `/endpoint <id>` are read from the reconstructed working lineage. They can
   branch with transcript content, but the default runtime context still uses
   the latest message event (the storage tip) when no explicit head is passed.
5. The full `OperatorConfig` can be loaded from TOML, but `/config save` only
   serializes `extraction`, `generation`, `llm`, `runtime`, `storage`,
   `backend`, and `backend_startup`. It omits `health_timing`, `shell`,
   `capability_advertisement`, `prompt`, `session`, `tool_writes`, and
   `diagnostics`.
6. `apply_overrides` currently reconstructs `OperatorConfig` without carrying
   `health_timing` or `prompt`, so file/session application can silently reset
   those sections to defaults. This is a resolver defect to fix before treating
   a full settings checkpoint as a trustworthy projection.
7. Child-process environment is already a transcript-control concern, but its
   precedence is distinct: host environment and call-local `env` are combined,
   transcript `/env` modifiers are applied, and the selected environment
   profile/mode is applied afterward. `replace` can intentionally discard the
   earlier layers. The same `TOAS_*` key may also be interpreted by the TOAS
   parent, so the future model must preserve the namespace distinction.

## Inventory method

The survey traced:

- every `OperatorConfig` dataclass field and the TOML/override parser;
- `/config`, `/env`, `/shell`, `/workspace`, `/cd`, `/session`, `/model`,
  `/endpoint`, `/lens`, `/intent`, and related operator handlers;
- durable record writers and `active_*` reducers in `graph.py` and
  `graph_control_state_edges.py`;
- sync and async generation policy paths;
- shell, script, runtime-family, workspace, and environment-policy execution;
- all `TOAS_*` reads in `src/toas`.

The disposition column below means “candidate scope for a future transcript
control/checkpoint model,” not a deletion decision.

## OperatorConfig registry

| Domain | Current fields | File/config-override status | Transcript command status | `/config save` | Disposition |
| --- | --- | --- | --- | --- | --- |
| Extraction | `extraction.yaml_position`, `loose_command_fallback`, `user_shell`, `operator_command`, `intent_arbitration`, `shell_staging`, `projection_shape` | TOML and `config_override` | `/config set/unset/restore/load` | yes | retain as ordinary policy deltas |
| Generation | `generation.thinking_mode`, `thinking_budget_tokens`, `max_tokens`, `avoid_terms`, `max_retries`, `retry_delay_s`, `transport_mode` | TOML and `config_override` | generic `/config` | yes | retain; generation is separate from action authority |
| Model invocation | `llm.base_url`, `model`, `provider`, `api_key_source`, `api_key_ref` | TOML and `config_override`; environment fallback varies by field | generic `/config`; `/endpoint` and legacy `/model` are message controls | yes for these fields | retain, but resolve as a model/provider domain |
| Endpoint catalog | `llm.endpoints`, including catalogs and observations | TOML; specialized endpoint commands emit config updates | `/config endpoint ...`, `/models refresh` | yes | retain as durable catalog data, not a per-step secret/checkpoint value |
| Named model targets | `llm.targets` with sparse generation overrides | TOML; named-map merge/unset support in overrides | `/config target ...` | target tables yes | retain target definitions separately from active selection |
| Runtime | `runtime.context_budget_mode`, `streaming_mode`, `async_runs`, `async_backend_mode`, `cancellation_mode`, `thinking_stream_mode`, `prompt_progress_mode`, `python_runtime`, `powershell_runtime` | TOML and generic override representation | generic `/config`; some consumers still read file-only config or ambient env | yes | retain, but split lifecycle, streaming, and child-runtime concerns |
| Health timing | `health_timing.profile`, `idle_warning_ms`, `first_frame_timeout_ms`, `inter_frame_timeout_ms`, `host_request_deadline_ms`, `recovery_timeout_ms` | TOML and valid override keys; currently lost by `apply_overrides` reconstruction | generic parser accepts the keys | no | keep as host/liveness policy; repair resolver and serialization before checkpointing |
| Storage | `storage.hot_journal_limit_mb` | TOML and override | generic `/config` | yes | infrastructure policy; checkpoint only if replay needs it |
| Assistant shell policy | `shell.assistant_timeout_s`, `shell.allowed_commands` | TOML and override | `/config`, `/shell config` | no | retain grants/timeout, with authority and lifetime labeled |
| Child environment policy | `shell.environment.mode`, profiles, bindings | TOML loader fully understands profiles/bindings; opaque `shell.environment` is not a usable scalar `/config set` lane | `/env` is message-authored; no durable env-control record; future fence-local env is absent | no | high-priority transcript-control domain; separate from TOAS control-plane env |
| Capability advertisement | `capability_advertisement.profile`, `hidden_tools` | TOML and generic override | generic `/config` | no | retain as model-facing visibility policy, not authorization itself |
| Prompt composition | `prompt.mode`, `constraints`, `ingress`, `output_profile` | TOML and valid override keys; currently dropped by `apply_overrides` | generic `/config`; `/prompt` also accepts one-shot mode/constraints | no | retain as prompt policy; repair resolver before checkpointing |
| Session | `session.transcript_path`, `bootstrap_prompt_ref` | TOML and override | `/session` emits config updates; surface binding can take precedence | no | retain path/bootstrap as session selection, not global defaults by accident |
| Tool writes | `tool_writes.newline_style` | TOML and generic override representation | generic `/config` | no | retain as materialization policy; current tool consumers read workspace file config |
| Backend startup | `backend_startup.thinking_budget_tokens` | TOML and override | generic `/config`; documented startup-only | yes | retain with explicit startup/restart semantics |
| Backend | `backend.mode`, `backend.managed_local.{command,cwd,env,health_url,health_timeout_s}` | TOML; managed-local structure is intentionally file-only for `/config set` | `/config set backend.mode`; managed-local must be edited in TOML | `backend` yes | retain backend lifecycle separately; do not conflate with model target selection |
| Diagnostics | `diagnostics.log_level`, `log_file` | TOML and valid override keys | generic parser accepts keys | no | retain as observability policy; checkpoint inclusion should be explicit |

The registry itself is not a complete “settings object” for future-step
behavior. Cwd, workspace roots, grants, active target, surface selection,
queue state, lenses, intents, and host lifecycle state live outside it.

## Durable control records and lineage

| Control | Record or source | Current reducer | Current timing | Branch/replay status |
| --- | --- | --- | --- | --- |
| Config delta | `config_override` payload; `__op__` supports unset/restore | `active_config_overrides(events)` deep-merges in event order | result node updates live config for later candidates in the same step; record is appended at persistence | whole-journal/history-forward in normal runtime; no parent/head field |
| Shell grant delta | `shell_scope_grant` with `global`, `user`, `workspace`, `head`, `session`, or `transient` scope | `active_shell_scope_grants(events)` then policy precedence `transient > session > head > workspace > user > global > defaults` | result node is persisted after step; no documented same-step live grant update | scope names do not carry a head id; whole-journal/history-forward |
| Cwd | `command_context` | `active_command_context(events)` | later steps use latest record | whole-journal/history-forward |
| Workspace roots/mode | `workspace_scope` | `active_workspace_scope(events)` | later tool/path checks use latest record | whole-journal/history-forward |
| Active target | `target_selection` | `active_target_selection(events)` | model invocation reads latest selection | whole-journal/history-forward |
| Surface binding/selection | `surface_bind`, `surface_select`, plus rebind/guardrail audit records | `surface_bindings` / `active_surface_id` | explicit surface request outranks selected context; selected binding chooses transcript path | records are not message-lineage deltas; selected surface is durable journal state |
| Lens artifacts | `lens_artifact` set/remove/reset | `collect_lens_artifacts_from_events(events)` | injected into context packet for generation | whole-journal reducer; source pointers preserve evidence but no branch parent |
| Intent and coordination | `intent`, `coordination_state` | latest records / active intent | inspection and coordination surfaces consume latest state | whole-journal; not a settings delta |
| Secrets | in-process `RUNTIME_SECRETS`; `/config secret` result node | direct runtime map | immediate; no durable config record | intentionally ephemeral; values must not enter checkpoints |

The append-only message graph does have explicit parentage and branch laws (see
[`docs/notes/2026-05-23-transcript-first-graph-rewrite-laws.md`](2026-05-23-transcript-first-graph-rewrite-laws.md)). The control records above do not currently participate in that parent graph.

## Observed resolution order by domain

### Ordinary config and model invocation

The intended documented order is:

```text
runtime secret
  > durable session override
  > local project file (toas.toml / .toas/config.toml)
  > global file (~/.toas.toml / ~/.config/toas/config.toml)
  > environment compatibility input
  > code default
```

File discovery applies global files first, then project files, so project values
win. `config_override` is then applied over the discovered file config.
`PolicyResolver.resolve_settings` makes session-applied model/provider values
win over file values, while API-key material uses runtime secret first and then
the configured `env` or `keyring` source. Source reporting is incomplete: the
general `build_config_sources` helper only recognizes environment provenance for
`llm.base_url` and `llm.model`, while `Settings.from_env()` also reads provider,
trace, transport, stream mode, CA file, and API key.

There are concrete exceptions:

- `TOAS_STREAM_THINKING` and `TOAS_STREAM_PROMPT_PROGRESS` override the
  corresponding runtime config in `resolve_stream_flags`.
- `TOAS_STREAM_STDOUT` is a fallback when `runtime.streaming_mode` remains at
  its default, but an explicit transcript env modifier wins over both.
- `TOAS_LLM_TRANSPORT_MODE` and `TOAS_LLM_STREAM_MODE` are read by
  `Settings.from_env()` but the normal policy path replaces them with
  `generation.transport_mode` and `runtime.streaming_mode`; they are therefore
  compatibility inputs with an inconsistent effective path.
- The sync generation runner reads streaming/debug flags directly from ambient
  environment when no CLI option is passed; the async start path resolves some
  flags through the policy helper. Sync and async provenance therefore differs.

### Child-process environment

The observed order is:

```text
host process environment
  -> call-local tool env mapping
  -> transcript `/env` set/unset modifiers
  -> selected `shell.environment` profile and mode
```

`replace` intentionally discards the lower layers. Profile variables override
same-name values and PATH prepend/append composition is deduplicated. Transcript
modifiers are currently parsed from user message content by
`resolve_effective_env_modifiers(working)`, not written as a dedicated control
record. `/env` with no arguments prints usage rather than an effective-state
view, despite the earlier task intent to provide inspection.

The child-process path is separate from parent TOAS control, even when the key
has a `TOAS_*` spelling. A transcript value such as `TOAS_STREAM_STDOUT` can
also affect the parent stream resolver for the current step, so a future
settings model must carry both the target (TOAS vs child) and the resolution
stage.

### Authority and workspace

Assistant tool calls receive workspace roots/mode, shell grants, and assistant
timeout from the step runtime. Direct user shell intent deliberately uses a
separate unbounded authority path. The grant reducer's precedence is explicit,
but its scope records are not branch-addressed. `tools._workspace_config()`
loads discovered files directly for environment profiles, configured Python/
PowerShell runtimes, and newline policy; it does not automatically load the
session override lane. This creates consumer-specific differences even when a
key is accepted by `/config set`.

### Frontier and inserted settings

Config commands already demonstrate the desired same-step shape: a
`config_update` result is applied to a live config before later candidates in
the same frontier consequence sequence, and the resulting `config_override`
record is appended on completion. Other controls do not have the same general
mechanism. Environment modifiers are derived once from the current working
messages; grants, cwd, workspace, target, and surface updates are materialized
as separate records after consequence execution. There is no general
branch-addressed “insert control delta, run one inline consequence, then close”
operation today.

## TOAS control-plane environment inventory

These variables must not be treated as child-process environment settings just
because the namespace overlaps:

| Family | Examples | Role | Durable/config status |
| --- | --- | --- | --- |
| CLI transport | `TOAS_RPC_MODE` | choose local/RPC routing | env-only compatibility; not transcript policy |
| LLM compatibility | `TOAS_LLM_BASE_URL`, `MODEL`, `PROVIDER`, `API_KEY`, `CA_FILE`, `TRACE`, `TRANSPORT_MODE`, `STREAM_MODE` | bootstrap or fallback model invocation | mixed: some have config fields, some remain env-only or are shadowed |
| Stream/debug | `TOAS_STREAM_STDOUT`, `STREAM_THINKING`, `STREAM_PROMPT_PROGRESS`, `DEBUG_PROMPT_PROGRESS`, `DEBUG_PROMPT_PROGRESS_FILE` | presentation and diagnostics | mostly ambient/one-shot; stdout has transcript modifier overlap |
| Async/daemon | `TOAS_ASYNC_BACKEND_MODE`, `ASYNC_LOCAL_STRICT_GUARD`, `DAEMON_ASYNCIO`, `DAEMON_ASYNCIO_WATCH`, `DAEMON_ASYNCIO_CANCEL`, `CANCEL_TERMINAL_TIMEOUT_S`, `FOLLOW_POLL_INTERVAL_S`, `TOOL_STREAM_FLUSH_BYTES`, `TOOL_STREAM_FLUSH_MS` | transport and lifecycle tuning | env-only or runtime-adjacent; not ordinary transcript config today |
| Host protocol | `TOAS_HOST_STDIO_JSON`, `HOST_IGNORE_OWNER_CHECK`, `HOST_STDIO_WIRE_LOG*`, `HOST_STDIO_DIAG_LOG*`, `HOST_SUBSCRIBE_DEADLINE_CAP_S`, `HOST_STDIO_OS_WRITE`, `OWNER_KIND`, `OWNER_ID` | host bootstrap, ownership, wire/diagnostic behavior | process/host state; keep out of ordinary settings checkpoint |
| Debug/test harness | `TOAS_DEBUG_BREAK_LLM_REQUEST_SHAPE`, `DEBUG_FORCE_LLM_FAILURE`, `TOAS_ACCEPTANCE_*` | test and failure injection | out of product settings scope |

`TOAS_HOST_SESSION_PATH` is historical only: the host-session retirement task
replaced it with an explicit `host_session_path` request field. It should not be
reintroduced as a settings source.

## Candidate scope cuts, made after inventory

The broad inventory supports these cuts for the first generalized transcript
settings model:

1. **Cut host/bootstrap and test-only environment.** These configure transport
   processes or acceptance harnesses, not transcript intent. Preserve them as
   explicit host/diagnostic inputs.
2. **Cut ephemeral secrets from serialized checkpoints.** Preserve provenance
   (`runtime_secret`/source reference) without serializing values.
3. **Cut derived operational records** such as run lifecycle, queue status,
   anchors, result/tool observations, and diagnostic log paths from the
   canonical settings delta. They remain history/audit state.
4. **Do not cut child-process environment.** Include it as a named policy
   domain, but keep its target and merge/replace semantics distinct from TOAS
   control-plane environment.
5. **Do not cut grants, workspace roots, target selection, or session/surface
   selection.** They are exactly the non-file-serializable, future-step controls
   motivating transcript deltas. Their follow-on representation may remain
   record-specific rather than forcing one flat schema.
6. **Defer a full checkpoint as a canonical record.** First make lineage-aware
   deltas authoritative; use a checkpoint only as a validated derived view or
   acceleration artifact.

## Recommended decomposition

1. **Survey/contract follow-on:** repair and test lineage-aware reduction for
   every transcript-scoped control record. A reducer should take an explicit
   selected message head/lineage and define insertion parentage; it must not
   scan the storage tip by default.
2. **Config round-trip follow-on:** make `OperatorConfig` application and save
   complete (`health_timing`, `prompt`, shell/environment, capability,
   session, tool writes, diagnostics) and expose per-key provenance that matches
   the actual consumer path.
3. **Control-delta follow-on:** retain record-specific deltas but give each
   record a common lineage/parent envelope and branch-forward default. Preserve
   same-step live updates where a command is sequenced before a later
   consequence.
4. **Child-environment follow-on:** add explicit inspection and eventually
   inline fence-local env, with a precedence table that names call-local,
   transcript, profile, and host layers. Do not use TOAS env compatibility
   variables as a generic override mechanism.
5. **Checkpoint projection follow-on:** only after the previous steps, define a
   full-state view that records its source head, covered deltas, and validation
   status. It should be replayable but not replace individual deltas.

## Unresolved decisions

- Whether the common lineage envelope is a parent message id, a selected head
  id plus sequence, or a more general control frontier reference.
- Whether “head” shell scope should become a real head-bound scope or be
  retired in favor of explicit lineage deltas.
- Which runtime/transport controls are worth promoting from env-only
  compatibility inputs into transcript policy after host/bootstrap cuts.
- Whether settings insertion is represented as a control record adjacent to a
  user message, an inline transcript step, or both.
- How checkpoint validation should handle missing/retained history segments and
  intervening deltas.

## Evidence index

- Config contract: [`docs/notes/2026-05-09-config-precedence-principles.md`](2026-05-09-config-precedence-principles.md)
- Config lifecycle precedent: [`tasks/closed/325-config-override-lifecycle-load-save-restore-and-unset.md`](../../tasks/closed/325-config-override-lifecycle-load-save-restore-and-unset.md)
- Transcript env precedent: [`tasks/closed/310-transcript-env-modifiers-as-execution-surface.md`](../../tasks/closed/310-transcript-env-modifiers-as-execution-surface.md)
- Grant lanes: [`tasks/closed/330-semi-durable-shell-grants-transcript-and-config-lanes.md`](../../tasks/closed/330-semi-durable-shell-grants-transcript-and-config-lanes.md)
- Environment policy: [`tasks/open/260621-windows-shell-launcher-and-path-resolution.md`](../../tasks/open/260621-windows-shell-launcher-and-path-resolution.md)
- Host env retirement: [`tasks/closed/260620-retire-host-session-path-env-coupling.md`](../../tasks/closed/260620-retire-host-session-path-env-coupling.md)
- Branch laws: [`docs/notes/2026-05-23-transcript-first-graph-rewrite-laws.md`](2026-05-23-transcript-first-graph-rewrite-laws.md)
- Implementation owners: [`docs/runtime-ownership.md`](../runtime-ownership.md), `src/toas/config.py`, `src/toas/config_overrides.py`, `src/toas/runtime/policy.py`, `src/toas/runtime/environment_policy.py`, `src/toas/graph_control_state_edges.py`, `src/toas/runtime/step_context_runtime.py`, and `src/toas/runtime/session_step_edges.py`.
