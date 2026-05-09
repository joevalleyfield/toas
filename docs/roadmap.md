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
- `400` module decomposition follow-through (remaining high branch-density hotspots)
- `469` functional acceptance epic (complete change request end-to-end)
- `470` operator API seam and CLI-thin migration for acceptance/e2e reliability
- `462` intent lane durability/query follow-through (remaining slices: CLI mirror, observability integration, docs stitching)
- `466` config sequencing/precedence contract and diagnostics clarity
- `415` weak-model-safe `apply_patch` contract exploration
- `417` plugin soft-failure warning-channel follow-up

Recently stabilized (kept short; details live in task history):
- `328` shell execution unification umbrella complete
- `336`-`340` runtime/QoL hardening set complete
- `374` baseline coverage-led refactor umbrella established with major slices landed
- `462` core durable intent lane landed (storage/query + `/intent` command family); follow-through slices remain open
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
- `483` command stdout streaming to Vim plugin debug/fix closed: daemon/watch protocol and Vim integration now surface incremental stdout with poll/follow semantics and integration coverage

## Next

Near-term sequencing intent:
1. continue `469`/`470` in lockstep so acceptance scenarios validate operator-equivalent surfaces
2. run acceptance/repro loops against landed guidance controls and open focused follow-ons only when drift evidence demands them
3. continue `400` decomposition queue in bounded slices with coverage guardrails
4. resolve `466` contract clarity work to reduce config ambiguity
5. re-open targeted runtime hardening follow-ons only when acceptance evidence demands them
6. close remaining `462` slices (CLI mirror, observability integration, docs stitching) or split explicit follow-on task(s)

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

### E. Recurring Maintenance Discipline

Why this arc exists:
- planning and help surfaces regress when maintenance is ad hoc.

Current state:
- recurring surface audit exists; recurring roadmap hygiene process now exists and has first run recorded.

Target outcome:
- lightweight recurring runs that catch drift early and spawn focused remediation tasks.
