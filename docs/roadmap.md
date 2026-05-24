# TOAS Roadmap

## Purpose

This roadmap is forward-looking planning, not a full implementation ledger.

Use it to answer:
- what is active now
- what should land next
- what open arcs exist

Execution policy for active runtime arcs (`525`):
- capability-first sequencing: land happy-path capability first
- add restrictions/guardrails only when backed by concrete failure evidence or cross-platform/data-integrity risk

Current capability shape belongs in `docs/capabilities.md`.
Doc intent/status guardrails (CURRENT vs DIRECTIONAL vs DRAFT) are defined in `docs/notes/2026-05-16-doc-truth-model.md`.

## Now

Active open tasks/arcs:
- `525` post-envelope runtime ownership and primary-path de-daemonization (master umbrella)
- `534` local-first async default policy and cutover controls
- `541` primary-surface RPC exception ledger and retirement plan closed: RPC compatibility-lane exceptions are inventoried with rationale, retirement hooks, and post-cutover sequencing
- `553` Vim transport architecture-shift triage and cleanup closed: architecture-shift narrative consolidation, OBE triage, roadmap hygiene, and close/reframe decisions were completed
- `554` Vim transport annotation implementation follow-on closed: Step 5 audit targets were implemented as annotation-only updates (no behavioral changes)
- `548` stdlib logging migration for runtime diagnostics (future-direction backlog follow-on)
- `549` LCP root-class relinearization hardening (prevent startup-class near-root messages from non-root parent attachment)
- `550` root sentinel taxonomy unification (`n0`) to remove null-parent exception pressure from rewrite parent selection
- `543` session-owned warm runtime lifecycle for CLI shell closed: stream-first stdio host lifecycle path now has terminal-complete subscribe semantics, resume/cursor contract notes, and structured host debug tracing
- `544` session host serve entrypoint and parent-coupled lifecycle
- `527` cancel/interruption bounded terminality for primary surfaces closed: bounded timeout escalation, deterministic terminal-event/watch convergence, Vim follow regression coverage, and post-forced-cancel run cleanliness are now validated
- `400` module decomposition follow-through (next slices queued from rerank: `497`, `496`)
- `490` alternative operator frontends (VSCode / Zed / Antigravity / Web)
- `488` multi-operator orchestration exploration
- `466` config sequencing/precedence contract and diagnostics clarity
- `415` weak-model-safe `apply_patch` contract exploration
- `417` plugin soft-failure warning-channel follow-up
- `510` fenced import blocks (language/path/provenance/fence safety)
- `513` `apply_patch` Windows/CRLF matching instrumentation/hardening
- `546` async stdio IPC todo experiment closed: isolated async stdio subprocess conversation spike completed and harvested into runtime-host follow-on slices
- `547` CLI module entrypoint bugfix closed: `python -m toas` is now canonical and `python -m toas.cli` is explicitly deterred
- `506` graph decomposition closed: index/message/control/writer seams extracted from `graph.py` into focused modules, with private-wrapper flattening pass completed and parity validation retained
- `508` daemon facade reduction third pass closed: wrapper/bootstrap clusters were extracted into focused facade modules and dispatch runtime assembly was consolidated with parity validation retained

Recently stabilized (kept short; details live in task history):
- `328` shell execution unification umbrella complete
- `336`-`340` runtime/QoL hardening set complete
- `374` baseline coverage-led refactor umbrella established with major slices landed
- `462` intent lane durability/query surfaces complete: storage/query, `/intent` command family, `toas intents` CLI mirror, observability/projection integration, and docs stitching are landed
- `469` harvested historical control-lane arbitration fixes from spike branch and re-centered them into current runtime semantics
- `474` bootstrap session seed + shared `/help tools` guidance source landed and closed
- `471` prompt/template tool-guidance inclusion controls landed (core/repo-work/first-edit-pass/full subsets, config defaults, bootstrap constraint application)
- `475` expanded edit-mode guidance landed with explicit `intent` inclusion and indentation-safe replacement rules (`|N`, `search_indent`)
- `476` inert wrapping policy landed at projection boundary with risky-line detection and idempotent inert wrapping
- `477` default transcript-path landing completed: runtime now defaults to `.toas/session.md` with compatibility migration behavior retained
- `478` weak-model search guidance policy landed: default guidance now prefers first-pass `$ rg` and keeps `search` for structured-use follow-ons
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
- `497` shell-ops subprocess boundary split follow-up in progress: Windows-safe stream-reader behavior was added in `shell_streaming` to avoid selector/pipe-handle incompatibility (`WinError 10038`) while preserving non-Windows and test-double parity.
- `486` runbook vs acceptance boundary cleanup closed: acceptance proof artifacts and operator runbook/probing ownership are now explicitly separated across docs/tasks
- `483` command stdout streaming to Vim plugin debug/fix closed: daemon/watch protocol and Vim integration now surface incremental stdout with poll/follow semantics and integration coverage
- `469` functional acceptance epic closed: complete-change-request acceptance scenario is executable and passing (`tests/acceptance/steps/test_complete_change_request_steps.py`), with interruption/recovery and durable-surface checks captured
- `470` operator API seam and CLI-thin migration closed: operator-api seams now cover `step` and major session/query/analysis local surfaces, with CLI local handlers reduced to thin output wrappers and seam parity validated
- `515` protocol envelope v0 and event durability map closed: envelope v0 semantics, event durability classification, and production-path classification wiring are landed
- `517` transport abstraction closed: stdio-first framed carrier, watch/daemon adapter boundary, and envelope-first watch consumer migration landed with compatibility parity retained
- `518` envelope adoption beyond watch closed: async `step_async`/`cancel` lifecycle responses and CLI status consumption now support envelope-first compatibility with legacy parity
- `519` envelope adoption for daemon status/backend lifecycle closed: `status` and `backend_status` now include envelope-compatible payloads with legacy parity retained
- `520` backend lifecycle mutation response adoption closed: `backend_start`/`backend_stop`/`backend_restart` now include envelope-compatible payloads with legacy parity retained
- `521` error-response normalization slice closed: protocol-level `ok=false/error` contract retained while envelope-first lifecycle status extraction remains compatibility-safe
- `522` CLI runtime consumer adoption closed: backend lifecycle command rendering now prefers envelope payload status/detail with legacy fallback
- `523` daemon dispatch contract docs/tests closed: dual-shape response expectations documented and reinforced by dispatch-adjacent tests
- `524` RPC client-facing schema surface closed: compatibility expectations documented and rpc protocol tests assert extra envelope field tolerance in payload objects
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

## Next

Near-term sequencing intent:
1. continue `525` follow-on execution after `534`-`538` completion, prioritizing remaining ownership-first/runtime-lifecycle seams
2. execute remaining RPC compatibility-lane retirement/governance actions via newly opened focused slices as needed
4. keep closed migration-era artifacts (`542`, `552`, `553`) concise and historically accurate without reopening implementation scope
5. continue graph-projection/runtime follow-ons after `539` closure, with branch semantics now covered by deterministic regressions
6. continue IPC/runtime-host simplification from envelope-first seams with legacy parity retained
7. prioritize next high-leverage non-envelope arc (`400`/`466`/`525`) based on operator acceptance and maintainability pressure
8. treat orchestration/multiplayer exploration as explicit follow-on (`488`) rather than hidden `469` scope
9. run acceptance/repro loops against landed guidance controls and open focused follow-ons only when drift evidence demands them
10. execute recurring maintenance runs via templates under `tasks/recurring/templates/` rather than reopening umbrella tasks

## Open Arcs

### A. Acceptance-Proven Operator Completion

Why this arc exists:
- TOAS must prove durable, interruption-tolerant completion of real repo change requests.

Current state:
- foundation is open under `469` with `470` as supporting architecture alignment.

Target outcome:
- reproducible end-to-end acceptance path from intake to validated commit with coherent durable history.

### B. Maintainable Runtime Decomposition

Why this arc exists:
- long-term operability requires reducing branch density and improving seam-testability in core runtime modules.

Current state:
- umbrella `400` remains active; multiple decomposition slices have landed; remaining hotspots are queued.

Target outcome:
- thinner facades, focused helper ownership, and stable coverage-backed behavior.

### C. Weak-Model Protocol Reliability

Why this arc exists:
- weaker models still drift on callable/shape behavior without stronger first-class guidance.

Current state:
- `471` is closed with landed guidance controls; exploratory `415` remains relevant for patch-path safety.

Target outcome:
- prompt/template composition can include deterministic tool guidance slices without manual operator coaching.

### D. Transcript/Control/Config Contract Clarity

Why this now also matters:
- precedence expectations should be explicit and least-surprise across subsystems; see docs/notes/2026-05-09-config-precedence-principles.md

Why this arc exists:
- operator confidence depends on explicit, predictable sequencing and projection boundaries.

Current state:
- `465` is closed; `466` remains open for config precedence and diagnostics clarity.

Target outcome:
- explicit, documented semantics with matching diagnostics and tests.

### G. Imported Content Block Identity And Provenance

Why this arc exists:
- imported file/context content needs deterministic fenced structure and metadata for future reload/diff/writeback tooling.

Current state:
- ad hoc imported-content rendering lacks a single robust contract (`510`).

Target outcome:
- imported blocks are language-tagged, path/provenance annotated, fence-safe, and identity-ready.

### H. Primary-Path Runtime Ownership and De-Daemonization

Why this arc exists:
- envelope adoption landed, but primary execution behavior still needs explicit ownership-first/runtime-lifecycle direction.

Current state:
- new master umbrella `525` opened with first slices `526`/`527`/`528`; all three are now closed and implementation follow-through continues under `525` and `470`.

Target outcome:
- `step`/`step --async`/`watch`/`cancel` are ownership-first primary paths, cancellation is bounded/terminal, and Vim streaming surfaces remain stable during migration.

### E. Recurring Maintenance Discipline

Why this arc exists:
- planning and help surfaces regress when maintenance is ad hoc.

Current state:
- recurring surface audit exists; recurring roadmap hygiene process now exists and has first run recorded.

Target outcome:
- lightweight recurring runs that catch drift early and spawn focused remediation tasks.
