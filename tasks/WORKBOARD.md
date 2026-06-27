# TOAS Workboard

> **Status:** Active Development
> **Last Sync:** 2026-06-27

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
- Current near-term queue from the June 26-27 intake is the remaining
  segmented storage chain starting with
  `260627-segmented-event-index-and-lookup-hardening`.
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
- Within the remaining segmented storage chain, sequence the work as:
  `260627-segmented-event-index-and-lookup-hardening` ->
  `260627-split-storage-rebuild-and-projection-parity`.
- Keep `260626-events-jsonl-multiplicity-and-merge-provenance`,
  `260626-transcript-parallelism-design-pressures`, and
  `260627-history-affordances-semantic-restaging` warm as design drivers, but
  do not force them ahead of the shell fixes or the segmented-storage proof
  chain.
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
<!-- WORKBOARD:RELATIONSHIP_ROOTS:END -->

### Active Arc Map
*Generated first-mention relationship tree; repeated tasks use `@task-id`.*

<!-- WORKBOARD:RELATIONSHIP_TREE:START -->
- 260614-architecture-follow-through-coordination # Architecture Follow-Through Coordination
  - 260614-backend-lifecycle-cross-process-identity # Backend Lifecycle Cross-Process Identity
  - 260614-legacy-and-fidelity-adapter-precedence # Legacy And Fidelity-Adapter Precedence
  - 260614-model-backend-failure-handoff # Model Invocation To Backend Lifecycle Failure Handoff
  - 260614-shell-owned-backend-lifecycle # Shell-Owned Backend Lifecycle
  - 260614-vim-test-cost-audit The vim tests dominate suite wall-clock time. Before accepting that cost as necessary, we should verify that the test structure isn't paying for setup...
  - 260615-runtime-package-growth-boundary-audit # Runtime Package Growth Boundary Audit
  - 260626-events-jsonl-multiplicity-and-merge-provenance # Events.jsonl Multiplicity And Merge Provenance (related `260626-transcript-parallelism-design-pressures`, `260509-multi-operator-orchestration`)
    - 260627-segmented-event-index-and-lookup-hardening # Segmented Event Index And Lookup Hardening (blocked by `260627-graph-segmented-read-query-hardening`; related `260614-architecture-follow-through-coordination`)
    - 260627-segmented-event-journal-storage-contract # Segmented Event Journal Storage Contract (related `260614-architecture-follow-through-coordination`)
    - 260627-split-storage-rebuild-and-projection-parity # Split Storage Rebuild And Projection Parity (blocked by `260627-graph-segmented-read-query-hardening`; related `260614-architecture-follow-through-coordination`)
  - 260626-transcript-parallelism-design-pressures The pressure is architectural before it is implementation detail.  It touches:  durable queue/claim facts projection identity versus transcript file i... (related `260509-multi-operator-orchestration`, `260524-exploratory-work-representation-model`)
  - 260627-history-affordances-semantic-restaging # History Affordances And Semantic Restaging (related `260626-transcript-parallelism-design-pressures`, `260524-exploratory-work-representation-model`)
<!-- WORKBOARD:RELATIONSHIP_TREE:END -->

- closed historical context: 400 module decomposition, 525 runtime ownership,
  374 coverage-led refactor pass, 379 coverage noise burndown

## 1. Open Queue
*Generated open-task inventory. Use Manual Triage above for active vs parked sequencing.*

<!-- WORKBOARD:NOW:START -->
- **[T260412-json-callable-lane-parser-and-policy]** Prompt-library text previously implied JSON action objects as if they were equivalent to current callable extraction, which created operator confusion...
- **[T260412-transcript-lcp-checkpoint-optimization]** Correctness fixes should land first, but full transcript rescans each step are unnecessary once we can recover effective state at a known checkpoint a...
- **[T260418-weak-model-safe-apply-patch-contract]** Current tool ergonomics rely significantly on model priors. We want a tighter contract and response shape that remains reliable when priors are weaker...
- **[T260428-cross-repo-intent-routing]** Cross-repo mission workflows were identified as a follow-on at `456` closure.
- **[T260428-session-identity-orchestration]** `456` established configurable transcript paths; next step is ergonomic multi-buffer identity and selection.
- **[T260509-alternative-operator-frontends]** Vim remains functional, but frontend diversity improves operator fit, reduces single-client coupling risk, and can surface protocol/runtime assumption...
- **[T260509-multi-operator-orchestration]** There is clear interest in reducing single-operator cognitive overhead by introducing structured high-level delegation/orchestration. This should be e...
- **[T260515-apply-patch-windows-crlf-hardening]** `apply_patch` failures on Windows/CRLF content are recurring and difficult to diagnose without better matching instrumentation.
- **[T260524-attention-focused-workboard-layout]** Design and implement an "Attention-Focused" layout for the Workboard that highlights high-impact tasks and suppresses noise.
- **[T260524-auto-inferred-task-dependencies]** Develop a mechanism to automatically infer task dependencies from code changes and commit history, reducing manual overhead and improving accuracy.
- **[T260524-exploratory-work-representation-model]** Define a flexible task schema that supports both "Verified Implementation" tasks and "Exploratory/Research" tasks without forcing one into the other's...
- **[T260524-workboard-as-control-surface]** Transform `WORKBOARD.md` from a passive report into an active control surface that allows the operator to influence system behavior.
- **[T260530-shell-lane-spawn-semantics]** Recent investigation under `571` found a deterministic lane split: Assistant lane shell calls could hang for commands like `rg ...` when no explicit p...
- **[T260602-transport-equivalence-certification]** `669` closed at the right bar for current work: shared runtime semantics are explicit routed daemon/RPC subscribe path no longer blocks parity legacy ...
- **[T260614-architecture-follow-through-coordination]** # Architecture Follow-Through Coordination
- **[T260614-backend-lifecycle-cross-process-identity]** # Backend Lifecycle Cross-Process Identity
- **[T260614-legacy-and-fidelity-adapter-precedence]** # Legacy And Fidelity-Adapter Precedence
- **[T260614-model-backend-failure-handoff]** # Model Invocation To Backend Lifecycle Failure Handoff
- **[T260614-shell-owned-backend-lifecycle]** # Shell-Owned Backend Lifecycle
- **[T260614-vim-test-cost-audit]** The vim tests dominate suite wall-clock time. Before accepting that cost as necessary, we should verify that the test structure isn't paying for setup...
- **[T260615-runtime-package-growth-boundary-audit]** # Runtime Package Growth Boundary Audit
- **[T260621-assistant-callable-plan-coalescing]** # Assistant Callable Plan Coalescing
- **[T260621-compact-search-output]** # Compact Search Output
- **[T260621-eval-command-output-formatting]** # Audit and Standardize Command Output Formats
- **[T260621-windows-shell-launcher-and-path-resolution]** # Windows Shell Launcher And Path Resolution
- **[T260621-yaml-block-indent-salvage]** # YAML Block Indent Salvage
- **[T260622-staged-replay-trailing-edge-newline-healing]** # Staged Replay Trailing-Edge Newline Healing
- **[T260622-tool-write-newline-policy-and-windows-lf-defaults]** # Tool Write Newline Policy And Windows LF Defaults
- **[T260626-events-jsonl-multiplicity-and-merge-provenance]** # Events.jsonl Multiplicity And Merge Provenance
- **[T260626-transcript-parallelism-design-pressures]** The pressure is architectural before it is implementation detail.  It touches:  durable queue/claim facts projection identity versus transcript file i...
- **[T260627-history-affordances-semantic-restaging]** # History Affordances And Semantic Restaging
- **[T260627-segmented-event-index-and-lookup-hardening]** # Segmented Event Index And Lookup Hardening
- **[T260627-split-storage-rebuild-and-projection-parity]** # Split Storage Rebuild And Projection Parity
<!-- WORKBOARD:NOW:END -->

## 2. Task Inbox
*Captured review items and inbox threads.*

<!-- WORKBOARD:INBOX:START -->

<!-- WORKBOARD:INBOX:END -->

### Strategic Priorities (Manual)
- **Architecture Follow-Through:** Coordinate top-down domain work under
  `260614-architecture-follow-through-coordination`.
- **Focused Implementation:** Open narrow subtasks from concrete architecture,
  failure, or regression evidence rather than reopening closed umbrellas.
- **Immediate Queue Order:** Work the remaining June 27 segmented-storage
  chain in this order:
  `260627-segmented-event-index-and-lookup-hardening`, then
  `260627-split-storage-rebuild-and-projection-parity`.
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
    - [ ] Windows async fixes follow-up (see #369)
    - [ ] Vim transport annotation cleanup (see #554)

## 4. Recent Closures
*Key completions driving current momentum.*

<!-- WORKBOARD:CLOSED:START -->
- **[T260627-workboard-relationship-tree-builder]** - relationship fields are parsed into structured task edges during workboard
- **[T260627-shell-script-control-word-and-assignment-grants]** # Shell Script Control-Word And Assignment Grants
- **[T260627-segmented-event-journal-storage-contract]** # Segmented Event Journal Storage Contract
- **[T260627-graph-segmented-read-query-hardening]** # Graph Segmented Read/Query Hardening
- **[T260627-live-repo-session-write-fence-decoupling]** # Live Repo Session Write Fence Decoupling
- **[T260626-shell-script-fence-safe-payload-parsing]** # Shell Script Fence-Safe Payload Parsing
- **[T260626-multiline-user-shell-command-spans]** # Multiline User Shell Command Spans
- **[T260626-multiline-shell-script-allowlist-segmentation]** # Multiline Shell Script Allowlist Segmentation
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
