# TOAS Workboard

> **Status:** Active Development
> **Last Sync:** 2026-06-30

## 0. Manual Triage
*Hand-curated operator triage, not automated extraction.*

- `260614-architecture-follow-through-coordination` is the active coordination
  object for top-down architecture follow-through. It ties subtasks to
  `docs/architecture-masterplan.md`, `docs/runtime-direction.md`, and
  `docs/runtime-ownership.md` without replacing those documents.
- First split children `260614-effective-policy-authority-resolver` and
  `260614-backend-lifecycle-identity-stale-config` are closed.
- `260614-backend-lifecycle-cross-process-identity` now parks the unresolved
  cross-process identity gap (backend process management is aspirational).
- `260614-shell-owned-backend-lifecycle` now parks the resolved design shape
  for shell-owned backend processes and parent session-host watchdogs.
- `260619-workboard-sync-script-parser-and-identity-fix` is closed: generated
  board entries preserve full task handles, fallback summaries ignore task
  header metadata, and the sync-script follow-up is complete.
- `260615-legacy-surface-retirement-inventory` is closed: the first inventory
  slice now distinguishes transitional compatibility surfaces from
  fidelity-lowering adapters.
- `260619-session-md-compatibility-retirement` is closed: the CLI/runtime
  fallback to `session.md` has been retired.
- `260620-retire-host-session-path-env-coupling` is closed: host default
  session targeting now uses explicit host-owned state and `host_session_path`
  payload threading instead of ambient `TOAS_HOST_SESSION_PATH`.
- `260620-host-stdio-reasoning-terminality-ux` is closed: host-stdio
  substantive recovery now respects reasoning-stream visibility, command-only
  tails no longer fabricate assistant answers, and failed runs append a compact
  visible cause line instead of depending on log-file spelunking.
- `260619-daemon-package-facade-shrinkage` is closed: the remaining daemon
  package root is now a bounded compatibility/execution-entry facade with
  direct package-boundary coverage, including `toas.daemon.__main__`.
- `260626-assistant-shell-script-relative-cwd-resolution` is closed: assistant
  `shell_script` relative `cwd` values now anchor to the active step
  `command_cwd` instead of ambient process cwd.
- Current near-term queue from the June 26-27 intake is back on
  `260627-split-storage-rebuild-and-projection-parity` for the semantic
  contract gap exposed after the first graph parity implementation slice.
- `260627-segmented-event-journal-storage-contract` is closed: a first
  storage-contract note now fixes `.toas/events.jsonl` as the sole hot append
  target, keeps transcript LCP reconciliation hot-only while allowing hot
  history to be self-contained, empty, or independent after rotation, seals
  older ordered segments under `.toas/segments/`, allows gzip archival
  compaction, and makes ordinal gaps/duplicates explicit invalid layout.
- `260627-graph-segmented-read-query-hardening` is closed: graph-side logical
  history reads now stitch sealed segments plus hot storage for
  `heads`/`history`/`transcript`/`llm-input`, while LCP reconciliation remains
  hot-only.
- `260627-segmented-event-index-and-lookup-hardening` is closed: index lookup
  now uses per-source indexes stitched into logical positions, including
  sealed `.jsonl` / `.jsonl.gz` segments plus the hot file.
- `260627-split-storage-rebuild-and-projection-parity` is reopened: `graph` now
  joins `heads`, `history`, `transcript`, and `llm-input` on the current
  stitched read path, but the task now owns the correction that local message
  ids are journal-scoped and cold/hot stitching should be LCP/alignment based
  rather than global-id concatenation.
- After the segmented-storage semantic contract is actually settled, treat
  corrupt-history work as an operator recovery and affordance-alignment lane
  first:
  `260627-history-recovery-tooling` and
  `260627-history-surface-user-intent-alignment`.
- `260627-event-log-fsck-contract` is already closed, and the remaining
  corruption-related open tasks should now be read against the newer baseline
  that normal history-facing surfaces already fail closed.
- Keep `260626-events-jsonl-multiplicity-and-merge-provenance`,
  `260626-transcript-parallelism-design-pressures`, and
  `260627-history-affordances-semantic-restaging` warm as design drivers, but
  do not force them ahead of the shell fixes or the segmented-storage proof
  chain.
- `260628-heads-selected-history-leaf-framing` is closed: `heads` now teaches
  itself locally as the compact leaf-set sibling to `history` and `graph`,
  with aligned help/output framing and no semantic broadening.
- `260628-transcript-writeback-surface-unification` is closed: the standalone
  `toas rebuild` command and operator `rebuild_session` are removed; transcript
  projection is the single transcript-shaped surface, and resume-from-lineage is
  `toas transcript <head_id> > <session_path>`.
- `260628-acceptance-suite-revival` is closed: the acceptance suite (excluded
  from the default run via `-m "not acceptance"`) had bitrotted and is green
  again in `replay_only`. It spun out a follow-on cluster:
  the now-closed `260628-acceptance-live-prompt-realism` (live staged-frontier
  runs now project the configured bootstrap prompt before the tiny acceptance
  frontier),
  `260628-acceptance-per-step-hybrid-generation`,
  `260628-acceptance-live-generation-bounds`, and the now-closed
  `260628-acceptance-replay-in-routine-checks`.
- `260628-project-checks-and-ci-posture` is closed and now defines TOAS's everyday
  check/verification posture in `docs/checks.md`: local `scripts/check.sh`
  spine, gated default pytest/replay acceptance, advisory `ruff`/`mypy` tracked
  by `260628-lint-type-routine-gate-cleanup`, and no hosted CI yet. It anchors
  the release lane's check gate
  (`260627-release-process-and-weekly-release-lane`,
  `260627-release-helper-tooling`) without pretending `.github/workflows/`
  exists.
- Treat recovery and affordance-alignment follow-ons as a prerequisite for
  broader parallel-affordance or history-affordance claims on top of the new
  fail-closed baseline.
- Inception-only children now park the remaining known architecture pressures
  until they are ready for focused investigation.
- Task lists may stay linear where that reflects reality; active coordination
  work should preserve tree/graph relationships with explicit task links.
- Closed umbrellas `400`, `525`, `374`, and `379` remain historical context,
  not active work parents.
- Parked or exploratory items remain intentionally deferred unless pulled into
  the architecture coordination tree or selected as focused follow-ups: `349`,
  `365`, `415`, `463`, `464`, `488`, `490`, `513`, `557`, `558`, `559`, `560`,
  `660`, and `676`.

### Relationship Roots
*Manual root selection for the generated relationship tree.*

<!-- WORKBOARD:RELATIONSHIP_ROOTS:START -->
- `260614-architecture-follow-through-coordination`
- `260627-release-process-and-weekly-release-lane`
- `260628-lint-type-routine-gate-cleanup`
- `260628-acceptance-per-step-hybrid-generation`
- `260628-acceptance-live-generation-bounds`
<!-- WORKBOARD:RELATIONSHIP_ROOTS:END -->

### Active Arc Map
*Generated first-mention relationship tree; repeated tasks use `@task-id`.*

<!-- WORKBOARD:RELATIONSHIP_TREE:START -->
- 260614-architecture-follow-through-coordination Architecture Follow-Through Coordination
  - 260614-backend-lifecycle-cross-process-identity Backend Lifecycle Cross-Process Identity
  - 260614-legacy-and-fidelity-adapter-precedence Legacy And Fidelity-Adapter Precedence
  - 260614-model-backend-failure-handoff Model Invocation To Backend Lifecycle Failure Handoff
  - 260614-shell-owned-backend-lifecycle Shell-Owned Backend Lifecycle
  - 260614-vim-test-cost-audit Audit the vim driver test suite to determine whether the tests are as cheap as they could be given what they're actually verifying.
  - 260615-runtime-package-growth-boundary-audit Runtime Package Growth Boundary Audit
  - 260626-events-jsonl-multiplicity-and-merge-provenance Events.jsonl Multiplicity And Merge Provenance (related `260626-transcript-parallelism-design-pressures`, `260509-multi-operator-orchestration`)
    - 260627-fail-closed-history-query-hardening Fail-Closed History Query Hardening (blocked by `260627-event-log-fsck-contract`, `260627-history-surface-corruption-semantics`; related `260626-transcript-parallelism-design-pressures`, `260627-split-storage-rebuild-and-projection-parity`, `260627-segmented-event-index-and-lookup-hardening`)
    - 260627-history-recovery-tooling History Recovery Tooling (blocked by `260627-history-surface-corruption-semantics`, `260627-fail-closed-history-query-hardening`; related `260627-history-affordances-semantic-restaging`, `260626-transcript-parallelism-design-pressures`)
    - 260627-history-surface-corruption-semantics History Surface Corruption Semantics (blocked by `260627-event-log-fsck-contract`; blocks `260627-fail-closed-history-query-hardening`; related `260627-history-affordances-semantic-restaging`, `260627-split-storage-rebuild-and-projection-parity`)
    - 260627-split-storage-rebuild-and-projection-parity Split Storage Rebuild And Projection Parity (blocked by `260627-graph-segmented-read-query-hardening`, `260629-storage-scale-model-proof-contract`; related `260614-architecture-follow-through-coordination`)
    - 260629-storage-scale-model-proof-contract Storage Scale-Model Proof Contract (blocks `260627-split-storage-rebuild-and-projection-parity`; related `260627-history-surface-user-intent-alignment`, `260627-history-surface-corruption-semantics`, `260628-graph-local-neighborhood-selector`)
  - 260626-transcript-parallelism-design-pressures Transcript Parallelism Design Pressures (related `260509-multi-operator-orchestration`, `260524-exploratory-work-representation-model`)
  - 260627-history-affordances-semantic-restaging History Affordances And Semantic Restaging (related `260626-transcript-parallelism-design-pressures`, `260524-exploratory-work-representation-model`)
  - 260627-history-surface-user-intent-alignment History Surface User Intent Alignment (related `260627-history-surface-corruption-semantics`, `260627-fail-closed-history-query-hardening`, `260627-history-recovery-tooling`, `260627-history-affordances-semantic-restaging`, `260627-split-storage-rebuild-and-projection-parity`, `260628-history-root-to-head-lineage-contract`, `260628-graph-selected-history-topology-framing`, `260628-graph-local-neighborhood-selector`)
    - 260628-durable-derived-history-previews Durable Derived History Previews (related `260628-history-preview-heuristic-selection`, `260627-history-affordances-semantic-restaging`)
    - 260628-graph-local-neighborhood-selector Graph Local Neighborhood Selector (related `260628-graph-selected-history-topology-framing`)
- 260627-release-process-and-weekly-release-lane Release Process And Weekly Release Lane (related `260628-project-checks-and-ci-posture`, `260627-release-helper-tooling`)
- 260628-lint-type-routine-gate-cleanup Lint Type Routine Gate Cleanup
- 260628-acceptance-per-step-hybrid-generation Acceptance Per-Step Hybrid Generation (related `260628-acceptance-suite-revival`, `260628-acceptance-live-prompt-realism`)
- 260628-acceptance-live-generation-bounds Acceptance Live Generation Bounds (related `260628-acceptance-suite-revival`, `260628-acceptance-live-prompt-realism`)
<!-- WORKBOARD:RELATIONSHIP_TREE:END -->

- closed historical context: 400 module decomposition, 525 runtime ownership,
  374 coverage-led refactor pass, 379 coverage noise burndown

## 1. Open Queue
*Generated open-task inventory. Use Manual Triage above for active vs parked sequencing.*

<!-- WORKBOARD:NOW:START -->
- **[T260412-json-callable-lane-parser-and-policy]** Define a separate JSON-callable lane with explicit parser, extraction semantics, and policy behavior, without coupling it to the current fenced-YAML c...
- **[T260412-transcript-lcp-checkpoint-optimization]** Optimize transcript-modifier resolution (`/shell`, `/env`, related command-derived state) using LCP/checkpoint state recovery plus tail replay.
- **[T260418-weak-model-safe-apply-patch-contract]** Explore and define a weak-model-safe `apply_patch` tool contract that improves first-pass correctness and guided recovery for lower-prior models.
- **[T260428-cross-repo-intent-routing]** Define scope/routing semantics for intents that span multiple repositories/workspaces without violating local history invariants.
- **[T260428-session-identity-orchestration]** Define and implement named/multi-buffer session identity semantics (for example `.toas/session-<name>.md`) while preserving canonical `events.jsonl` a...
- **[T260509-alternative-operator-frontends]** Evaluate and stage a medium-horizon path for operator frontends beyond Vim, including VS Code, Antigravity, and/or Web surfaces.
- **[T260509-multi-operator-orchestration]** Evaluate higher-level orchestration patterns (including TOAS-in-TOAS or multi-agent collaboration) as a follow-on capability, separate from base singl...
- **[T260515-apply-patch-windows-crlf-hardening]** Investigate and harden `apply_patch` behavior on Windows/CRLF files with explicit diagnostics around newline/context matching.
- **[T260524-attention-focused-workboard-layout]** Design and implement an "Attention-Focused" layout for the Workboard that highlights high-impact tasks and suppresses noise.
- **[T260524-auto-inferred-task-dependencies]** Develop a mechanism to automatically infer task dependencies from code changes and commit history, reducing manual overhead and improving accuracy.
- **[T260524-exploratory-work-representation-model]** Define a flexible task schema that supports both "Verified Implementation" tasks and "Exploratory/Research" tasks without forcing one into the other's...
- **[T260524-workboard-as-control-surface]** Transform `WORKBOARD.md` from a passive report into an active control surface that allows the operator to influence system behavior.
- **[T260530-shell-lane-spawn-semantics]** Track and defer a focused cleanup to eliminate unintended behavior differences between assistant and user shell execution lanes by centralizing spawn ...
- **[T260602-transport-equivalence-certification]** Only if and when it becomes worthwhile, push beyond task `669`'s contract-bounding bar toward stronger transport-equivalence proof and possibly a more...
- **[T260614-architecture-follow-through-coordination]** Architecture Follow-Through Coordination
- **[T260614-backend-lifecycle-cross-process-identity]** Backend Lifecycle Cross-Process Identity
- **[T260614-legacy-and-fidelity-adapter-precedence]** Legacy And Fidelity-Adapter Precedence
- **[T260614-model-backend-failure-handoff]** Model Invocation To Backend Lifecycle Failure Handoff
- **[T260614-shell-owned-backend-lifecycle]** Shell-Owned Backend Lifecycle
- **[T260614-vim-test-cost-audit]** Audit the vim driver test suite to determine whether the tests are as cheap as they could be given what they're actually verifying.
- **[T260615-runtime-package-growth-boundary-audit]** Runtime Package Growth Boundary Audit
- **[T260621-assistant-callable-plan-coalescing]** Assistant Callable Plan Coalescing
- **[T260621-compact-search-output]** Refactor the `search` tool output to be significantly more token-efficient and cognitively clear.
- **[T260621-eval-command-output-formatting]** Audit existing tool/command outputs for verbosity and token bloat. Establish a unified "compact output" pattern similar to the proposed `search` forma...
- **[T260621-windows-shell-launcher-and-path-resolution]** Windows Shell Launcher And Path Resolution
- **[T260621-yaml-block-indent-salvage]** YAML Block Indent Salvage
- **[T260622-staged-replay-trailing-edge-newline-healing]** Staged Replay Trailing-Edge Newline Healing
- **[T260622-tool-write-newline-policy-and-windows-lf-defaults]** Tool Write Newline Policy And Windows LF Defaults
- **[T260626-events-jsonl-multiplicity-and-merge-provenance]** Events.jsonl Multiplicity And Merge Provenance
- **[T260626-transcript-parallelism-design-pressures]** Transcript Parallelism Design Pressures
- **[T260627-fail-closed-history-query-hardening]** Fail-Closed History Query Hardening
- **[T260627-history-affordances-semantic-restaging]** History Affordances And Semantic Restaging
- **[T260627-history-recovery-tooling]** History Recovery Tooling
- **[T260627-history-surface-corruption-semantics]** History Surface Corruption Semantics
- **[T260627-history-surface-user-intent-alignment]** History Surface User Intent Alignment
- **[T260627-release-helper-tooling]** Release Helper Tooling
- **[T260627-release-process-and-weekly-release-lane]** Release Process And Weekly Release Lane
- **[T260627-split-storage-rebuild-and-projection-parity]** Split Storage Rebuild And Projection Parity
- **[T260628-acceptance-live-generation-bounds]** Acceptance Live Generation Bounds
- **[T260628-acceptance-per-step-hybrid-generation]** Acceptance Per-Step Hybrid Generation
- **[T260628-durable-derived-history-previews]** Durable Derived History Previews
- **[T260628-graph-local-neighborhood-selector]** Graph Local Neighborhood Selector
- **[T260628-lint-type-routine-gate-cleanup]** Lint Type Routine Gate Cleanup
- **[T260629-storage-scale-model-proof-contract]** Storage Scale-Model Proof Contract
<!-- WORKBOARD:NOW:END -->

## 2. Task Inbox
*Captured review items and inbox threads.*

<!-- WORKBOARD:INBOX:START -->

<!-- WORKBOARD:INBOX:END -->

## 2a. Pain-Point Log
*Raw operator friction. One or two sentences per entry; do not elaborate here.*

- **2026-06-28 task-intake deficit:** The weekend produced a useful but tiring
  task-opening surplus. Capture future friction here before promoting it to a
  task.

## 2b. Unelaborated Backlog
*Known follow-on pressure. One line each; do not promote to tasks until selected.*

- **Local model driver:** Optional Stage 4 `llama-cpp` in-process driver with
  dynamic import, opened only when a concrete local-driver need appears.
- **Endpoint/model routing:** Multiple configured endpoints, multiple models
  per endpoint, fast operator switching, and eventual task-class-specific
  endpoint/model policy for parallelism and auto-summary lanes.

### Strategic Priorities (Manual)
- **Architecture Follow-Through:** Coordinate top-down domain work under
  `260614-architecture-follow-through-coordination`.
- **Focused Implementation:** Open narrow subtasks from concrete architecture,
  failure, or regression evidence rather than reopening closed umbrellas.
- **Immediate Queue Order:** Work the remaining June 27 segmented-storage
  chain next:
  `260627-split-storage-rebuild-and-projection-parity`.
- **Next Operator-Leverage Lane:** After that proof chain, prioritize
  `260627-history-recovery-tooling` and
  `260627-history-surface-user-intent-alignment` so corrupt-history refusal
  and healthy-history inspection both point users toward usable next actions.
- **Design Work Held Warm:** Keep
  `260626-events-jsonl-multiplicity-and-merge-provenance`,
  `260626-transcript-parallelism-design-pressures`, and
  `260627-history-affordances-semantic-restaging` active as framing work, but
  use them to sharpen implementation slices rather than treating them as the
  next build targets.
- **Deferred But Still Open:** `260621-windows-shell-launcher-and-path-resolution`
  remains an active implementation lane, but it is no longer the first manual
  priority after the June 26-27 task intake.
- **New Follow-Up:** `260622-staged-replay-trailing-edge-newline-healing`
  captures the likely CRLF/trailing-newline seam where indent-only mismatches
  may fall back to fuzzy diagnostics instead of staging `/heal`.
- **New Follow-Up:** `260622-tool-write-newline-policy-and-windows-lf-defaults`
  captures Windows tool-written CRLF defaults creating mixed endings in
  otherwise LF-oriented repos.

## 3. System Health
*Recurring maintenance and operational metrics.*

### Coverage & Hygiene
- [ ] **Coverage Ratchet**
  - *Last Run:* 2026-05-16
  - *Next Target:* `src/toas/cli/` and `src/toas/step/`
- [ ] **Docs Truth Governance**
  - *Last Run:* 2026-05-16
  - *Action:* Align `README.md` and `tasks/recurring/` templates with actual surface.

### Operational Sharp Edges
- [ ] **Sharp Edges Log**
  - *Last Run:* 2026-05-16
  - *Active Issues:*
    - [x] Windows async fixes follow-up (see #369) — sync stale: #369 (and
      its parent #366) closed Fixed; this was a flag that outlived its task,
      not a live sharp edge.
    - [ ] Vim transport annotation cleanup (see #554)

## 4. Recent Closures
*Key completions driving current momentum.*

<!-- WORKBOARD:CLOSED:START -->
- **[T260630-source-qualified-logical-index-lookup]** Source-Qualified Logical Index Lookup
- **[T260629-starting-dirty-tree-hygiene]** Starting Dirty Tree And Planning Surface Hygiene
- **[T260628-workboard-objective-parser-shape-tolerance]** Workboard Objective Parser Shape Tolerance
- **[T260628-transcript-writeback-surface-unification]** Transcript Writeback Surface Unification
- **[T260628-task-template-intent-line]** Give the task template a one-line intent slot under the title so authored tasks carry a non-redundant workboard label by construction.
<!-- WORKBOARD:CLOSED:END -->

### Impact Notes (Manual)
- **510:** Imported content projection now emits stable fenced metadata blocks for file reads, search excerpts, and high-confidence shell file output.
- **675:** Runtime/tool ownership guidance now lives in `docs/runtime-ownership.md`; legacy hub files are documented as facades.
- **543:** Stream-first stdio host lifecycle path established.
- **542:** Historical record preserved after local-host default cutover.
- **551:** Vim default transport is now `local_host`.
- **533:** CLI-level local mode lifecycle contract validated.

## 5. Strategic Arcs
*High-level themes and open questions.*

### A. Acceptance-Proven Operator Completion
- **Goal:** Reproducible end-to-end acceptance path from intake to validated commit.
- **Status:** Foundation closed under `469`/`470`; further orchestration exploration is parked under `488`.

### B. Maintainable Runtime Decomposition
- **Goal:** Thinner facades, focused helper ownership, stable coverage.
- **Status:** Umbrellas `400`, `374`, and `379` are closed; future work should
  open focused tasks from concrete domain, failure, or regression evidence.

### C. Weak-Model Protocol Reliability
- **Goal:** Deterministic tool guidance slices without manual coaching.
- **Status:** `471` closed; `415` open for patch safety.

### D. Transcript/Control/Config Contract Clarity
- **Goal:** Explicit precedence semantics and diagnostics.
- **Status:** `465`, `466`, and `354` closed; reopen only on fresh drift evidence.

### H. Primary-Path Runtime Ownership
- **Goal:** `step`/`watch`/`cancel` are ownership-first; cancellation is bounded/terminal.
- **Status:** `525` is closed; future ownership work should route through the
  architecture coordination task or focused follow-ups.
