# TOAS Roadmap

## Purpose

This roadmap is forward-looking planning, not a full implementation ledger.

Use it to answer:
- what is active now
- what should land next
- what open arcs exist

Roadmap size cap:
- keep this file under 250 lines
- keep `## Now` at 12 bullets or fewer
- keep `## Now` to open or actively selected work only
- move closed implementation detail to task history, release notes, or concise
  historical context sections instead of preserving it inline here

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
- segmented-storage proof remains the immediate implementation lane:
  `260627-segmented-event-index-and-lookup-hardening` ->
  `260627-split-storage-rebuild-and-projection-parity`.
- after that proof chain, the next highest-leverage operator lane is
  `260627-history-recovery-tooling` plus
  `260627-history-surface-user-intent-alignment`.
- `260627-history-surface-corruption-semantics` and
  `260627-fail-closed-history-query-hardening` remain open, but should now be
  read against the stronger baseline that normal history-facing surfaces
  already fail closed on fatal durable-history corruption.
- `260626-events-jsonl-multiplicity-and-merge-provenance`,
  `260626-transcript-parallelism-design-pressures`, and
  `260627-history-affordances-semantic-restaging` remain warm framing tasks,
  but they are not the next build targets.
- the next bounded history-surface implementation slices are
  `260628-graph-local-neighborhood-selector` and
  `260628-history-preview-heuristic-selection`.
- `260628-transcript-writeback-surface-unification` is now closed: the
  standalone `toas rebuild` command (and the operator `rebuild_session`) has
  been removed. Transcript projection is the single transcript-shaped surface;
  resume-from-lineage is `toas transcript <head_id> > <session_path>`.
  `260628-llm-input-envelope-visibility` is now closed: `toas llm-input
  --envelope` exposes the packet/system shaping above the core projection.
- `260627-release-process-and-weekly-release-lane` is the active governance
  lane and was first exercised on 2026-06-28 for candidate `0.0.0.0`;
  `260627-release-helper-tooling` is the bounded follow-on if release review
  overhead becomes annoying enough to automate.
- acceptance-suite test-infra cluster (opened 260628, after
  `260628-acceptance-suite-revival` brought the suite back to green):
  live-prompt realism spike (`260628-acceptance-live-prompt-realism`), per-step
  hybrid generation (`260628-acceptance-per-step-hybrid-generation`), and live
  generation bounds (`260628-acceptance-live-generation-bounds`). These are
  test-harness quality lanes, below the segmented-storage and history-surface
  priorities.
- `260628-project-checks-and-ci-posture` is closed and defines TOAS's everyday
  check/verification posture in `docs/checks.md`: local `scripts/check.sh`
  spine, gated default pytest/replay acceptance, advisory `ruff`/`mypy` tracked
  by `260628-lint-type-routine-gate-cleanup`, and no hosted CI yet. It is
  distinct from the `260627-release-process-and-weekly-release-lane` governance
  lane, whose release gate now references the routine check set.
- `260621-windows-shell-launcher-and-path-resolution` remains an active
  implementation lane, but is below the current segmented-storage and
  history-surface priorities.
- no broad decomposition/coverage umbrella is currently active; open focused
  implementation tasks only when concrete domain, failure, or
  coverage-regression evidence appears.

Other parked open follow-ons:
- the roadmap names only a small set of parked open follow-ons here; the
  broader open task inventory and day-to-day queue live in `tasks/WORKBOARD.md`.
- `260614-backend-lifecycle-cross-process-identity` parked: cross-process identity deferred (backend management is aspirational)
- `260614-shell-owned-backend-lifecycle` parked: shell-owned backend QoL design resolved and parked
- `260615-runtime-package-growth-boundary-audit` runtime module/domain boundary
  audit, not a speculative package redesign
- `260621-read-file-optional-line-numbering` active follow-up for opt-in
  numbered `read_file` projections alongside the existing line-window surface
- `260621-search-block-first-line-indent-diff-fidelity` follow-up for
  whitespace-faithful mismatch diff rendering in `replace_block` diagnostics
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
- `260621-windows-shell-launcher-and-path-resolution` active: remove
  non-TTY-hostile Windows `bash -ic` usage and make shell-launched command
  resolution track the selected MSYS/Git-Bash toolchain
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

Historical summary:
- major closed arcs include runtime ownership (`525`), decomposition/coverage
  (`400`, `374`, `379`), backend-lifecycle ownership, transport/envelope
  adoption, local-first async cutover, and shell-lane hardening.
- recent closed capability slices include graph/history framing, fenced output
  contracts, config/precedence clarification, event-graph rendering, provenance,
  and acceptance-path stabilization.
- recurring maintenance lanes have been normalized into templates under
  `tasks/recurring/templates/` for docs governance, coverage ratchets, sharp
  edges, operator spikes, function-intent audits, and release review.
- use task files, task history, and release notes for closure detail rather
  than expanding this roadmap into a historical ledger.

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
- the original acceptance foundation is closed, and the remaining pressure is
  to preserve that bar while future orchestration stays explicit.

Target outcome:
- reproducible end-to-end acceptance path from intake to validated commit with coherent durable history.

### B. Maintainable Runtime Decomposition

Why this arc exists:
- long-term operability requires reducing branch density and improving seam-testability in core runtime modules.

Current state:
- the big decomposition and coverage umbrellas are closed historical context.
  The repo has strong seam coverage, so new decomposition work should only open
  from concrete domain, failure, or regression evidence.

Target outcome:
- thinner facades, focused helper ownership, and stable coverage-backed behavior.

### C. History Surface Clarity And Recovery

Why this arc exists:
- durable history is becoming a more important operator substrate, so TOAS
  needs both clear healthy-history affordances and explicit recovery lanes when
  history is corrupt.

Current state:
- segmented storage is mid-proof, fail-closed corruption handling is already a
  baseline, and the sharpest open pressure is now recovery tooling plus
  user-intent alignment across `heads`, `history`, `transcript`, `llm-input`,
  and `graph` (the standalone `rebuild` surface has since been removed in favor
  of projection-plus-redirect; see
  `260628-transcript-writeback-surface-unification`).

Target outcome:
- history-facing surfaces answer distinct operator questions clearly, and
  corrupt-history refusal points toward safe next actions instead of dead ends.

### D. Imported Content Block Identity And Provenance

Why this arc exists:
- transcript-projected payloads need deterministic fenced structure, potency,
  and metadata so they do not accidentally become executable intent and can
  support future reload/diff/writeback tooling.

Current state:
- imported-content rendering has a first robust contract for file reads,
  search excerpts, and high-confidence shell file output, while the broader
  output-boundary investigation is closed and available as historical context.

Target outcome:
- projected output classes have explicit boundary/provenance/potency policy,
  with imported blocks as a stable identity-ready slice of that policy.

### E. Primary-Path Runtime Ownership

Why this arc exists:
- primary execution paths need to stay runtime-owned and transport-adapter
  driven rather than drifting back toward daemon-shaped semantic ownership.

Current state:
- the ownership-first cutover is landed for primary paths and backend
  lifecycle. Remaining work is mostly about holding that boundary, plus any
  optional stronger transport-equivalence follow-on.

Target outcome:
- `step`/`step --async`/`watch`/`cancel` remain ownership-first primary paths,
  cancellation stays bounded/terminal, and transport choices remain adapter
  concerns rather than semantic forks.

### F. Protocol Reliability For Weaker Models

Why this arc exists:
- weaker models still drift on callable shape, edit safety, and tool-usage
  conventions unless TOAS gives them stronger deterministic guidance.

Current state:
- major guidance controls are landed, but `apply_patch` safety and any
  deliberate JSON-callable-lane work remain parked until they become the
  highest-value reliability slice again.

Target outcome:
- prompt/template composition can include deterministic tool-guidance slices
  that reduce manual coaching for weaker models.

### G. Recurring Maintenance Discipline

Why this arc exists:
- planning and help surfaces regress when maintenance is ad hoc.

Current state:
- recurring maintenance templates exist, and the roadmap/workboard now need
  continued light-touch pruning so planning surfaces stay useful.

Target outcome:
- lightweight recurring runs that catch drift early and spawn focused remediation tasks.
