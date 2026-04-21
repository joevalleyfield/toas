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
- shell execution unification and queueing: `328` umbrella with `331`-`333` (`329`, `330` landed)
  - latest follow-on landed: `393` replace_block ergonomics (`indent` accepts `int|str`, whitespace-lax matching)
  - latest follow-on landed: `394` replace_block match modes (`strict|default|lax`) with narrower default behavior
  - latest follow-on landed: `395` replace_block best-window + similarity-gated diff diagnostics for no-match errors
- agentic low-activation execution arc (procedures + lane splits): `358` umbrella with `360`-`362` (`359`, `364` landed; includes replay evolution from `356`)
- runtime and QoL hardening: `336`-`340`
  - exploratory planning follow-on opened: `415` (weak-model-safe `apply_patch` contract and recovery-oriented tool response design)
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
  - bootstrap phase `404` is complete; active decomposition focus remains `402` and `403`
- lineage-bounded projection diagnostics and fix: `354` (minimal deterministic branch repro passes; scope narrowed to oversized replay-content ingress/append interactions)
- prompt/session replay ergonomics for behavior regression: `356`
- modifier-resolution checkpoint optimization (LCP/tail replay): `365` (deferred until correctness-first pass lands)
- context assembly prototype from lens artifacts: `344`
- docs surface rebalance roadmap vs capabilities: `345` umbrella (first pass `346` landed)
- immediate shell-policy follow-up cleanup/testing tasks: complete (`371`, `372` landed)

## Next

Near-term sequencing intent:
1. execute remaining `328` umbrella subtasks in order (`331`-`333`)
2. run targeted runtime/QoL hardening from `336`, `339`, and `340` alongside shell-arc implementation (`337` landed)
3. advance `344` prototype seam to first inference-path integration
4. continue remaining shell-queue arc delivery (`331`-`333`) on top of stabilized shell grant policy surfaces
5. execute `374` in small slices: add seam tests first, refactor internals second, spin out follow-on tasks for larger smells
6. set the next coverage floor ratchet task on top of `374` now that `375` checkpoint completed
7. select next compact elimination targets under `379` after landing `390`-`392`
8. execute remaining `400` breadth-first phases through concrete subtasks (currently `402`) and open next focused follow-ons as needed

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
- umbrella `328` open
- `329` and `330` landed
- active subtasks: `331`-`333`
- immediate follow-up tasks: none (policy view/copy + contract stabilization complete)

Target outcome:
- one internal shell normalization/authorization model with deterministic queue behavior for mixed authorization sequences

### C. Runtime / UX Hardening

Why this arc exists:
- practical runtime behavior and editor workflows still benefit from tight, test-backed iterations

Current state:
- `336`: Windows daemon detachment parity
- `337`: Vim `:ToasRestart` implemented and closed
- `339`: optional thinking stream projection
  - in progress: broaden streamed reasoning extraction beyond `delta.reasoning_content` to tolerate provider-specific chunk shapes, with opt-in reasoning diagnostics
  - in progress: re-enable `reasoning_format=auto` request hint when thinking callback is active to recover backend reasoning emission where supported
  - in progress: align `runtime.streaming_mode` with core runtime settings to remove lane-dependent stream/thinking behavior
  - in progress: harden shared LLM client cache access under concurrent daemon requests
- `340`: runtime prompt-processing progress projection

### D. Context Assembly Evolution

Why this arc exists:
- hierarchical context/lensing design exists in notes but needs implementation seam

Current state:
- `344` open: Context Assembly Engine prototype from lens artifacts

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
- umbrella `358` open
- active subtasks: `360`-`362`
- `359` and `364` implemented and closed
- `356` replay runner intent remains open and is incorporated into this arc

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
  - active decomposition subtasks: `402` (shared runtime edges)

## Recently Closed

Recently closed tasks that still inform current planning:
- `412`: first tools package-shape migration slice landed by introducing `src/toas/tools_cluster/` with moved helper modules and legacy compatibility shims
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
- operator config persistence is established (`toas.toml`, durable `config_override` records, transcript/runtime capability layering)
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
