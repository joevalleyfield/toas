# TOAS Roadmap

## Purpose

This roadmap is forward-looking planning, not a full implementation ledger.

Use it to answer:
- what is active now
- what should land next
- what open arcs exist

Current capability shape belongs in `docs/capabilities.md`.

## Now

Active open tasks/arcs:
- `400` module decomposition follow-through (next slices queued from rerank: `506`, `507`, `508`)
- `470` operator API seam and CLI-thin migration for acceptance/e2e reliability
- `490` alternative operator frontends (VSCode / Zed / Antigravity / Web)
- `487` operator spike cadence and scorecard
- `488` multi-operator orchestration exploration
- `466` config sequencing/precedence contract and diagnostics clarity
- `415` weak-model-safe `apply_patch` contract exploration
- `417` plugin soft-failure warning-channel follow-up
- `510` fenced import blocks (language/path/provenance/fence safety)
- `511` operational sharp-edges and empirical-failure log
- `513` `apply_patch` Windows/CRLF matching instrumentation/hardening
- `504` coverage missing-files ratchet gate
  - current working cap is temporarily set to `20` (from `17`) after recent Windows compatibility fixes; continue targeted burndown before next ratchet
- `505` function-intent test audit (behavioral confidence over line execution)
- `506` graph decomposition in progress: index seams previously extracted; current slice is extracting message/lineage projection helpers behind stable `graph.py` wrappers

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

## Next

Near-term sequencing intent:
1. `509` completed and validated cross-platform (including Windows); maintain soak observations while proceeding with next daemon/runtime slices
2. continue runbook/probe process evolution under `487` without reopening acceptance-closure scope
3. treat orchestration/multiplayer exploration as explicit follow-on (`488`) rather than hidden `469` scope
4. run acceptance/repro loops against landed guidance controls and open focused follow-ons only when drift evidence demands them
5. continue `470` seam migration only where `400` slices expose API-boundary friction
6. resolve `466` contract clarity work to reduce config ambiguity
7. re-open targeted runtime hardening follow-ons only when acceptance evidence demands them
8. open follow-on intent-lane enhancements only when new operator/acceptance evidence demands them

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

### E. Recurring Maintenance Discipline

Why this arc exists:
- planning and help surfaces regress when maintenance is ad hoc.

Current state:
- recurring surface audit exists; recurring roadmap hygiene process now exists and has first run recorded.

Target outcome:
- lightweight recurring runs that catch drift early and spawn focused remediation tasks.
