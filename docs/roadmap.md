# TOAS Roadmap

## Purpose

This roadmap is forward-looking planning, not a full implementation ledger.

Use it to answer:
- what is active now
- what should land next
- what open arcs exist

Execution policy from the closed runtime ownership arc (`525`):
- capability-first sequencing: land happy-path capability first
- add restrictions/guardrails only when backed by concrete failure evidence or cross-platform/data-integrity risk

Current capability shape belongs in `docs/capabilities.md`.
Doc intent/status guardrails (CURRENT vs DIRECTIONAL vs DRAFT) are defined in `docs/notes/2026-05-16-doc-truth-model.md`.

## Now

Active open work:
- `260614-architecture-follow-through-coordination` coordinates the top-down
  architecture follow-through after the masterplan/backend-lifecycle proof
  slice closed. It is a task-tree coordination object, not a replacement for
  `docs/architecture-masterplan.md`, `docs/runtime-direction.md`, or
  `docs/runtime-ownership.md`.
- `260620-read-file-line-window-support` closed: optional `start_line` and
  `end_line` arguments now let `read_file` return bounded line windows.
- `260619-workboard-sync-script-parser-and-identity-fix` closed: workboard
  sync now preserves full task identity and skips task-header metadata in
  fallback summaries.
- `260619-session-md-compatibility-retirement` closed: the legacy `session.md`
  fallback has been retired in favor of explicit transcript paths.
- `260620-retire-host-session-path-env-coupling` closed: host default session
  targeting now uses explicit host-owned state plus `host_session_path` payload
  threading instead of ambient `TOAS_HOST_SESSION_PATH`.
- `260620-host-stdio-reasoning-terminality-ux` closed: host-stdio substantive
  recovery now respects reasoning-stream visibility, command-only tails no
  longer fabricate assistant answers, and failed runs append a compact visible
  cause line so invariant failures do not require log-file spelunking.
- `260619-daemon-package-facade-shrinkage` closed: the daemon package root is
  now only a thin compatibility/execution-entry facade, with direct
  package-boundary coverage including `toas.daemon.__main__`.
- `260621-enable-shell-globbing` closed: user `$ ...` shell shorthand now
  regains substantive wildcard expansion via real shell routing, while
  assistant plain `shell` remains intentionally narrower than `shell_script`.
- `260626-multiline-user-shell-command-spans` closed: user-turn `$ ...`
  shorthand now collects one logical shell span across multiline quotes,
  backslash continuation, and heredoc bodies, with aligned arbitration and
  inert-fence handling.
- `260626-transcript-parallelism-design-pressures` inception: recorded the
  queue-shaped transcript parallelism pressure as architecture follow-through
  work, tied to multi-surface/projection semantics rather than jumping straight
  to multi-agent implementation.
- `260626-events-jsonl-multiplicity-and-merge-provenance` inception: recorded
  a conservative follow-on design pressure around mergeable event journals,
  keeping LCP as the primary reconciliation primitive while exploring whether
  first-new-node rebound provenance is ever justified.
- `260627-segmented-event-journal-storage-contract` closed: the first storage
  contract now fixes `.toas/events.jsonl` as the sole hot append target,
  keeps transcript LCP reconciliation hot-only while allowing hot history to be
  self-contained, empty, or independent after rotation,
  orders sealed cold/archive segments under `.toas/segments/` by monotonic
  filename ordinal, allows `.jsonl.gz` archival compaction without semantic
  deletion, and treats ordinal gaps/duplicates/ambiguous duplicate sealed
  forms as explicit invalid layout.
- `260627-graph-segmented-read-query-hardening` closed: graph-side logical
  history reads now stitch ordered sealed segments plus hot
  `.toas/events.jsonl`, support `.jsonl.gz` archival segments, refuse ordinal
  gaps/duplicates explicitly, and route `heads`/`history`/`transcript`/
  `llm-input` through the stitched seam without changing hot-only
  reconciliation.
- `260627-segmented-event-index-and-lookup-hardening` inception: split the
  index/lookup consequences of segmented storage into their own durable-state
  hardening seam.
- `260627-split-storage-rebuild-and-projection-parity` inception: captured the
  user-visible proof slice that rebuild/projection surfaces keep the same
  semantics across split storage.
- `260627-workboard-relationship-tree-builder` closed: workboard sync now
  parses explicit relationship metadata, renders a generated tree from manual
  roots in `WORKBOARD.md`, and preserves the flat open/inbox/closed sections.
- `260627-history-affordances-semantic-restaging` inception: recorded a
  white-paper style exploration of how TOAS might expose durable history as
  reusable operator material, with current skepticism toward "replay" as the
  headline product term and a bias toward restaging/refresh framing until
  parallelism yields sharper affordances.
- `260627-event-log-fsck-contract` inception: captured the immediate
  graph-integrity seam for a simple durable-history `fsck` contract after live
  duplicate-id evidence showed `.toas/events.jsonl` can be structurally
  invalid while current surfaces keep going.
- `260627-event-log-fsck-contract` closed: TOAS now has a bounded
  `fsck_logical_history(...)` contract for logical durable history, coverage
  for duplicate ids / missing parents / malformed message shape / invalid
  segment layout, and fail-closed operator behavior across `heads`,
  `history`, `transcript`, `llm-input`, `rebuild`, and `graph`.
- `260627-history-surface-corruption-semantics` inception: split the
  operator-facing contract for how `heads`/`history`/`transcript`/
  `llm-input`/`rebuild`/`graph` should behave under fatal durable-history
  corruption instead of silently disagreeing.
- `260627-fail-closed-history-query-hardening` inception: captured the
  implementation follow-through to make graph/history/projection surfaces
  refuse fatal durable-history corruption, explicitly ahead of broader
  parallel-affordance growth.
- `260627-history-recovery-tooling` inception: captured the follow-on recovery
  tooling seam for structured corruption diagnostics, duplicate-id
  disambiguation tracing, transcript/head extraction, and possible
  restaging/recombination work without weakening the new fail-closed default.
  Current pressure is now sharper after the six-surface audit (`heads`,
  `history`, `transcript`, `llm-input`, `rebuild`, `graph`): fail-closed
  refusal is correct, but the next bounded operator affordance still needs to
  answer "what can I safely inspect or extract now that normal surfaces
  refuse?"
- `260627-history-surface-user-intent-alignment` inception: captured the
  broader operator-facing audit question left after the same six-surface
  exploration: even when history is healthy, do `heads`, `history`,
  `transcript`, `llm-input`, `rebuild`, and `graph` actually answer the user
  questions their names imply, and do refusal/mutation paths preserve that
  intent clearly?
- `260628-history-root-to-head-lineage-contract` inception: split the first
  bounded implementation follow-on from the history-surface parent task so
  `history` can be narrowed into a root-to-head lineage view over the shared
  implicit anchor slice.
- `260628-history-root-to-head-lineage-contract` active: `history` now renders
  a bounded root-to-head lineage window with explicit lineage framing and
  omission text, removing the old selected-head/bind/head-summary mix from the
  default surface.
- `260628-history-root-to-head-lineage-contract` closed: `history`,
  `toas history --help`, top-level CLI help, and user-facing docs now agree on
  the bounded root-to-head lineage contract for the current default lineage.
- `260628-graph-selected-history-topology-framing` inception: split the first
  bounded graph follow-on from the history-surface parent task so `graph` can
  be framed as the topology view over the same selected history graph,
  including implicit-anchor and oversize-fallback clarity.
- `260628-requirements-parent-follow-on-discipline` inception: captured a
  small governance/doc follow-on to name and document the pattern where one
  task holds design/requirements truth while narrower follow-ons land concrete
  gap-closing slices.
- `260627-release-process-and-weekly-release-lane` active: release policy is
  now documented in `docs/release-process.md`, release notes live under
  `docs/releases/`, TOAS versions are defined as `epoch.{semver}`
  (`EPOCH.MAJOR.MINOR.PATCH`) with optional `-rN` release-fix suffixes, and
  weekly release review remains the recurring operational lane.
- `260627-release-helper-tooling` inception: captured the follow-on helper
  tooling seam for release-note scaffolding, recurring release-review run
  scaffolding, release-slice summarization, and version/tag/note consistency
  checks without turning the release lane into a black-box publish pipeline.
- `260626-shell-script-fence-safe-payload-parsing` closed: the original
  assistant-turn fenced-heredoc failure could not be reproduced on current
  code; a faithful repro now writes the expected Markdown file content, and the
  task split follow-ups for separate relative-`cwd` and multiline-allowlist
  issues discovered during triage.
- `260626-assistant-shell-script-relative-cwd-resolution` closed: assistant
  `shell_script` relative `cwd` values now resolve against the active step
  command cwd rather than ambient process cwd, with regression coverage at both
  the step and workspace-policy seams.
- `260626-multiline-shell-script-allowlist-segmentation` closed: assistant
  `shell_script` allowlist validation now treats later newline-separated
  logical shell spans as distinct command boundaries while preserving quoted
  multiline content, backslash continuation, and heredoc bodies.
- `260627-shell-script-control-word-and-assignment-grants` closed: assistant
  `shell_script` validation now skips shell control words and leading
  assignment prefixes so allowlist checks land on the actual covered command
  leaders for the supported loop/conditional/env-prefix shapes.
- `260627-live-repo-session-write-fence-decoupling` closed: the test harness
  now fences live repo `.toas/session.md` writes by protected path and
  write-capable mode across both builtins `open(...)` and `Path.open(...)`,
  with direct guard tests so production code is less coupled to opener style.
- Manual priority order for the June 26-27 intake is now:
  the remaining segmented storage proof chain
  (`260627-segmented-event-index-and-lookup-hardening` ->
  `260627-split-storage-rebuild-and-projection-parity`).
- After that proof chain, the next hardening subtree should be:
  `260627-event-log-fsck-contract` ->
  `260627-history-surface-corruption-semantics` ->
  `260627-fail-closed-history-query-hardening`.
- `260626-events-jsonl-multiplicity-and-merge-provenance`,
  `260626-transcript-parallelism-design-pressures`, and
  `260627-history-affordances-semantic-restaging` remain important framing
  tasks, but they currently serve better as decomposition pressure and
  vocabulary guidance than as the next implementation lane.
- The new corruption-hardening subtree is intentionally sequenced before
  broader history-affordance or transcript-parallelism expansion: durable
  history should fail closed on obvious graph corruption before TOAS leans on
  it for richer parallel affordances.
- inception-only child tasks now hold known architecture pressures for broad
  force-structure alignment, model backend failure handoff,
  transcript reconciliation handoff, legacy versus fidelity-adapter precedence,
  and runtime package growth pressure; backend cross-process identity,
  shell-owned lifecycle design, edge fidelity-adapter inventory, and
  crash-surviving activity stream replay are parked or marker-only
- no broad decomposition/coverage umbrella is currently active; open focused
  implementation tasks when concrete domain, failure, or coverage-regression
  evidence appears

Other open work not currently selected:
- `260614-backend-lifecycle-cross-process-identity` parked: cross-process identity deferred (backend management is aspirational)
- `260614-shell-owned-backend-lifecycle` parked: shell-owned backend QoL design resolved and parked
- `260615-runtime-package-growth-boundary-audit` runtime module/domain boundary
  audit, not a speculative package redesign
- `260615-legacy-surface-retirement-inventory` closed inventory slice for
  transitional compatibility surfaces versus fidelity-lowering adapters
- `260620-retire-host-session-path-env-coupling` closed host/session
  env-coupling retirement slice
- `566` closed: `search_block` near-match mismatch diagnostics now use a short
  safety-fuse budget and heuristic best-so-far fallback instead of exhaustive
  scanning
- `260621-read-file-optional-line-numbering` active follow-up for opt-in
  numbered `read_file` projections alongside the existing line-window surface
- `260621-search-block-first-line-indent-diff-fidelity` follow-up for
  whitespace-faithful mismatch diff rendering in `replace_block` diagnostics
- `260621-staged-replay-healing-indent-only-mismatches` closed with compact
  `/heal` replay for full-block indentation-only mismatches
- `260622-staged-replay-trailing-edge-newline-healing` inception follow-up for
  cases where CRLF/LF or trailing-newline differences may suppress otherwise
  valid indent-only `/heal` staging
- `260622-tool-write-newline-policy-and-windows-lf-defaults` inception
  follow-up for Windows tool-created content picking up CRLF and causing mixed
  endings in otherwise LF-oriented repos
- `260621-assistant-callable-plan-coalescing` inception follow-up for
  user-invoked projection of adjacent single-call YAML as one callable plan
- `260621-yaml-block-indent-salvage` inception follow-up for user-invoked,
  non-executing repair projection of structurally under-indented YAML blocks
- `260621-enable-shell-globbing` closed: user-shell globbing recovery landed;
  assistant plain `shell` vs `shell_script` semantics remain an explicit split
- `260621-windows-shell-launcher-and-path-resolution` active: remove
  non-TTY-hostile Windows `bash -ic` usage and make shell-launched command
  resolution track the selected MSYS/Git-Bash toolchain
- `260614-retire-local-suffix-naming-inversion` closed naming cleanup for the
  `_local` suffix inversion that motivated the workboard follow-up
- `260614-vim-test-cost-audit` Vim test-cost audit
- `349` JSON callable lane separation arc
- `365` transcript LCP checkpoint optimization for modifier resolution
- `415` weak-model-safe `apply_patch` contract exploration
- `463` session identity orchestration and buffer mapping
- `464` cross-repo intent routing and projection scope
- `488` multi-operator orchestration exploration
- `490` alternative operator frontends
- `513` `apply_patch` Windows/CRLF matching instrumentation and hardening
- `557` exploratory work representation model and flexible task schema
- `558` auto-inferred task dependencies from code changes
- `559` workboard as control surface
- `560` attention-focused workboard layout
- `660` shell lane spawn-semantics unification follow-up
- `676` transport-equivalence certification and shared-adapter follow-up

Closed and historical items remain below for context and auditability.

Recently stabilized (kept short; details live in task history):
- `260615-retire-dead-modules-and-shims` closed: retired unused reconcile.py module, and runtime_edges.py / step_frontier.py shims.
- `260615-relocate-reconciliation-lcp-logic` closed: relocated LCP calculations (_lcp, _eq, _normalize_bind_index, _normalize_anchor_index) from step.py facade to transcript.py.
- `260615-force-structure-alignment-survey` closed: completed the repository-wide force alignment survey, inventorying naming, ownership, adapter/domain, legacy debt, documentation fiction, and package placement pressures.
- `260614-activity-live-durable-boundary` closed: classified live async run
  state, in-memory replay, durable terminal facts, transport cursors, and host
  attachment records; runtime guidance now states that watch/subscribe replay
  is live reconnect behavior, not crash-surviving stream replay.
- `260614-backend-lifecycle-identity-stale-config` closed: implemented managed-local backend configuration fingerprinting and stale/restart-required status checks.
- `260614-effective-policy-authority-resolver` closed: consolidated policy, authority, and config-precedence resolution under a unified PolicyResolver boundary in runtime/policy.py.
- `260614-retire-stale-test-expectations` closed: the remaining collected
  unconditional skip and stale non-strict xfail were retired after confirming
  the Vim viability precursor is historical and the frontier-boundary xfail no
  longer serves as a clean diagnostic gate.
- `400` module decomposition follow-through closed: original god-module-adjacent
  targets (`tools.py`, `step.py`, `cli.py`, `daemon.py`) received staged
  extraction/compatibility cleanup slices, tests now target focused boundaries,
  and the final CLI facade sweep removed stale compatibility helpers instead of
  preserving them as covered dead surface.
- `374` coverage-led refactor pass closed: coverage gaps served as testability
  and smell evidence across runtime/tool/CLI surfaces, targeted coverage tooling
  landed, the final full-suite report reached 100% coverage, and the default
  pytest coverage gate now requires both `--cov-fail-under=100` and
  `--cov-max-missing-files=0`.
- `260614-toas-architecture-masterplan-draft` closed: broad architecture review, role-template extraction, runtime direction/ownership promotion, and backend-lifecycle implementation split are complete; future slices should update architecture only when new implementation evidence lands.
- `260614-runtime-owned-backend-lifecycle-architecture` closed: `ModelBackendLifecycle` now owns the runtime managed-local backend command core, daemon/backend RPC and stdio host paths delegate through adapters, local `TOAS_RPC_MODE=off toas backend ...` works for that contract, and domain/adapter tests are retargeted around runtime code ownership.
- `548` stdlib logging migration closed: diagnostics now use `DiagnosticsPolicy`, `configure_logging`, and module-level stdlib loggers across daemon request dispatch, session host, async store, LLM streaming, and frontier debug paths; ad hoc debug env/file channels were retired.
- `379` coverage noise burndown first pass closed: the near-complete-module
  burndown achieved its purpose, gates were raised, and later architecture-era
  coverage gaps are now treated as `400` decomposition signals or `374`
  evidence needs rather than unfinished burndown scope.
- `510` fenced import blocks closed: direct file reads, high-confidence shell file output, and search/file excerpts now project as inert metadata-bearing fences with inferred language/path/source and deterministic `block_id` values; generated/proposed content is deferred until a concrete producer appears.
- `675` architecture intent doc refresh closed: contributor-facing guidance now points to `docs/runtime-ownership.md`, with legacy facade/module boundaries called out explicitly for future runtime and tool decomposition work.
- `680` test-cost profiling and millisecond boundary remediation closed: repeatable timing workflow, slow-test classification, and fast shell-routing fixture landed; remaining slow cases are documented as contract-valid.
- `466` config sequencing/precedence contract and diagnostics clarity closed: formalized contract for config precedence classes and timing, updated `/help config` and `/config show --sources` with precedence legends, and added handler regression tests.
- `354` selected-head projection lineage boundary diagnostics closed: completed audit of `/prompt` raw-injected consequence execution to verify that no loop duplication or repeated turn behavior occurs, with lineage safety and parentage boundaries confirmed across previous sibling parentage fixes.
- `681` task naming scheme closed: new tasks should use `YYMMDD-short-intent.md`, with continuity fields (`Filed as:`, `FKA:`, `AKA:`, `Legacy index:`) documented in `tasks/README.md` and seeded in `tasks/task-template.md`.
- `677` task thread capture and routing complete: synchronous, deterministic local capture tool (`capture_task_thread`) with pluggable `TaskTrackerAdapter` and regex-based `LocalMarkdownAdapter` for node/standalone/blocker routing and context-aligned history logging.
- `328` shell execution unification umbrella complete
- `336`-`340` runtime/QoL hardening set complete
- `374` baseline coverage-led refactor umbrella closed after major slices landed
- `462` intent lane durability/query surfaces complete: storage/query, `/intent` command family, `toas intents` CLI mirror, observability/projection integration, and docs stitching are landed
- `469` harvested historical control-lane arbitration fixes from spike branch and re-centered them into current runtime semantics
- `474` bootstrap session seed + shared `/help tools` guidance source landed and closed
- `471` prompt/template tool-guidance inclusion controls landed (core/repo-work/first-edit-pass/full subsets, config defaults, bootstrap constraint application)
- `475` expanded edit-mode guidance landed with explicit `intent` inclusion and indentation-safe replacement rules (`|N`, `search_indent`)
- `476` inert wrapping policy landed at projection boundary with risky-line detection and idempotent inert wrapping
- `477` default transcript-path landing completed: runtime now defaults to `.toas/session.md` with compatibility migration behavior retained
- `478` weak-model search guidance policy landed: default guidance now prefers first-pass `$ rg` and keeps `search` for structured-use follow-ons
- `679` new-log root sentinel storage contract closed: fresh durable logs now reserve `n0` as virtual root and start authored messages at `n1`.
- `465` transcript control lane landed end-to-end: parser/frontier/projection behavior plus inert-in-control coverage and docs clarification
- `479` stdin/one-shot control step-input path landed: `toas step --stdin` and `toas step --control` now support one-step control/transcript injection with durable parity
- `480` `/prompt` projection semantics fix landed: leaf render output is inert by default; non-leaf prompt listings remain active/selectable
- `481` acceptance backend mode pytest surface landed: explicit `pytest` options now override env/defaults for replay/live/hybrid selection and related live-capture cutoff knobs
- `482` file-backed capability prompt template migration landed: dynamic capability prompt prose is now file-backed under `src/toas/prompts/dynamic/capabilities/*` with runtime interpolation retained in code
- `485` shell-lane purpose unification closed: shared live stream/watch contract now validated across user-intent and callable lanes, with intentional policy divergence explicitly tested and documented
- `489` daemon self-shell elimination via operator API closed: daemon async consequence path now executes in-process via operator API (no TOAS self-shell subprocess hop), with warm lane retired and parity tests retained
- `491` daemon async-runner warm-artifact retirement closed: removed obsolete `daemon/async_runner_warm.py` and revalidated daemon async/full-suite parity
- `498` step runtime frontier consequence split second pass closed: `_execute_frontier_consequences` now delegates user/control, plan, assistant-non-plan, and residual return/projection checks through focused helpers with direct seam tests and full-suite parity.
- `499` cli session step-local dependency-surface split closed: `run_step_local` now delegates transcript/context/config/kwargs/persistence-output phases through focused helpers with caller parity retained and full-suite validation.
- `502` replay runtime queue-until-boundary second pass closed: queue plan-state validation, skip/cancel transitions, and boundary outcome/render seams were extracted into focused helpers with targeted/full-suite parity.
- `503` daemon run-store watch async-step phase split closed: watch request parsing, follow wait loop, poll/follow snapshot capture, and response shaping now delegate cohesive helpers with parity tests.
- `500` runtime prompt/workspace intent+lens decomposition second pass closed: `_handle_intent`/`_handle_lens` now delegate focused helper seams (including lens remove/reset branch extraction) with targeted parity validation.
- `501` shell streaming run-subprocess phase split and coverage hardening closed: `run_streaming_subprocess` is now phase-decomposed into process/reader/wait/drain/assembly seams with preserved streaming semantics and targeted/full-suite parity validation.
- `512` durable capability grants closed: `/shell` grant mutations now persist as graph-real scope records with explicit `--scope` targeting and layered precedence resolution.
- `514` operational vs conversational boundary closed: shell authorization state is now operationally authoritative (not transcript-derived), with boundary note captured in `docs/notes/2026-05-15-operational-state-vs-conversational-projection.md`.
- `670` durable shell grant execution parity closed: event-backed `/shell` grants now thread into assistant callable shell policy without reviving transcript-derived authorization, with regression coverage for durable grants and same-turn inertness.
- `667` event graph CLI and operator entry points closed: `toas graph` and `/graph` now expose temporal/consequence durable-forest rendering with explicit projection parsing, deterministic message labels, and focused CLI/operator coverage.
- `260624-large-event-graph-render-performance` closed: large-log graph inspection now uses indexed renderer lookups, duplicate-id hardening, bounded full-render refusal, and cached `toas heads` stats.
- `260624-message-timestamps-and-toas-provenance` closed: newly materialized message events now carry UTC epoch-second timestamps, and sparse `toas_provenance` writer-boundary records capture schema/writer/git context when available.
- `260624-graph-provenance-coverage-gap-closure` closed: direct tests now
  cover git SHA helper success/fallback behavior and lineage-stat provenance
  fallback cases, removing the last small coverage miss in this area.
- `260624-backend-policy-max-tokens-compatibility` closed: prompt-policy
  callers can omit `max_tokens` again, with focused regression coverage for the
  compatibility path and dynamic prompt listing branch.
- `260624-cli-message-timestamp-assertion-cleanup` closed: stale CLI
  durability assertions from the graph/provenance slice now compare parsed
  event structure while still checking that modern message timestamps are valid
  integer metadata.
- `534` local-first async default policy and cutover controls closed: async operator behavior defaults to local-first for CLI sessions, tested and integrated via `540` and `551`.
- `497` shell-ops subprocess boundary split and stream-policy normalization closed: subprocess setup, read loop, and policy shaping decomposed from `run_subprocess` into `run_streaming_subprocess` in `shell_streaming.py`, with Windows-safe blocking-read fallback implemented and verified.
- `569` frontier empty transcript block normalization closed: empty synthetic result-prefix emission is gone, result lane semantics now derive from stamped transient provenance in mixed-intent consequence paths, and control-originated slash-command results now remain in the control lane by default.
- `672` producer-side transient result-node provenance normalization closed: active transient result producers now construct provenance-complete result nodes through shared helpers, downstream repair is gone, and renderer fallback for unstamped results has been removed.
- `674` runtime result-node helper extraction closed: result-node construction/validation/lane semantics now live in `runtime.result_nodes`, active callers use the runtime-owned boundary, and focused helper coverage landed.
- `673` Vim reasoning stream-policy and rendering contract closed: local-host reasoning lane rendering preserves stream policy across subscribe-window rollover without falling back to text-shape guesswork.
- `669` runtime transport parity and shared subscribe core closed: shared subscribe-read semantics are explicit, routed daemon subscribe no longer blocks parity, legacy watch `chunk` behavior is bounded, and fuller transport-equivalence certification is split to `676` if later justified.
- `666` runtime env decoupling and explicit flag threading closed: in-process async stream controls now thread explicit stdout/thinking/prompt-progress/LLM-stream/debug policy through operator/CLI/generation seams, worker-level stream env mutation is removed, and duplicate `GenerationRunner` class consolidated from `cli_session_commands.py`.
- `486` runbook vs acceptance boundary cleanup closed: acceptance proof artifacts and operator runbook/probing ownership are now explicitly separated across docs/tasks
- `483` command stdout streaming to Vim plugin debug/fix closed: daemon/watch protocol and Vim integration now surface incremental stdout with poll/follow semantics and integration coverage
- `469` functional acceptance epic closed: complete-change-request acceptance scenario is executable and passing (`tests/acceptance/steps/test_complete_change_request_steps.py`), with interruption/recovery and durable-surface checks captured
- `470` operator API seam and CLI-thin migration closed: operator-api seams now cover `step` and major session/query/analysis local surfaces, with CLI local handlers reduced to thin output wrappers and seam parity validated
- 470 follow-on under `400`/`525` closed as `260614-daemon-free-host-local-command-surface`: stdio host request handling now uses a narrow daemon-free local command surface instead of the broad `toas.cli` facade.
- `515` protocol envelope v0 and event durability map closed: envelope v0 semantics, event durability classification, and production-path classification wiring are landed
- `517` transport abstraction closed: stdio-first framed carrier, watch/daemon adapter boundary, and envelope-first watch consumer migration landed with compatibility parity retained
- `518` envelope adoption beyond watch closed: async `step_async`/`cancel` lifecycle responses and CLI status consumption now support envelope-first compatibility with legacy parity
- `519` envelope adoption for daemon status/backend lifecycle closed: `status` and `backend_status` now include envelope-compatible payloads with legacy parity retained
- `520` backend lifecycle mutation response adoption closed: `backend_start`/`backend_stop`/`backend_restart` now include envelope-compatible payloads with legacy parity retained
- `521` error-response normalization slice closed: protocol-level `ok=false/error` contract retained while envelope-first lifecycle status extraction remains compatibility-safe
- `522` CLI runtime consumer adoption closed: backend lifecycle command rendering now prefers envelope payload status/detail with legacy fallback
- `523` daemon dispatch contract docs/tests closed: dual-shape response expectations documented and reinforced by dispatch-adjacent tests
- `524` RPC client-facing schema surface closed: compatibility expectations documented and rpc protocol tests assert extra envelope field tolerance in payload objects
- `525` post-envelope runtime ownership and primary-path de-daemonization closed: primary `step`/`step --async`/`watch`/`cancel` surfaces have runtime/local ownership checks or explicit opt-back exceptions, stdio host request handling stays daemon-free, and the later backend lifecycle ownership follow-up has also closed.
- `529` acceptance marker contract and slow non-acceptance audit closed: acceptance suite now has marker-bound lane separation and slow non-acceptance hotspots are explicitly inventoried
- `526` primary-path RPC dependency inventory and exception governance closed: CLI/Vim dependency matrix, RPC-only exception qualification/schema, and follow-on mapping were completed and validated against current code paths
- `530` step-async/watch/cancel shared terminality policy seam closed: terminality policy and finalization seams were unified across watch/cancel interleavings with exactly-once terminal event/record checks and full-suite parity retained
- `531` primary-surface ownership compliance and RPC-exception governance seam closed: compliance matrix/test anchors, backend-mode selection seam, and switchable strict local cutover guard are now in place; first real local async execution path is tracked as follow-on `532`
- `532` local async execution path implementation closed: local backend lifecycle paths for `step --async`/`watch`/`cancel` are now wired behind backend-mode seam with strict cutover guard and default RPC compatibility preserved
- `533` local async lifecycle functional/system assertions closed: CLI-level local mode lifecycle contract and daemon runtime start/cancel/watch terminality integration assertions are now in place with full-suite parity
- `537` local-first cancellation/interruption hardening closed: acceptance now includes explicit local-first async cancel contract (`@local_first_async_cancel`) validating bounded timeout escalation to terminal cancellation with full-suite parity retained
- `540` async local-first default flip and mode diagnostics closed: async primary surfaces now default to local backend selection with explicit backend-mode CLI diagnostics and override-compatibility tests retained
- `544` session host serve and parent-coupled lifecycle closed: spawned `toas host serve`/`toas host stop` surfaces, owner-watchdog lifecycle seam, owner-coupled attach recovery, and teardown/recovery test coverage are now landed
- `545` editor-owned session host exclusivity and shell refusal UX closed: owner identity metadata (`owner_kind`/`owner_id`) now governs attach/reuse and shell refusal, Vim now exports editor owner identity and performs owner-matched host cleanup on `VimLeavePre`, and host stop identity filters are test-backed and documented
- `551` local-host push-forwarding flush + Vim transport default cutover closed: host stdio subscribe now forwards push frames incrementally (no post-hoc burst buffering), and Vim default transport is now `local_host` with explicit RPC opt-back retained
- `542` Vim primary-surface local/RPC parity matrix closed: parity ledger and migration breadcrumb surface preserved as historical record after local-host default cutover
- `552` Vim stdio contract phase slice closed: callback/push and marked-region contract findings preserved as contributing rationale artifact under architecture-shift narrative cleanup
- `535` runtime-owned async activity store extraction closed: runtime store/API seams now own local async lifecycle symbol consumption across CLI/daemon runner/facade surfaces, with daemon compatibility retained via adapter-backed imports and full-suite parity
- `536` daemon-to-transport adapter demotion closed: daemon async surfaces now consume runtime async activity store APIs as adapter-first boundaries, with explicit runtime-vs-backing contract tests and compatibility parity retained
- recurring maintenance lanes normalized from umbrella-task shape:
  - `487` operator spike cadence and scorecard -> `tasks/recurring/templates/operator-spike-cadence-scorecard.md`
  - `511` operational sharp-edges log maintenance -> `tasks/recurring/templates/operational-sharp-edges-log-maintenance.md`
  - `505` function-intent test audit -> `tasks/recurring/templates/function-intent-test-audit.md`
  - `504` coverage missing-files ratchet -> `tasks/recurring/templates/coverage-missing-files-ratchet.md`
  - `345` + `516` docs governance -> `tasks/recurring/templates/docs-truth-and-surface-governance.md`
  - `260627-release-process-and-weekly-release-lane` release review ->
    `tasks/recurring/templates/release-review-weekly-tagged-lane.md`
## Next

Near-term sequencing intent:
1. use `260614-architecture-follow-through-coordination` to track architecture
   follow-through subtasks without reopening the closed masterplan as a live
   planning document
2. reconcile architecture documents when implementation evidence changes a
   decision, especially where the masterplan still describes already-landed
   backend lifecycle work as pending
3. open focused decomposition or coverage-regression tasks from concrete
   runtime-ownership/domain evidence; keep closed `400`, `374`, and `379` as
   historical context rather than active umbrellas
4. use the closed masterplan plus `docs/runtime-direction.md` / `docs/runtime-ownership.md` as guidance for new runtime slices; update architecture only when implementation evidence changes a decision
5. prioritize future boundary cleanup only where implementation evidence,
   coverage, and code survey agree; avoid reopening broad catch-all umbrellas
6. keep backend lifecycle follow-up work focused on evidence-backed gaps such as workspace/config keying, lifecycle record semantics, or cross-process persistence rather than reopening the ownership decision
7. keep closed migration-era artifacts (`542`, `552`, `553`) concise and historically accurate without reopening implementation scope
8. treat orchestration/multiplayer exploration as explicit follow-on (`488`) rather than hidden `469` scope
9. run acceptance/repro loops against landed guidance controls and open focused follow-ons only when drift evidence demands them
10. execute recurring maintenance runs via templates under `tasks/recurring/templates/` rather than reopening umbrella tasks
11. the `663` transport guardrail notes remain closed context for the earlier transport-contract cleanup lane; use them as historical boundary references rather than reopening that lane

## Open Arcs

### A. Acceptance-Proven Operator Completion

Why this arc exists:
- TOAS must prove durable, interruption-tolerant completion of real repo change requests.

Current state:
- foundation closed under `469` with `470` as supporting architecture alignment; follow-on orchestration exploration is parked under `488`.

Target outcome:
- reproducible end-to-end acceptance path from intake to validated commit with coherent durable history.

### B. Maintainable Runtime Decomposition

Why this arc exists:
- long-term operability requires reducing branch density and improving seam-testability in core runtime modules.

Current state:
- umbrellas `400`, `374`, and `379` are closed historical context. The repo now
  has 100% full-suite coverage and focused decomposition boundaries across the
  original module targets; future slices should be opened from concrete domain,
  failure, or regression evidence.

Target outcome:
- thinner facades, focused helper ownership, and stable coverage-backed behavior.

### C. Weak-Model Protocol Reliability

Why this arc exists:
- weaker models still drift on callable/shape behavior without stronger first-class guidance.

Current state:
- `471` is closed with landed guidance controls; `415` remains parked for patch-path safety, and `349` stays parked until a JSON callable lane is deliberately reprioritized.

Target outcome:
- prompt/template composition can include deterministic tool guidance slices without manual operator coaching.

### D. Transcript/Control/Config Contract Clarity

Why this now also matters:
- precedence expectations should be explicit and least-surprise across subsystems; see docs/notes/2026-05-09-config-precedence-principles.md

Why this arc exists:
- operator confidence depends on explicit, predictable sequencing and projection boundaries.

Current state:
- `465`, `549`, and `466` are closed; configuration precedence contract, timings, and `/config` command output improvements are completed, with adjacent parentage hardening from `354` completed.

Target outcome:
- explicit, documented semantics with matching diagnostics and tests.

### G. Imported Content Block Identity And Provenance

Why this arc exists:
- transcript-projected payloads need deterministic fenced structure, potency, and metadata so they do not accidentally become executable intent and can support future reload/diff/writeback tooling.

Current state:
- targeted fixes already landed for inert examples, risky result wrapping, prompt leaf inertness, and Vim result marker clarity (`443`, `476`, `480`, `556`).
- imported-content rendering has a first robust contract for file reads, search excerpts, and high-confidence shell file output (`510`).
- the broader "fences around outputs" investigation (260608-fenced-output-projection-contract / 678) has been completed and closed.

Target outcome:
- projected output classes have explicit boundary/provenance/potency policy.
- imported blocks are language-tagged, path/provenance annotated, fence-safe, and identity-ready as a focused slice of that policy.

### H. Primary-Path Runtime Ownership and De-Daemonization

Why this arc exists:
- envelope adoption landed, but primary execution behavior still needs explicit ownership-first/runtime-lifecycle direction.

Current state:
- master umbrella `525` is closed after primary-path ownership audit and implementation follow-through.
- `step`/`step --async`/`watch`/`cancel` have runtime/local ownership checks or explicit opt-back exceptions.
- stdio host request handling now builds on a daemon-free local command surface.
- backend lifecycle is no longer a daemon/RPC-owned exception: `ModelBackendLifecycle` owns the runtime core, while daemon RPC, local CLI, and stdio host surfaces act as adapters.
- `660` remains intentionally deferred, and any optional stronger transport-equivalence push is tracked separately in `676`.

Target outcome:
- `step`/`step --async`/`watch`/`cancel` are ownership-first primary paths, cancellation is bounded/terminal, and Vim streaming surfaces remain stable during migration.

### E. Recurring Maintenance Discipline

Why this arc exists:
- planning and help surfaces regress when maintenance is ad hoc.

Current state:
- recurring surface audit exists; recurring roadmap hygiene process now exists and has first run recorded.

Target outcome:
- lightweight recurring runs that catch drift early and spawn focused remediation tasks.
