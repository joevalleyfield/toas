# TOAS Roadmap

## Purpose

This roadmap is forward-looking planning, not a full implementation ledger.

Use it to answer:
- what is active now
- what should land next
- what open arcs exist

Current capability shape belongs in `docs/capabilities.md`.

## Now

Open arc clusters in progress:
- shell execution unification and queueing umbrella `328` is now complete (`329`-`333` all closed)
  - `331` completion landed: replay queue continuation coverage now explicitly includes `--skip` / `--cancel` / terminal-resume behavior on durable `execution_queue` state
  - `333` completion landed: canonical callable schema docs now reflect `operation` + `params` + optional `intent` with compatibility aliases and shell payload ambiguity guard
  - `332` previously closed: shell-only tool-plan lists project compactly by default (single + multi-call, multiline/heredoc-safe), while mixed/non-shell plans remain YAML and `/extract --verbose` provides canonical YAML preview/adopt
  - explicit regression follow-on landed: `440` (disallowed assistant `shell_script` block now auto-stages into user turn with regression coverage)
- agentic low-activation execution arc (procedures + lane splits) is complete: `358` umbrella and subtasks `359`-`362`, `364` are implemented (including replay evolution from `356`)
  - latest `360` slice landed: deterministic tool error repair hints now include compact `next valid shape` guidance for common invalid-argument failures (`shell`, `shell_script`, `capability_help`, `apply_patch`, generic missing args)
  - latest `361` slice landed: packaged procedure library plus invokable `operation: procedure` surface (`name`, optional `dry_run`) with default procedures and template-linked bootstrap prompt fragment
  - latest `362` slice landed: first-class `toas replay-script` command for append-first progressive replay with `prompt`/`procedure` step sources and artifact capture (`steps`, `events_tail`, `session_tail`)
  - exploratory tooling follow-on closed: `419` (first-class code introspection survey tool for weaker models)
- runtime and QoL hardening: `336`-`340` implementation set is complete
  - daemon/vim discovery follow-on closed: `467` (Vim plugin default daemon discovery paths aligned to daemon-owned `.toas/` endpoints; legacy fallback retained)
  - env-modifier follow-on closed: `468` (`/env set|unset` transcript modifier resolution now scans multiline user blocks so state remains sticky across turns even when `/env` is non-terminal)
  - exploratory planning follow-on opened: `415` (weak-model-safe `apply_patch` contract and recovery-oriented tool response design)
  - precedence regression follow-on `441` now closed (user-frontier trailing slash command precedence restored over mixed callable-plan execution)
  - arbitration-policy follow-on `442` now closed (mixed-intent ordering modes, per-turn IDs, and queue-backed continuation behavior completed)
  - latest `442` slice landed: user-frontier mixed-intent arbitration policy now wired via `extraction.intent_arbitration` (`first_wins|last_wins|in_order`, default `in_order`) with deterministic operator->plan->shell execution ordering and mode coverage
  - latest `442` slice landed: `/replay` candidate surfaces now include replay intent IDs (`#rN`) and `/replay --index` accepts `n|rN` selectors
  - latest `442` slice landed: mixed user-frontier consequence nodes now include `intent_execution` metadata for multi-intent turns (`id/kind/order/total/arbitration`)
  - latest `442` slice landed: `/outline` now surfaces persistent mixed-intent and queue handles when present on message metadata (`intent:dN`, `queue:qN`)
  - latest `442` slice landed: `/help` common-goals now includes explicit `extraction.intent_arbitration` examples (`in_order|first_wins|last_wins`)
  - latest `442` slice landed: `extraction.intent_arbitration=strict` now blocks ambiguous mixed-intent user turns with explicit detected-handle diagnostics
  - latest `442` slice landed: `/help` now includes strict arbitration and replay/queue continuation examples for mixed-intent workflows (`strict`, `/replay --index #r1`, `/queue approve`)
  - latest `442` slice landed: `toas history` recent message summaries now surface handle annotations from message metadata when present (`intent:dN`, `queue:qN`)
  - command-plane authoring/projection follow-on `443` now closed (multiline script ergonomics, projection-shape controls, and inert/escape semantics completed)
  - latest `443` slice landed: `/help commands` now emits inert-region-wrapped slash examples and extraction paths ignore intent inside inert regions (`[[inert]]` ... `[[/inert]]`)
  - latest `443` slice landed: turn-header `!inert` (first non-empty line) now suppresses tool/op extraction while preserving slash-command potency
  - latest `443` slice landed: `extraction.projection_shape` (`auto|yaml|shell`) now controls `/extract` candidate/adopt projection and assistant auto-stage projection with shell-to-yaml fallback for non-representable shell views
  - latest `443` slice landed: replay queue continuation now has a compact `/queue` alias with default-approve semantics and active-queue ambiguity guards (`/queue [resume|approve*|skip|cancel]`)
  - latest `443` slice landed: `/extract` now supports per-command shape override via `--shape <auto|yaml|shell>` for preview/adopt rendering without mutating global extraction config
  - latest `443` slice landed: markdown-native inert fences now dud intent extraction inside ` ```inert ... ``` ` regions (alongside existing `[[inert]]` markers)
  - latest `443` slice landed: `/help commands` now explicitly advertises both inert region forms for multiline-safe authoring (`[[inert]]` and fenced ` ```inert ... ``` `)
  - latest `443` slice landed: `/help commands` now includes a concrete fenced inert snippet example (` ```inert ... ``` `) for direct multiline authoring copy/paste
  - latest `443` slice landed: `/help commands` now includes an inert callable YAML example (`[[inert]]` + ```yaml) for non-potent callable authoring
  - latest `443` slice landed: inert stripping now accepts info-string aliases where fence headers include `inert` (for example ```text (inert response))
  - latest `443` slice landed: `/help commands` now includes a concrete ` ```text (inert response) ` snippet alongside ` ```inert ` examples
  - latest `443` slice landed: `/help commands` now includes explicit compact queue controls with default-approve annotation (`/queue [resume|approve*|skip|cancel] [qN]`)
  - `339` closed: optional thinking stream projection path completed (policy-gated stream projection, provider-shape-tolerant reasoning extraction, targeted request hints, and client-cache concurrency hardening)
  - `340` closed: runtime prompt-processing progress projection completed (telemetry extraction, policy toggle, replacement-style stream rendering, and async-path wiring/tests)
  - windows compatibility follow-ons landed: `438` (Vim msysgit path normalization compatibility) and `439` (Windows-safe signal defaults without `SIGKILL`)
  - cancellation regression follow-on landed: `413` (default async dispatch back to subprocess path for prompt cancel responsiveness)
  - patch ergonomics follow-on landed: `414` (`apply_patch` multi-`@@` support within a single `*** Update File` hunk)
  - streaming resilience follow-on landed: `416` (reasoning parse-failure fallback + partial/salvaged stream-content recovery)
  - streaming resilience follow-on landed: `418` (reasoning-only stream output fallback when no content delta is emitted)
- coverage-led refactor/testability pass: `374` (use targeted coverage increases to surface and remove deferred code smells)
  - first ratchet slice `375` landed (floor raised to 80 with focused module-level coverage gains)
  - first module subtasks landed: `376` (rpc tcp/transport), `377` (llm stream/reasoning), `378` (daemon async/fallback orchestration)
  - 100%-first noise-burndown pass `379` active: landed targets `380`/`381`/`382`/`383` (`rpc_transport`, `transcript`, `rpc_client`, `capability_prompts`)
  - latest target status: `384` landed (`shell_grants`), `385` closed at `99%` by design-signal decision
  - follow-on `386` landed: shell intent/grants parser simplification reduced fallback/test contortions
  - latest target status: `387` landed (`secrets`), `388` landed (`rpc_windows`)
  - latest target status: `389` landed (`rpc_protocol`)
  - latest target status: `390` landed (`shell_intent`), `391` landed (`rpc_unix`), `392` landed (`rpc_tcp`)
  - staged follow-on umbrella `396` landed for `tools.py`, `step.py`, and `cli.py`
  - first slice `397` landed: `tools.py` pure-seam/diagnostics coverage pass (`tools.py` to `88%`)
  - second slice `398` landed: `step.py` frontier-stage helper extraction (`step.py` to `79%`)
  - third slice `399` landed: `cli.py` async/rpc handler seam pass (`cli.py` to `89%`)
  - decomposition follow-on `400` opened with breadth-first module plan for `tools.py`/`step.py`/`cli.py`/`daemon.py`
  - decomposition execution subtasks opened: `401` (phase-0 boundary freeze), `402` (shared runtime edges), `403` (`cli`/`daemon` handlers), `404` (`step`/`tools` bootstrap)
  - `401` closed after phase-0 boundary inventory + contract-lock tests
  - active focus shifted to `402`: first shared runtime-edge extraction landed (`runtime_edges` rpc gating/wrapper helpers) and CLI adopted call sites
  - latest `402` shared runtime-edge slice landed: extracted config/runtime policy resolution helpers to `runtime/policy_edges` and adopted daemon + CLI call sites
  - latest `402` shared runtime-edge slice landed: extracted transcript block/newline rendering helpers to `runtime/rendering_edges` and adopted first CLI call sites
  - latest `402` shared runtime-edge slice landed: extracted shared content-preview formatter in `runtime/rendering_edges` and adopted diff/ancestry CLI call sites
  - latest `402` shared runtime-edge slice landed: extracted shared lineage find/format helpers to `runtime/lineage_edges` and adopted CLI diff/ancestry call sites
  - latest `402` shared runtime-edge slice landed: extracted presentation/output line helpers to `runtime/presentation_edges` and adopted CLI block/rpc/heads/history formatting call sites
  - latest `402` shared runtime-edge slice landed: extracted RPC payload shaping helpers to `runtime/rpc_payload_edges` and adopted CLI workdir/optional-field payload call sites
  - latest `402` shared runtime-edge slice landed: extracted history-view row-input helpers to `runtime/history_view_edges` and adopted CLI heads/history preparation call sites
  - latest `402` shared runtime-edge slice landed: extracted stream-presentation format helpers to `runtime/stream_presentation_edges` and adopted `_StreamPresenter` formatting call sites
  - latest `402` shared runtime-edge slice landed: extracted session-file newline read/write helpers to `runtime/session_file_edges` and adopted CLI session update/rebuild call sites
  - latest `402` shared runtime-edge slice landed: extracted diff/ancestry view assembly helpers to `runtime/diff_ancestry_view_edges` and adopted CLI diff/ancestry rendering call sites
  - first `403` implementation slice landed and closed: `405` (CLI async/rpc lifecycle command handler extraction into `cli_async_commands`)
  - next `403` implementation slice landed and closed: `406` (daemon op-dispatch orchestration extraction into `daemon_op_dispatch`)
  - latest `403` daemon slice landed: extracted daemon request payload-validation contract/mapping into `daemon_request_contract` with `daemon.py` compatibility aliases
  - latest `403` daemon slice landed: extracted local-op dispatch/workdir/default-op helpers into `daemon_local_ops` with `daemon.py` compatibility wrappers
  - latest `403` daemon slice landed: extracted async run-store/watch/cancel state APIs into `daemon_run_store` with `daemon.py` compatibility aliases
  - latest `403` daemon slice landed: extracted pid/path/liveness process-control helpers into `daemon_process_control` with `daemon.py` compatibility wrappers
  - latest `403` daemon slice landed: extracted subprocess/warm async runner internals into `daemon_async_runner` with `daemon.py` compatibility wrappers
  - latest `403` daemon slice landed: extracted op-handler implementations and `_OP_HANDLERS` map assembly into `daemon_handlers` with `daemon.py` compatibility wrappers
  - latest `403` package-shape slice landed: migrated daemon entrypoint/helpers to `src/toas/daemon/` package with `toas.daemon` module-run continuity and temporary `daemon_*` compatibility shims
  - `403` closed after daemon command/handler decomposition, package-shape migration, and post-migration daemon coverage push
  - first `404` implementation slice landed and closed: `407` (step frontier helper cluster extraction into `step_frontier`)
  - follow-up housekeeping: post-extraction lint normalization (`ruff --fix`) landed to keep active decomposition branches style-clean
  - first tools-side `404` implementation slice landed and closed: `408` (tools registry/validation/dispatch helper extraction into `tools_registry`)
  - next tools-side `404` implementation slice landed and closed: `409` (tools execute_plan orchestration extraction into `tools_execution`)
  - next tools-side `404` implementation slice landed and closed: `410` (tools result rendering extraction into `tools_rendering`)
  - package-shape migration runtime slice landed and closed: `411` (runtime subpackage with compatibility shims for legacy imports)
  - package-shape migration tools slice landed and closed: `412` (tools helper subpackage with compatibility shims for legacy helper imports)
- bootstrap phase `404` is complete; `402` and `403` are complete
- next `400` follow-on decomposition queue opened from fresh `code_survey`: `426`-`430` (operator command family split, CLI assembly/dispatch split, tools patch+survey split, daemon facade thinning pass 2)
  - latest `400` follow-on slice landed: `426` runtime operator-command family decomposition (`execute_operator_command` split into focused handler modules with thin facade dispatch)
  - latest `400` follow-on slice landed: `427` CLI session assembly/side-effect extraction (`_stitch_frontier_records` + `_apply_result_side_effects` moved behind runtime module wrappers)
  - latest `400` follow-on slice landed: `428` CLI main dispatch decomposition (`main()` now delegates command/arg routing to `cli_dispatch`)
  - latest `400` follow-on slice landed: `429` tools apply-patch/code-survey extraction (`tools.py` wrappers now delegate to `tools_cluster` patch/survey modules)
  - latest `400` follow-on slice landed: `430` daemon facade-thinning second pass (`daemon/__init__.py` helper/process clusters extracted to `daemon/facade_helpers.py` and `daemon/facade_process.py`)
  - next `400` follow-on decomposition queue opened from refreshed `code_survey`: `431`-`433` (runtime operator handler function decomposition for `config/help`, `prompt/workspace`, and `extract/replay` + bounded `step_runtime` seam)
  - latest `400` follow-on slice landed: `431` runtime config/help handler decomposition (split into focused helper units with thin command dispatch and direct helper-branch tests)
  - latest `400` follow-on slice landed: `432` runtime prompt/workspace handler decomposition (split into per-command helpers with direct compact/cd helper-path tests)
  - latest `400` follow-on slice landed: `433` runtime extract/replay + bounded step-runtime seam decomposition (parser/collector/renderer helpers plus `run_step` dependency/frontier intent helper seams)
  - next `400` follow-on decomposition queue opened from post-`433` reassessment: `434`-`436` (tools execution/validation boundary extraction, capability/help rendering extraction, and shell boundary/user-shell extraction)
  - latest `400` follow-on slice landed: `434` tools non-shell execution/validation extraction (`read/write/search/echo_block/get_structure` moved to `tools_cluster/basic_ops.py` with facade wrappers retained in `tools.py`)
  - latest `400` follow-on slice landed: `435` tools capability/help rendering extraction (`capability_help` topic/detail/profile helpers moved to `tools_cluster/capability_help_ops.py` with facade wrapper retained in `tools.py`)
  - latest `400` follow-on slice landed: `436` tools shell boundary extraction (`run_user_shell`/`execute_shell_call`/validation helpers moved to `tools_cluster/shell_ops.py` with compatibility wrappers retained in `tools.py`)
  - post-`436` reassessment opened the next `400` queue for remaining high branch-density hotspots (`config` parsing/overrides split, `cli_dispatch` routing split, `daemon.async_runner` warm/process split, `tools_cluster.file_ops` matcher/diagnostics split, runtime config-backend shaping split, and final `step_runtime.run_step` phase split)
  - latest `400` follow-on slice landed: config parsing/overrides split (`config.py` now delegates coercion to `config_parsing.py` and override materialization to `config_overrides.py` with facade compatibility retained)
  - latest `400` follow-on slice landed: CLI dispatch routing split (`watch`/`prompt`/`ancestry` option parsing extracted from `cli_dispatch.dispatch_main` to `cli_dispatch_ops.py`)
  - latest `400` follow-on slice landed: daemon async warm/process split (`start_async_step_warm` in-process execution worker extracted to `daemon/async_runner_warm.py`, keeping `daemon/async_runner.py` focused on run orchestration)
  - latest `400` follow-on slice landed: tools file matcher/diagnostic split (`replace_block` matcher selection + mismatch diagnostics extracted from `tools_cluster/file_ops.py` to `tools_cluster/file_match_ops.py`)
  - latest `400` follow-on slice landed: runtime config/backend shaping split (`/config backend` list/add/set/remove/capture logic extracted from `runtime/operator_command_config_help.py` to `runtime/operator_config_backend_ops.py`)
  - latest `400` follow-on slice landed: `step_runtime` phase split (`run_step` now delegates transcript-delta assembly and frontier consequence execution to focused helpers with direct helper tests)
  - latest `400` follow-on slice landed: CLI replay-script command flow split (`run_replay_script_local` extracted from `cli.py` into `cli_replay_script` with explicit dependency wiring and direct module test coverage)
  - latest `400` follow-on slice landed: `/config backend` branch decomposition in `runtime/operator_config_backend_ops.py` (`config_backend_result` now delegates focused list/add/remove/set/capture helpers)
  - latest `400` follow-on slice landed: config coercion decomposition in `config_parsing.py` (`parse_config_value` now delegates dedicated int/float/choice/bool/default-field helpers)
  - latest `400` follow-on slice landed: session side-effect fan-out decomposition in `runtime/session_step_edges.py` (`apply_result_side_effects` now delegates queue/lens/context/workspace/secret/config/save/session helpers)
  - latest `400` follow-on slice landed: lens command helper decomposition in `runtime/operator_command_prompt_workspace.py` (`_handle_lens` now delegates extracted module-level set/parser helpers)
  - latest `400` follow-on slice landed: tools duplicate matcher/diagnostic helper removal (`tools.py` now relies on `tools_cluster/file_match_ops.py` as the single owner for replace-block matcher diagnostics)
- lineage-bounded projection diagnostics and fix: `354` (minimal deterministic branch repro passes; scope narrowed to oversized replay-content ingress/append interactions)
- prompt/session replay ergonomics for behavior regression `356` are complete and folded into the finished low-activation execution arc
- draft-import capture follow-on landed and closed: `449` (procedure parameter/default interpolation, procedure step-result visibility, and Windows shell env parity hardening with tests)
  - intake checklist companion landed and closed: `450` (exhaustive per-commit import ledger for `9401df55` and `8fc11687`)
- modifier-resolution checkpoint optimization (LCP/tail replay): `365` (deferred until correctness-first pass lands)
- context assembly prototype from lens artifacts: `344`
  - latest `344` slice landed: first inference-path context assembly seam (`runtime/context_assembly`) with deterministic packet construction from durable `metadata.lens_artifact` artifacts plus generation-time quality-gate guidance (`coverage|staleness|conflict`)
  - latest `344` slice landed: operator-facing `/lens` durable lane (`list|set|remove|reset`) now writes `lens_artifact` records to history and context assembly consumes that lane during generation packet assembly
  - `344` execution subtasks opened: `444`-`448` (lens authoring ergonomics, write-time validation, packet inspection surface, remediation workflow, and packet-shaping expansion)
  - latest `444` slice landed: `/lens set` now supports flag-form authoring plus fenced multiline distillation capture while preserving positional compatibility
  - latest `445` slice landed: `/lens set` now validates source pointers against known message IDs at write time and emits explicit replacement diagnostics for duplicate-title updates
  - latest `446` slice landed: `/lens packet` now exposes context packet observability (goal/artifact summary + quality status/detail) using the same assembly and gate path as generation
  - latest `447` slice landed: generation quality-gate failures now project code-specific remediation commands and `/lens doctor` provides compact packet-health diagnostics
  - latest `448` slice landed: generation request preparation now applies deterministic sectioned packet shaping (goal/distillations/evidence/constraints/limits) with bounded growth and truncation signaling while preserving no-artifact parity
  - `344` subtask chain `444`-`448` is complete
  - exploratory compaction follow-on `420` is now implemented (folded outline seam, expansion triggers, observability, command controls, and generation-path shaping)
- docs surface rebalance roadmap vs capabilities: `345` umbrella (first pass `346` landed)
- help-surface follow-on landed and closed: `451` (`/help tools` now renders required + optional/default arg metadata, including `code_survey` defaults)
- help-ux follow-on landed and closed: `452` (compact default `/help`, `/help full`, and explicit `/help approvals` surface)
- arbitration-ordering correction follow-on landed and closed: `453` (`in_order`/`first_wins`/`last_wins` now honor user-message textual intent ordering rather than fixed intent-type priority)
- config ergonomics follow-on landed and closed: `454` (`/config values <key>` categorical value enumeration surface)
- slash extraction safety follow-on landed and closed: `455` (slash commands execute only from column-1 line starts)
- transcript path/config follow-on `456` closed (decoupled hardcoded `session.md`; configurable workspace-local session paths supported)
- config layering follow-on `458` closed: global + hidden project config path discovery landed with backward-compatible `toas.toml` fallback
- config layering diagnostics follow-on `460` closed (concrete source-path identity in `/config show --sources` plus `/config paths` discovered-path introspection)
- runtime state layout companion `459` closed (default runtime artifacts now under `.toas/` with legacy events-path fallback compatibility)
- intent-lane follow-on `462` closed (durable intent records, `/intent` command surface, `toas intents` read surface, and lineage-safe invariants with coverage)
- `456` follow-on tasks opened: `463` (session identity orchestration), `464` (cross-repo intent routing scope)
- transcript control-lane follow-on opened: `465` (`TOAS:CONTROL` operator-only lane with durable ordering parity and explicit LLM-projection exclusion)
- functional acceptance epic bootstrap opened: `469` (foundational long-horizon scenario: complete a change request on a repository end-to-end with interruption/recovery and durability evidence)
- operator-api seam follow-on opened: `470` (CLI-thin-over-API migration path plus acceptance layer taxonomy to lift scenario verification from low-level internals to operator-equivalent surfaces; linked to `469`/`400`/`374`)
- config sequencing/precedence clarity follow-on opened: `466` (explicit `/config` timing + precedence contract and diagnostics/help alignment)
- immediate shell-policy follow-up cleanup/testing tasks: complete (`371`, `372` landed)

## Next

Near-term sequencing intent:
1. execute `374` in small slices: add seam tests first, refactor internals second, spin out follow-on tasks for larger smells
2. execute `460` implementation slices (config source identity + discovered-path diagnostics)
3. set the next coverage floor ratchet task on top of `374` now that `375` checkpoint completed
4. re-run `code_survey` for the next queue after landing post-decomposition coverage tightening
5. execute `470` in lockstep with `469`: extract operator API seam (`step` first), keep CLI thin-over-API, and add minimal CLI subprocess smoke checks

## Open Arcs

### A. Real-Environment Backend Adaptation And Prompt-Lane Alignment

Why this arc exists:
- live backend behavior has exposed seams that do not appear in ideal OpenAI-compatible paths

Current state:
- this arc is functionally complete for current scope (`298`-`306`, `308`-`315` closed)
- follow-on work should open as new tasks when additional probing/runtime adaptation scope is identified

### B. Unified Shell Execution And Authorization

Why this arc exists:
- shell behavior still has syntax/context friction across assistant proposals and user-staged execution

Current state:
- umbrella `328` closed
- `329`-`333` landed and closed
- explicit regression follow-on `440` implemented and closed (assistant disallowed `shell_script` now auto-stages)
- immediate follow-up tasks: none (policy view/copy + contract stabilization complete)

Target outcome:
- one internal shell normalization/authorization model with deterministic queue behavior for mixed authorization sequences

### C. Runtime / UX Hardening

Why this arc exists:
- practical runtime behavior and editor workflows still benefit from tight, test-backed iterations

Current state:
- `336`: Windows daemon detachment parity (implemented and closed)
- `438`: Vim msysgit path normalization compatibility (implemented and closed)
- `439`: Windows-safe signal defaults without `SIGKILL` (implemented and closed)
- `337`: Vim `:ToasRestart` implemented and closed
- `339`: optional thinking stream projection (implemented and closed)
- `340`: runtime prompt-processing progress projection (implemented and closed)
- active exploratory follow-on: `415`

### D. Context Assembly Evolution

Why this arc exists:
- hierarchical context/lensing design exists in notes but needs implementation seam

Current state:
- `344` and `420` implementation scopes are complete; context assembly follow-ons should open as new tasks when expanded policy/ranking work is prioritized

### E. Documentation Surface Rebalance

Why this arc exists:
- roadmap drifted toward history density; user-facing capability shape needs first-class docs

Current state:
- `345` open umbrella
- `346` implemented and closed (first-pass reshape landed)

### F. Capability Help And Advertisement Profiles

Why this arc exists:
- capability detail currently enters the operator loop with too much relay friction during active tasks

Current state:
- `348` implemented and closed

### G. JSON Callable Lane (Parked)

Why this arc exists:
- JSON action-object callable semantics should be a separate explicit lane, not implied by prompt wording in the current YAML callable model

Current state:
- `349` open and parked at low priority pending explicit reprioritization

### H. Agentic Low-Activation Execution

Why this arc exists:
- weaker/local models need reusable execution procedures and expressive but explicit action lanes to maintain bias-to-action without policy drift

Current state:
- this arc is complete for current scope (`358`-`362`, `364` closed)
- follow-on tuning should open as new tasks when expanded procedure libraries or replay script semantics are reprioritized
- `359` and `364` implemented and closed
- replay-runner intent from `356` is complete and incorporated in this arc

### I. Modifier Resolution Scaling

Why this arc exists:
- transcript-derived modifier state (`/shell`, `/env`, similar command state) should scale with tail replay rather than full transcript scans once correctness is stable

Current state:
- `365` open and explicitly deferred until modifier correctness pass lands

### J. Coverage-Led Testability Refactor

Why this arc exists:
- complexity has grown in runtime paths while coverage remains below target; targeted tests can both improve reliability and reveal architectural smells worth immediate cleanup

Current state:
- `374` open: prioritize low-coverage/high-churn modules, lock seam behavior with tests, refactor internals in validated slices
- first ratchet checkpoint complete: `375` closed (80% floor + initial module slices landed)
- `379` open: 100%-first coverage noise-burndown (near-complete modules first)
- `396` closed: multi-arc refactor/coverage umbrella for `tools.py`, `step.py`, `cli.py`
  - `400` open: module decomposition follow-on for `tools.py`, `step.py`, `cli.py`, `daemon.py` with phased target module map
  - active decomposition subtasks: none (`421`-`436` landed: step operator-command/runtime, cli session-generation, tools rewrite-op, daemon facade reduction, operator-command family split, cli session assembly/side-effect extraction, cli main dispatch decomposition, tools patch/survey extraction, daemon facade thinning second pass, config/help handler decomposition, prompt/workspace handler decomposition, extract/replay + bounded step-runtime seam decomposition, tools non-shell execution/validation extraction, tools capability/help rendering extraction, tools shell boundary extraction)
  - post-`426` coverage tightening landed in-progress under `374`: added focused operator-command handler tests and raised coverage in new runtime handler modules (`extract/replay` to `85%`, `config/help` to `73%`, `prompt/workspace` to `73%`)
  - post-`430` coverage tightening landed in-progress under `374`: added daemon facade helper/process branch tests and raised full-suite total coverage to `89.64%` (`963 passed`)
  - latest `374` ratchet landed: added focused `cli_dispatch` + `daemon_run_store` branch tests, raised full-suite total coverage to `90.05%` (`970 passed`), and increased global `pytest --cov-fail-under` gate from `80` to `90`
  - latest coverage follow-on landed post-`433`: `437` helper-branch tightening for extracted runtime command-handler helper modules (`config/help` to `82%`, `prompt/workspace` to `80%`, `extract/replay` to `89%`)
  - latest `374` slice landed: added deterministic `procedures.py` resource/validation branch-matrix tests (`list` filtering/sorting plus invalid-asset and interpolation edges), lifting full-suite coverage to `91.04%` (`1130 passed`)
  - latest `374` slice landed: expanded shell + tools boundary-path coverage (`tools_cluster/shell_ops` validation/context/launcher/timeout paths and `tools.py` procedure/policy helper edges), lifting full-suite coverage to `91.36%` (`1140 passed`)
  - latest `374` ratchet landed: raised global `pytest --cov-fail-under` gate from `90` to `92` after tools duplicate-removal cleanup and full-suite verification (`1152 passed`, `92.43%`)
  - platform-structure follow-on: where behavior is strongly platform-divergent (transport/process/shell/path semantics), prefer file-level splits (`*_common.py` + `*_unix.py` + `*_windows.py`) behind a thin selector seam so irrelevant platform files/tests can be cleanly excluded per platform without branch-heavy mixed modules

## Recently Closed

Recently closed tasks that still inform current planning:
- `420`: folded context-outline exploration completed (deterministic outline seam, explicit/auto expansion triggers, observability counters, `/lens packet` mode controls, and generation-path folded shaping)
- `344`: context assembly prototype from lens artifacts completed via `444`-`448` (authoring ergonomics, write-time validation, packet inspection, remediation workflow, bounded sectioned generation shaping)
- `443`: command-plane authoring/projection shape controls completed (projection-shape policy, `!inert`, inert regions/fence aliases, queue command affordances, and help/docs examples)
- `442`: mixed-intent arbitration follow-on completed (`in_order|first_wins|last_wins|strict`, intent IDs, replay selectors, and persistent handle surfacing in outline/history)
- `340`: runtime prompt-processing progress projection completed with policy-gated prompt-progress stream callbacks and replacement-style projection in async stream output
- `339`: optional thinking stream projection completed with policy-gated reasoning deltas, provider-shape-tolerant extraction, and stream-lane coherence hardening
- `336`: Windows daemon startup detachment hardening landed with platform-branch launch kwargs (`creationflags` on Windows, `start_new_session` on POSIX) and mock-based tests
- `333`: operation schema cleanup completed with canonical callable schema documentation (`operation` + `params` + optional `intent`) and compatibility alias guidance
- `331`: queued mixed-authorization replay controls completed with explicit `skip`/`cancel`/terminal-resume continuation coverage
- `328`: shell execution unification and queueing umbrella closed after `329`-`333` completion
- `440`: assistant disallowed `shell_script` execution now auto-stages YAML into user turn in auto-staging mode; regression test moved from strict `xfail` to passing coverage
- `332`: compact executable projection parity completed (multi-call shell-plan compact default + mixed-plan YAML fallback + `/extract --verbose` canonical YAML preview/adopt path)
- `439`: daemon stop-path signal defaults are now Windows-safe (`SIGKILL` no longer required at import/default-evaluation time; fallback behavior covered by tests)
- `438`: Vim plugin `toas_workdir()` no longer forces `/c/...` to drive-letter form under `win32unix` (msysgit compatibility)
- `412`: first tools package-shape migration slice landed by introducing `src/toas/tools_cluster/` with moved helper modules and legacy compatibility shims
- `426`: `runtime/operator_commands.py` decomposed into family handlers (`prompt/workspace`, `extract/replay`, `config/help`) with thin facade dispatch and direct handler tests
- `414`: `apply_patch` now supports multi-`@@` hunks within a single `*** Update File` block, including strict late-mismatch failure and chunk-preview diagnostics
- `413`: default async step routing restored to subprocess path to recover prompt-time cancellation responsiveness
- `411`: first package-shape migration slice landed by introducing `src/toas/runtime/` with moved runtime helper modules and legacy compatibility shims
- `410`: tools result-rendering helpers/dispatch extracted to `tools_rendering`, compatibility wrapper retained in `tools.py`, and direct 100%-covered module tests landed
- `409`: tools execute-plan orchestration extracted to `tools_execution`, compatibility wrapper retained in `tools.py`, and direct 100%-covered module tests landed
- `408`: first tools-side `404` slice closed with registry/validation/dispatch helper extraction to `tools_registry`, compatibility wrappers retained in `tools.py`, and direct 100%-covered module tests
- `407`: first `404` slice closed with frontier helper extraction to `step_frontier`, compatibility aliases retained in `step.py`, and direct 100%-covered module tests
- `406`: daemon op-dispatch orchestration extracted to `daemon_op_dispatch` with compatibility wrappers retained in `daemon.py` and direct 100%-covered module tests
- `403`: phase-2 cli/daemon command-handler decomposition closed after daemon module extractions (`request_contract`, `local_ops`, `run_store`, `process_control`, `async_runner`, `handlers`), package migration to `toas/daemon/`, and targeted daemon coverage increases
- `405`: first `403` slice closed with CLI async/rpc lifecycle handler extraction to `cli_async_commands` and direct 100%-covered module tests
- `401`: phase-0 decomposition boundary freeze closed with explicit boundary inventory and contract-lock tests
- `389`: `rpc_protocol.py` reached `100%` coverage and now drops from missing-lines output
- `393`: `replace_block`/`replace_range` indent arguments now accept `int|str`; `replace_block` uses whitespace-lax matching for more robust agent edits
- `394`: `replace_block` now supports mode-gated matching (`strict|default|lax`) with `default` narrowed to blank-line whitespace tolerance
- `395`: `replace_block` no-match diagnostics now include best equal-length similarity and a gated unified diff for near matches
- `397`: first `396` tools slice landed with seam/diagnostic tests (`apply_patch` parser branches + `capability_help` alias/validation) and raised `tools.py` coverage to `88%`
- `398`: first `396` step slice landed with extracted frontier helper seams (`_assistant_loose_command_projection`, `_generation_guard_result`) and raised `step.py` coverage to `79%`
- `399`: first `396` cli slice landed with async/rpc lifecycle handler seam tests/helpers and raised `cli.py` coverage to `89%`
- `404`: phase-3 step/tools decomposition bootstrap completed via slices `407`-`412`
- `421`: extracted `_execute_operator_command` from `step.py` into `runtime/operator_commands.py` with compatibility wrapper and direct module tests
- `422`: extracted top-level `step()` orchestration into `runtime/step_runtime.py` with `toas.step.step` retained as compatibility facade
- `423`: extracted CLI generation/session runner + local step path to `cli_session_commands.py` with compatibility wrappers retained in `cli.py`
- `424`: extracted rewrite/file-op execution paths to `tools_cluster/file_ops.py` with compatibility wrappers retained in `tools.py`
- `425`: extracted daemon server/bootstrap lifecycle to `daemon/server_lifecycle.py` with compatibility facade retained in `daemon/__init__.py`
- `396`: tools/step/cli staged refactor+coverage umbrella completed via slices `397`-`399`
- `392`: `rpc_tcp.py` reached `100%` coverage and now drops from missing-lines output
- `391`: `rpc_unix.py` reached `100%` coverage and now drops from missing-lines output
- `390`: `shell_intent.py` reached `100%` coverage and now drops from missing-lines output
- `388`: `rpc_windows.py` reached `100%` coverage and now drops from missing-lines output
- `387`: `secrets.py` reached `100%` coverage and now drops from missing-lines output
- `386`: shell intent/grants parser simplification landed with explicit staged extraction/parser flow and callable parser helpers
- `385`: shell intent coverage push intentionally closed at `99%`; parser/recovery contortion signal captured and split into `386`
- `384`: `shell_grants.py` reached `100%` coverage and now drops from missing-lines output
- `383`: `capability_prompts.py` reached `100%` coverage and now drops from missing-lines output
- `382`: `rpc_client.py` reached `100%` coverage and now drops from missing-lines output
- `381`: `transcript.py` reached `100%` coverage and now drops from missing-lines output
- `380`: `rpc_transport.py` reached `100%` coverage and now drops from missing-lines output
- `378`: daemon async watch/lane fallback orchestration coverage slice landed; `daemon.py` coverage raised to `73%` with additional lifecycle/edge-path tests
- `375`: first coverage ratchet checkpoint landed (floor 80% + initial targeted slices `376`-`378`)
- `377`: LLM stream/reasoning/progress coverage slice landed; `llm.py` coverage raised to `92%` with helper/fallback/error seam tests
- `376`: TCP transport seam coverage pass landed with deterministic `rpc_tcp` + `rpc_transport` behavior tests
- `373`: transcript-safe escaping/unescaping for closed-set transcript role markers at projection/extraction boundaries (including RESULT-body rendering and streamed-delta projection paths)
- `372`: shell grant policy output contract tests for `/shell` and `/shell config` view/update surfaces
- `371`: centralized shell grant policy rendering and `/shell` usage/help copy via shared helpers
- `330`: semi-durable shell grants across transcript/config lanes with source-attributed effective policy and segmented shell-script authorization checks
- `367`: model-addressable `apply_patch` lane for structured assistant-side patch execution with strict context mismatch failure semantics
- `368`: async latency reduction via lane ladder completed for current single-session scope
- `370`: step/daemon/llm rationalization and reliability arc completed (stages 1-8)
- `369`: cleanup pass after Windows async restoration, intentionally squashed into the original fix changeset
- `366`: fix async execution on Windows with msys-vim
- `364`: shell-grant correctness in append-style transcripts
- `363`: replace_block result preview with context and line numbers
- `359`: explicit shell_script lane with policy-preserving boundaries
- `357`: project capability_help content into result blocks
- `355`: pragmatic-default template adds repo local-first few-shot entrainment (early probes had method/runtime-path confounders; corrected in task errata)
- `353`: repo-work capability advertisement includes required args and help-first guard
- `352`: capability_help shell-shape clarity and topic normalization
- `351`: remove stale JSON action entrainment and reinforce shell `argv` callable shape
- `350`: core capability advertisement includes `capability_help`
- `337`: Vim `:ToasRestart` daemon recycle command
- `348`: model-addressable capability help and advertisement profiles
- `347`: composed prompt templates as first-class assets
- `346`: roadmap compression and capability-map first pass
- `329`: unified shell authorization model and command normalization
- `315`: multi-op prompt and tool advertisement touchup
- `314`: tail-armed user structured command execution
- `313`: multiline user-shell execution and adoption semantics
- `312`: unified `/prompt` selector surface
- `311`: config capability space vs model selection state

## Compressed History (Capability Stories)

Older closed work, compressed:
- durable message-graph runtime is in place with lineage-aware stepping, branching, head/jump selection, transcript projection/rebuild, and durable non-message records
- operator command substrate is established (`command_request` / `command_result`) with adoption-oriented projection behavior
- operator config persistence is established (layered config files, durable `config_override` records, transcript/runtime capability layering)
- LLM runtime seam is established with retries, richer `llm_call` durability, backend normalization, and daemon/RPC integration
- provenance/index/inspection surfaces are established (provenance markers, correction capture, seekable index, ancestry/diff inspection)
- help and discoverability surfaces are unified across CLI and session commands

## Recurring Docs-Maintenance Lane

Recurring work (proposed and in-flight):
- keep roadmap forward-looking; compress older closures into short capability-story bullets
- keep current behavior detail in capability/reference docs rather than roadmap history
- treat this as periodic maintenance work, not one-time rewrite

## Boundaries To Preserve

Future work should preserve:
- no hidden mutable state outside durable history unless explicitly justified
- no conflation of message events with control/tool/model-call/operator-command records
- no system-side rewriting of user transcript content during ordinary operation
- no storage decisions that make lineage or replay ambiguous
